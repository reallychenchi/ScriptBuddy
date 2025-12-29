import asyncio
import json
import struct
import logging
import websockets
from fastapi import WebSocket, WebSocketDisconnect
from api.services.config_service import ConfigService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tts_proxy")
logger.setLevel(logging.DEBUG)

# VolcEngine Binary Protocol Constants
class MsgType:
    FullClientRequest = 0b0001
    AudioOnlyServer = 0b1011
    FrontEndResultServer = 0b1100
    Error = 0b1111

class MsgTypeFlag:
    NoSeq = 0b0000
    PositiveSeq = 0b0001
    NegativeSeq = 0b0011

class SerializationType:
    Raw = 0b0000
    JSON = 0b0001

class CompressionType:
    NoCompression = 0b0000
    Gzip = 0b0001


def build_full_client_request(payload_bytes: bytes) -> bytes:
    """Build a FullClientRequest frame according to VolcEngine protocol.
    
    Frame format for FullClientRequest with NoSeq flag:
    - Header (4 bytes): version|headerSize, msgType|flags, serialization|compression, reserved
    - Payload Size (4 bytes, big endian)
    - Payload (variable)
    """
    # Header: version=1, headerSize=1 (4 bytes)
    header = bytes([
        0x11,  # version(4bits)=1, headerSize(4bits)=1
        (MsgType.FullClientRequest << 4) | MsgTypeFlag.NoSeq,  # msgType=1, flag=0
        (SerializationType.JSON << 4) | CompressionType.NoCompression,  # JSON, no compression
        0x00   # reserved
    ])
    
    # Payload size (big endian uint32)
    payload_size = struct.pack(">I", len(payload_bytes))
    
    return header + payload_size + payload_bytes


def parse_client_frame(data: bytes) -> dict | None:
    """Parse incoming frame from browser client and extract JSON payload.
    
    Expected format for FullClientRequest with NoSeq:
    - Header (4 bytes)
    - Payload Size (4 bytes)
    - Payload (JSON)
    """
    if len(data) < 8:
        logger.warning(f"Frame too short: {len(data)} bytes")
        return None
    
    # Parse header
    header = data[0:4]
    version = (header[0] >> 4) & 0x0F
    header_size = header[0] & 0x0F
    msg_type = (header[1] >> 4) & 0x0F
    flags = header[1] & 0x0F
    serialization = (header[2] >> 4) & 0x0F
    
    logger.debug(f"Frame header: version={version}, headerSize={header_size}, msgType={msg_type}, flags={flags}, serialization={serialization}")
    
    actual_header_size = header_size * 4
    cursor = actual_header_size
    
    # For FullClientRequest with NoSeq (flags=0), there is NO sequence field
    # Only read sequence if flags indicate it (POS_SEQUENCE=1, NEG_SEQUENCE=2, NEG_WITH_SEQ=3)
    if flags in [MsgTypeFlag.PositiveSeq, MsgTypeFlag.NegativeSeq]:
        if len(data) < cursor + 4:
            logger.warning("Frame too short for sequence")
            return None
        seq = struct.unpack(">i", data[cursor:cursor+4])[0]
        cursor += 4
        logger.debug(f"Sequence: {seq}")
    
    # Read payload size
    if len(data) < cursor + 4:
        logger.warning("Frame too short for payload size")
        return None
    
    payload_size = struct.unpack(">I", data[cursor:cursor+4])[0]
    cursor += 4
    
    logger.debug(f"Payload size: {payload_size}, remaining data: {len(data) - cursor}")
    
    # Read payload
    if len(data) < cursor + payload_size:
        logger.warning(f"Frame too short for payload: expected {payload_size}, got {len(data) - cursor}")
        return None
    
    payload_bytes = data[cursor:cursor+payload_size]
    
    if serialization == SerializationType.JSON:
        try:
            payload = json.loads(payload_bytes.decode('utf-8'))
            logger.debug(f"Parsed JSON payload successfully")
            return payload
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON payload: {e}")
            logger.debug(f"Payload bytes: {payload_bytes[:100]}")
            return None
    else:
        logger.warning(f"Unsupported serialization: {serialization}")
        return None


async def tts_websocket_endpoint(client_ws: WebSocket):
    await client_ws.accept()
    logger.info("🔊 [TTS Proxy] Client connected")
    
    # 1. Get Config
    all_configs = ConfigService.get_all_configs()
    tts_config = all_configs.get("tts", {})
    
    app_id = tts_config.get("appId")
    token = tts_config.get("token")
    cluster = tts_config.get("cluster")
    
    logger.debug(f"🔊 [TTS Proxy] Config loaded - appId: {app_id[:8] if app_id else 'None'}..., cluster: {cluster}")
    
    if not (app_id and token and cluster):
        logger.error("🔊 [TTS Proxy] ❌ Server config missing!")
        await client_ws.close(code=1008, reason="Server Config Missing")
        return

    # 2. Build Headers for VolcEngine
    extra_headers = {
        "Authorization": f"Bearer;{token}",
    }
    
    volc_url = "wss://openspeech.bytedance.com/api/v1/tts/ws_binary"
    logger.info(f"🔊 [TTS Proxy] Connecting to VolcEngine: {volc_url}")

    try:
        async with websockets.connect(volc_url, extra_headers=extra_headers, max_size=10*1024*1024) as volc_ws:
            logger.info("🔊 [TTS Proxy] ✓ Connected to VolcEngine")
            
            client_to_volc_count = 0
            volc_to_client_count = 0
            volc_to_client_bytes = 0
            
            async def client_to_volc():
                nonlocal client_to_volc_count
                try:
                    while True:
                        data = await client_ws.receive_bytes()
                        client_to_volc_count += 1
                        logger.debug(f"🔊 [TTS Proxy] Client → Volc #{client_to_volc_count}: {len(data)} bytes")
                        
                        # Parse the client's frame
                        payload = parse_client_frame(data)
                        
                        if payload:
                            # Inject app credentials into payload
                            payload["app"] = {
                                "appid": app_id,
                                "token": token,
                                "cluster": cluster
                            }
                            
                            logger.debug(f"🔊 [TTS Proxy] Injected app credentials. Text: {payload.get('request', {}).get('text', '')[:30]}...")
                            
                            # Rebuild the frame with correct format
                            new_payload_bytes = json.dumps(payload).encode('utf-8')
                            new_frame = build_full_client_request(new_payload_bytes)
                            
                            logger.debug(f"🔊 [TTS Proxy] Rebuilt frame: {len(new_frame)} bytes")
                            await volc_ws.send(new_frame)
                        else:
                            # If we can't parse, forward as-is (might be audio-only frame)
                            logger.warning("🔊 [TTS Proxy] Could not parse frame, forwarding as-is")
                            await volc_ws.send(data)
                            
                except WebSocketDisconnect:
                    logger.info("🔊 [TTS Proxy] Client disconnected")
                except Exception as e:
                    logger.error(f"🔊 [TTS Proxy] ❌ Client→Volc Error: {e}")

            async def volc_to_client():
                nonlocal volc_to_client_count, volc_to_client_bytes
                try:
                    async for message in volc_ws:
                        volc_to_client_count += 1
                        msg_len = len(message) if isinstance(message, bytes) else len(message.encode())
                        volc_to_client_bytes += msg_len
                        logger.debug(f"🔊 [TTS Proxy] Volc → Client #{volc_to_client_count}: {msg_len} bytes")
                        await client_ws.send_bytes(message)
                except Exception as e:
                    logger.error(f"🔊 [TTS Proxy] ❌ Volc→Client Error: {e}")
                finally:
                    logger.info(f"🔊 [TTS Proxy] Session stats: {volc_to_client_count} messages, {volc_to_client_bytes} bytes from Volc")

            await asyncio.gather(client_to_volc(), volc_to_client())

    except Exception as e:
        logger.error(f"🔊 [TTS Proxy] ❌ Connection Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        try:
            await client_ws.close(code=1011, reason=str(e))
        except:
            pass
