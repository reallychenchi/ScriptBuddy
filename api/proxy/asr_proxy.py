import asyncio
import json
import struct
import logging
import uuid
import gzip
import websockets
from fastapi import WebSocket, WebSocketDisconnect
from api.services.config_service import ConfigService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("asr_proxy")
logger.setLevel(logging.DEBUG)

# VolcEngine Binary Protocol Constants
class MsgType:
    FullClientRequest = 0b0001
    AudioOnlyClient = 0b0010
    FullServerResponse = 0b1001
    AudioOnlyServer = 0b1011
    Error = 0b1111

class MsgTypeFlag:
    NoSeq = 0b0000
    PositiveSeq = 0b0001
    NegativeSeq = 0b0010
    NegativeSeqLast = 0b0011

class SerializationType:
    Raw = 0b0000
    JSON = 0b0001

class CompressionType:
    NoCompression = 0b0000
    Gzip = 0b0001


def build_full_client_request(payload_bytes: bytes, use_compression: bool = True) -> bytes:
    """Build a FullClientRequest frame for ASR.

    Frame format for FullClientRequest with NoSeq flag:
    - Header (4 bytes)
    - Payload Size (4 bytes, big endian)
    - Payload (variable, optionally compressed)
    """
    # Compress payload if requested
    if use_compression:
        payload_bytes = gzip.compress(payload_bytes)
        compression = CompressionType.Gzip
    else:
        compression = CompressionType.NoCompression

    header = bytes([
        0x11,  # version=1, headerSize=1
        (MsgType.FullClientRequest << 4) | MsgTypeFlag.NoSeq,
        (SerializationType.JSON << 4) | compression,
        0x00
    ])
    payload_size = struct.pack(">I", len(payload_bytes))
    return header + payload_size + payload_bytes


def build_audio_only_request(audio_data: bytes, sequence: int, is_last: bool, use_compression: bool = True) -> bytes:
    """Build an AudioOnlyClient frame for ASR.

    Frame format for AudioOnlyClient with sequence:
    - Header (4 bytes)
    - Sequence (4 bytes, signed int, big endian) - negative if last
    - Payload Size (4 bytes, big endian)
    - Payload (audio data, optionally compressed)
    """
    # Compress audio data if requested
    if use_compression:
        audio_data = gzip.compress(audio_data)
        compression = CompressionType.Gzip
    else:
        compression = CompressionType.NoCompression

    flag = MsgTypeFlag.NegativeSeqLast if is_last else MsgTypeFlag.PositiveSeq

    header = bytes([
        0x11,
        (MsgType.AudioOnlyClient << 4) | flag,
        (SerializationType.Raw << 4) | compression,
        0x00
    ])

    seq_value = -sequence if is_last else sequence
    seq_bytes = struct.pack(">i", seq_value)
    payload_size = struct.pack(">I", len(audio_data))

    return header + seq_bytes + payload_size + audio_data


def parse_client_frame(data: bytes) -> tuple:
    """Parse incoming frame from browser client.

    Returns: (msg_type, flags, payload_or_audio, sequence)
    """
    if len(data) < 8:
        logger.warning(f"Frame too short: {len(data)} bytes")
        return (None, None, None, 0)

    header = data[0:4]
    version = (header[0] >> 4) & 0x0F
    header_size = header[0] & 0x0F
    msg_type = (header[1] >> 4) & 0x0F
    flags = header[1] & 0x0F
    serialization = (header[2] >> 4) & 0x0F
    compression = header[2] & 0x0F

    logger.debug(f"🎤 [ASR] Frame: version={version}, headerSize={header_size}, msgType={msg_type}, flags={flags}, serialization={serialization}, compression={compression}")

    actual_header_size = header_size * 4
    cursor = actual_header_size

    sequence = 0
    # For FullClientRequest with NoSeq (flags=0), NO sequence field
    # For AudioOnly with PositiveSeq/NegativeSeq, read sequence
    if flags in [MsgTypeFlag.PositiveSeq, MsgTypeFlag.NegativeSeq, MsgTypeFlag.NegativeSeqLast]:
        if len(data) < cursor + 4:
            logger.warning("Frame too short for sequence")
            return (None, None, None, 0)
        sequence = struct.unpack(">i", data[cursor:cursor+4])[0]
        cursor += 4
        logger.debug(f"🎤 [ASR] Sequence: {sequence}")

    if len(data) < cursor + 4:
        logger.warning("Frame too short for payload size")
        return (None, None, None, 0)

    payload_size = struct.unpack(">I", data[cursor:cursor+4])[0]
    cursor += 4

    logger.debug(f"🎤 [ASR] Payload size: {payload_size}, remaining: {len(data) - cursor}")

    if len(data) < cursor + payload_size:
        logger.warning(f"Frame too short for payload: expected {payload_size}, got {len(data) - cursor}")
        return (None, None, None, 0)

    payload_bytes = data[cursor:cursor+payload_size]

    # Decompress if needed
    if compression == CompressionType.Gzip:
        try:
            payload_bytes = gzip.decompress(payload_bytes)
            logger.debug(f"🎤 [ASR] Decompressed payload: {len(payload_bytes)} bytes")
        except Exception as e:
            logger.error(f"🎤 [ASR] Failed to decompress: {e}")
            return (None, None, None, 0)

    if msg_type == MsgType.FullClientRequest:
        # JSON payload
        try:
            payload = json.loads(payload_bytes.decode('utf-8'))
            logger.debug(f"🎤 [ASR] Parsed FullClientRequest JSON: {list(payload.keys())}")
            return (msg_type, flags, payload, sequence)
        except json.JSONDecodeError as e:
            logger.error(f"🎤 [ASR] JSON parse error: {e}")
            logger.debug(f"🎤 [ASR] Raw bytes (first 100): {payload_bytes[:100]}")
            return (msg_type, flags, None, sequence)
    elif msg_type == MsgType.AudioOnlyClient:
        # Audio payload
        return (msg_type, flags, payload_bytes, sequence)

    logger.debug(f"🎤 [ASR] Unknown msg_type: {msg_type}")
    return (msg_type, flags, payload_bytes, sequence)


async def asr_websocket_endpoint(client_ws: WebSocket):
    await client_ws.accept()
    logger.info("🎤 [ASR Proxy] Client connected")

    # 1. Get Config
    all_configs = ConfigService.get_all_configs()
    asr_config = all_configs.get("asr", {})

    app_key = asr_config.get("appId")        # V2L_APPID → app_key
    access_token = asr_config.get("token")   # V2L_ACCESS_TOKEN
    cluster = asr_config.get("cluster")

    # V2 API works with ACCESS_TOKEN (verified by test)
    access_key = access_token

    logger.info(f"🎤 [ASR Proxy] Config loaded:")
    logger.info(f"  - appKey: {app_key}")
    logger.info(f"  - accessKey: {access_key}")
    logger.info(f"  - cluster: {cluster}")
    logger.info(f"  - Using V3 API (bigmodel)")

    if not (app_key and access_key):
        logger.error("🎤 [ASR Proxy] ❌ Server config missing!")
        await client_ws.close(code=1008, reason="Server Config Missing")
        return

    # 2. Build Headers (matching official demo: sauc_websocket_demo.py)
    reqid = str(uuid.uuid4())
    extra_headers = {
        "X-Api-Resource-Id": "volc.bigasr.sauc.duration",
        "X-Api-Request-Id": reqid,
        "X-Api-Access-Key": access_key,
        "X-Api-App-Key": app_key
    }

    # Use V3 API endpoint (same as official demo)
    volc_url = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel"
    logger.info(f"🎤 [ASR Proxy] Connecting to VolcEngine: {volc_url}")
    logger.info(f"🎤 [ASR Proxy] Headers: {extra_headers}")

    try:
        async with websockets.connect(volc_url, additional_headers=extra_headers, max_size=10*1024*1024) as volc_ws:
            logger.info("🎤 [ASR Proxy] ✓ Connected to VolcEngine")
            
            client_to_volc_count = 0
            client_to_volc_bytes = 0
            volc_to_client_count = 0
            
            async def client_to_volc():
                nonlocal client_to_volc_count, client_to_volc_bytes
                try:
                    while True:
                        data = await client_ws.receive_bytes()
                        client_to_volc_count += 1
                        client_to_volc_bytes += len(data)
                        
                        msg_type, flags, payload, sequence = parse_client_frame(data)
                        
                        logger.debug(f"🎤 [ASR Proxy] Frame #{client_to_volc_count}: msg_type={msg_type}, flags={flags}, payload_type={type(payload).__name__}")
                        
                        if msg_type == MsgType.FullClientRequest:
                            if isinstance(payload, dict):
                                # For ASR v3 API, authentication is done via headers only
                                # No need to inject app credentials into payload
                                logger.debug(f"🎤 [ASR Proxy] Forwarding FullClientRequest from client")

                                new_payload_bytes = json.dumps(payload).encode('utf-8')
                                new_frame = build_full_client_request(new_payload_bytes)

                                logger.debug(f"🎤 [ASR Proxy] Client → Volc #1: {len(new_frame)} bytes (rebuilt)")
                                await volc_ws.send(new_frame)
                            else:
                                # Payload parsing failed, forward original frame
                                logger.warning(f"🎤 [ASR Proxy] FullClientRequest but payload={payload}, forwarding as-is")
                                await volc_ws.send(data)
                            
                        elif msg_type == MsgType.AudioOnlyClient:
                            # Audio frame - rebuild with correct format
                            is_last = sequence < 0
                            abs_seq = abs(sequence) if sequence != 0 else client_to_volc_count
                            
                            new_frame = build_audio_only_request(payload, abs_seq, is_last)
                            
                            if client_to_volc_count <= 3 or client_to_volc_count % 50 == 0:
                                logger.debug(f"🎤 [ASR Proxy] Client → Volc #{client_to_volc_count}: {len(new_frame)} bytes (audio, last={is_last})")
                            
                            await volc_ws.send(new_frame)
                        else:
                            # Unknown frame type, forward as-is
                            logger.warning(f"🎤 [ASR Proxy] Unknown frame type {msg_type}, forwarding as-is (raw={len(data)} bytes)")
                            await volc_ws.send(data)
                            
                except WebSocketDisconnect:
                    logger.info(f"🎤 [ASR Proxy] Client disconnected. Total: {client_to_volc_count} frames, {client_to_volc_bytes} bytes")
                except Exception as e:
                    logger.error(f"🎤 [ASR Proxy] ❌ Client→Volc Error: {e}")
                    import traceback
                    logger.error(traceback.format_exc())

            async def volc_to_client():
                nonlocal volc_to_client_count
                try:
                    async for message in volc_ws:
                        volc_to_client_count += 1
                        msg_len = len(message) if isinstance(message, bytes) else len(message.encode())

                        # Try to decode and log the response
                        try:
                            if isinstance(message, bytes) and len(message) > 8:
                                header = message[0:4]
                                msg_type = (header[1] >> 4) & 0x0F
                                flags = header[1] & 0x0F
                                serialization = (header[2] >> 4) & 0x0F
                                compression = header[2] & 0x0F

                                logger.debug(f"🎤 [ASR] Response header: type={msg_type}, flags={flags}, ser={serialization}, comp={compression}, raw={header.hex()}")

                                if msg_type == MsgType.FullServerResponse:
                                    payload_size = struct.unpack(">I", message[4:8])[0]
                                    if payload_size > 0 and len(message) >= 8 + payload_size:
                                        payload_bytes = message[8:8+payload_size]

                                        # Decompress if gzipped
                                        if compression == CompressionType.Gzip:
                                            try:
                                                payload_bytes = gzip.decompress(payload_bytes)
                                            except:
                                                pass

                                        payload_str = payload_bytes.decode('utf-8', errors='ignore')

                                        # Parse JSON and extract recognition result
                                        try:
                                            resp_json = json.loads(payload_str)
                                            result = resp_json.get("result", {})
                                            text = result.get("text", "")
                                            is_final = result.get("utterance_end", False)

                                            if text:
                                                if is_final:
                                                    logger.info(f"🎤 [ASR] ✅ Final: \"{text}\"")
                                                else:
                                                    logger.debug(f"🎤 [ASR] Partial: \"{text}\"")
                                            else:
                                                logger.debug(f"🎤 [ASR Proxy] Volc → Client #{volc_to_client_count}: {msg_len} bytes")
                                        except json.JSONDecodeError:
                                            logger.debug(f"🎤 [ASR Proxy] Response: {payload_str[:200]}...")
                                elif msg_type == MsgType.Error:
                                    # Parse error response (format: header + [seq] + error_code + payload_size + payload)
                                    try:
                                        cursor = 4  # after header
                                        # Check if sequence is present (flags & 0x01)
                                        if flags & 0x01:
                                            cursor += 4  # skip sequence

                                        error_code = struct.unpack(">i", message[cursor:cursor+4])[0]
                                        cursor += 4
                                        error_payload_size = struct.unpack(">I", message[cursor:cursor+4])[0]
                                        cursor += 4

                                        if error_payload_size > 0 and len(message) >= cursor + error_payload_size:
                                            error_bytes = message[cursor:cursor+error_payload_size]
                                            if compression == CompressionType.Gzip:
                                                try:
                                                    error_bytes = gzip.decompress(error_bytes)
                                                except:
                                                    pass
                                            error_str = error_bytes.decode('utf-8', errors='ignore')
                                            # Try to parse as JSON for better formatting
                                            try:
                                                error_json = json.loads(error_str)
                                                error_msg = error_json.get("message", error_str)
                                                logger.error(f"🎤 [ASR Proxy] ❌ Error {error_code}: {error_msg}")
                                            except:
                                                logger.error(f"🎤 [ASR Proxy] ❌ Error {error_code}: {error_str}")
                                        else:
                                            logger.error(f"🎤 [ASR Proxy] ❌ Error code: {error_code}")
                                    except Exception as err_parse:
                                        logger.error(f"🎤 [ASR Proxy] ❌ Error response: {msg_len} bytes (parse failed: {err_parse})")
                                else:
                                    logger.debug(f"🎤 [ASR Proxy] Volc → Client #{volc_to_client_count}: {msg_len} bytes (type={msg_type})")
                        except Exception as parse_err:
                            logger.debug(f"🎤 [ASR Proxy] Volc → Client #{volc_to_client_count}: {msg_len} bytes")

                        await client_ws.send_bytes(message)
                except Exception as e:
                    logger.error(f"🎤 [ASR Proxy] ❌ Volc→Client Error: {e}")
                finally:
                    logger.info(f"🎤 [ASR Proxy] Session ended. Responses from Volc: {volc_to_client_count}")

            await asyncio.gather(client_to_volc(), volc_to_client())

    except Exception as e:
        logger.error(f"🎤 [ASR Proxy] ❌ Connection Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        try:
            await client_ws.close(code=1011, reason=str(e))
        except:
            pass
