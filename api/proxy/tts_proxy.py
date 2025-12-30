import asyncio
import io
import json
import struct
import logging
import uuid
from dataclasses import dataclass
from enum import IntEnum
from typing import List, Callable

import websockets
from fastapi import WebSocket, WebSocketDisconnect
from api.services.config_service import ConfigService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tts_proxy")
logger.setLevel(logging.DEBUG)


# ===============================================================
# VolcEngine Binary Protocol (matching official SDK implementation)
# ===============================================================

class MsgType(IntEnum):
    """Message type enumeration"""
    Invalid = 0
    FullClientRequest = 0b1
    AudioOnlyClient = 0b10
    FullServerResponse = 0b1001
    AudioOnlyServer = 0b1011
    FrontEndResultServer = 0b1100
    Error = 0b1111

    ServerACK = AudioOnlyServer  # Alias


class MsgTypeFlagBits(IntEnum):
    """Message type flag bits"""
    NoSeq = 0  # Non-terminal packet with no sequence
    PositiveSeq = 0b1  # Non-terminal packet with sequence > 0
    LastNoSeq = 0b10  # Last packet with no sequence
    NegativeSeq = 0b11  # Last packet with sequence < 0
    WithEvent = 0b100  # Payload contains event number (int32)


class VersionBits(IntEnum):
    """Version bits"""
    Version1 = 1


class HeaderSizeBits(IntEnum):
    """Header size bits (in units of 4 bytes)"""
    HeaderSize4 = 1


class SerializationBits(IntEnum):
    """Serialization method bits"""
    Raw = 0
    JSON = 0b1


class CompressionBits(IntEnum):
    """Compression method bits"""
    None_ = 0
    Gzip = 0b1


@dataclass
class Message:
    """Message object for VolcEngine TTS binary protocol"""

    version: VersionBits = VersionBits.Version1
    header_size: HeaderSizeBits = HeaderSizeBits.HeaderSize4
    type: MsgType = MsgType.Invalid
    flag: MsgTypeFlagBits = MsgTypeFlagBits.NoSeq
    serialization: SerializationBits = SerializationBits.JSON
    compression: CompressionBits = CompressionBits.None_

    sequence: int = 0
    error_code: int = 0
    payload: bytes = b""

    @classmethod
    def from_bytes(cls, data: bytes) -> "Message":
        """Create message object from bytes"""
        if len(data) < 3:
            raise ValueError(f"Data too short: expected at least 3 bytes, got {len(data)}")

        type_and_flag = data[1]
        msg_type = MsgType(type_and_flag >> 4)
        flag = MsgTypeFlagBits(type_and_flag & 0b00001111)

        msg = cls(type=msg_type, flag=flag)
        msg.unmarshal(data)
        return msg

    def marshal(self) -> bytes:
        """Serialize message to bytes"""
        buffer = io.BytesIO()

        # Write header (4 bytes)
        header = [
            (self.version << 4) | self.header_size,
            (self.type << 4) | self.flag,
            (self.serialization << 4) | self.compression,
        ]

        header_size = 4 * self.header_size
        if padding := header_size - len(header):
            header.extend([0] * padding)

        buffer.write(bytes(header))

        # Write other fields
        writers = self._get_writers()
        for writer in writers:
            writer(buffer)

        return buffer.getvalue()

    def unmarshal(self, data: bytes) -> None:
        """Deserialize message from bytes"""
        buffer = io.BytesIO(data)

        # Read version and header size
        version_and_header_size = buffer.read(1)[0]
        self.version = VersionBits(version_and_header_size >> 4)
        self.header_size = HeaderSizeBits(version_and_header_size & 0b00001111)

        # Skip second byte (type and flag already parsed in from_bytes)
        buffer.read(1)

        # Read serialization and compression methods
        serialization_compression = buffer.read(1)[0]
        self.serialization = SerializationBits(serialization_compression >> 4)
        self.compression = CompressionBits(serialization_compression & 0b00001111)

        # Skip header padding
        header_size = 4 * self.header_size
        read_size = 3
        if padding_size := header_size - read_size:
            buffer.read(padding_size)

        # Read other fields
        readers = self._get_readers()
        for reader in readers:
            reader(buffer)

    def _get_writers(self) -> List[Callable[[io.BytesIO], None]]:
        """Get list of writer functions"""
        writers = []

        if self.type in [
            MsgType.FullClientRequest,
            MsgType.FullServerResponse,
            MsgType.FrontEndResultServer,
            MsgType.AudioOnlyClient,
            MsgType.AudioOnlyServer,
        ]:
            if self.flag in [MsgTypeFlagBits.PositiveSeq, MsgTypeFlagBits.NegativeSeq]:
                writers.append(self._write_sequence)
        elif self.type == MsgType.Error:
            writers.append(self._write_error_code)

        writers.append(self._write_payload)
        return writers

    def _get_readers(self) -> List[Callable[[io.BytesIO], None]]:
        """Get list of reader functions"""
        readers = []

        if self.type in [
            MsgType.FullClientRequest,
            MsgType.FullServerResponse,
            MsgType.FrontEndResultServer,
            MsgType.AudioOnlyClient,
            MsgType.AudioOnlyServer,
        ]:
            if self.flag in [MsgTypeFlagBits.PositiveSeq, MsgTypeFlagBits.NegativeSeq]:
                readers.append(self._read_sequence)
        elif self.type == MsgType.Error:
            readers.append(self._read_error_code)

        readers.append(self._read_payload)
        return readers

    def _write_sequence(self, buffer: io.BytesIO) -> None:
        """Write sequence number"""
        buffer.write(struct.pack(">i", self.sequence))

    def _write_error_code(self, buffer: io.BytesIO) -> None:
        """Write error code"""
        buffer.write(struct.pack(">I", self.error_code))

    def _write_payload(self, buffer: io.BytesIO) -> None:
        """Write payload"""
        size = len(self.payload)
        buffer.write(struct.pack(">I", size))
        buffer.write(self.payload)

    def _read_sequence(self, buffer: io.BytesIO) -> None:
        """Read sequence number"""
        sequence_bytes = buffer.read(4)
        if sequence_bytes:
            self.sequence = struct.unpack(">i", sequence_bytes)[0]

    def _read_error_code(self, buffer: io.BytesIO) -> None:
        """Read error code"""
        error_code_bytes = buffer.read(4)
        if error_code_bytes:
            self.error_code = struct.unpack(">I", error_code_bytes)[0]

    def _read_payload(self, buffer: io.BytesIO) -> None:
        """Read payload"""
        size_bytes = buffer.read(4)
        if size_bytes:
            size = struct.unpack(">I", size_bytes)[0]
            if size > 0:
                self.payload = buffer.read(size)

    def __str__(self) -> str:
        """String representation"""
        if self.type in [MsgType.AudioOnlyServer, MsgType.AudioOnlyClient]:
            if self.flag in [MsgTypeFlagBits.PositiveSeq, MsgTypeFlagBits.NegativeSeq]:
                return f"MsgType: {self.type.name}, Sequence: {self.sequence}, PayloadSize: {len(self.payload)}"
            return f"MsgType: {self.type.name}, PayloadSize: {len(self.payload)}"
        elif self.type == MsgType.Error:
            return f"MsgType: {self.type.name}, ErrorCode: {self.error_code}, Payload: {self.payload.decode('utf-8', 'ignore')}"
        else:
            if self.flag in [MsgTypeFlagBits.PositiveSeq, MsgTypeFlagBits.NegativeSeq]:
                return f"MsgType: {self.type.name}, Sequence: {self.sequence}, Payload: {self.payload.decode('utf-8', 'ignore')}"
            return f"MsgType: {self.type.name}, Payload: {self.payload.decode('utf-8', 'ignore')}"


def get_cluster(voice_type: str) -> str:
    """Determine cluster based on voice type (matching official SDK logic)"""
    if voice_type.startswith("S_"):
        return "volcano_icl"
    return "volcano_tts"


async def full_client_request(websocket, payload: bytes) -> None:
    """Send full client request message"""
    msg = Message(type=MsgType.FullClientRequest, flag=MsgTypeFlagBits.NoSeq)
    msg.payload = payload
    logger.debug(f"Sending: {msg}")
    await websocket.send(msg.marshal())


async def receive_message(websocket) -> Message:
    """Receive message from websocket"""
    data = await websocket.recv()
    if isinstance(data, str):
        raise ValueError(f"Unexpected text message: {data}")
    elif isinstance(data, bytes):
        msg = Message.from_bytes(data)
        logger.debug(f"Received: {msg}")
        return msg
    else:
        raise ValueError(f"Unexpected message type: {type(data)}")


# ===============================================================
# TTS WebSocket Proxy Endpoint
# ===============================================================

async def tts_websocket_endpoint(client_ws: WebSocket):
    await client_ws.accept()
    logger.info("🔊 [TTS Proxy] Client connected")

    # 1. Get Config
    all_configs = ConfigService.get_all_configs()
    tts_config = all_configs.get("tts", {})

    app_id = tts_config.get("appId")
    token = tts_config.get("token")
    voice_type = tts_config.get("voiceType", "zh_male_linjiananhai_moon_bigtts")

    logger.debug(f"🔊 [TTS Proxy] Config loaded - appId: {app_id[:8] if app_id else 'None'}...")

    if not (app_id and token):
        logger.error("🔊 [TTS Proxy] ❌ Server config missing!")
        await client_ws.close(code=1008, reason="Server Config Missing")
        return

    # Determine cluster based on voice type (matching demo logic)
    cluster = get_cluster(voice_type)
    logger.info(f"🔊 [TTS Proxy] Using cluster: {cluster} for voice: {voice_type}")

    # 2. Build Headers for VolcEngine (matching demo)
    extra_headers = {
        "Authorization": f"Bearer;{token}",
    }

    volc_url = "wss://openspeech.bytedance.com/api/v1/tts/ws_binary"
    logger.info(f"🔊 [TTS Proxy] Connecting to VolcEngine: {volc_url}")

    try:
        async with websockets.connect(
            volc_url,
            additional_headers=extra_headers,
            max_size=10 * 1024 * 1024
        ) as volc_ws:
            logger.info(f"🔊 [TTS Proxy] ✓ Connected to VolcEngine")
            if hasattr(volc_ws, 'response') and volc_ws.response:
                log_id = volc_ws.response.headers.get('x-tt-logid', 'N/A')
                logger.info(f"🔊 [TTS Proxy] Logid: {log_id}")

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

                        # Parse the client's frame using our Message class
                        try:
                            client_msg = Message.from_bytes(data)
                            logger.debug(f"🔊 [TTS Proxy] Parsed client message: {client_msg}")

                            if client_msg.serialization == SerializationBits.JSON and client_msg.payload:
                                # Parse JSON payload
                                payload = json.loads(client_msg.payload.decode('utf-8'))

                                # Inject app credentials (matching demo format)
                                payload["app"] = {
                                    "appid": app_id,
                                    "token": token,
                                    "cluster": cluster
                                }

                                # Ensure user UID is set
                                if "user" not in payload:
                                    payload["user"] = {"uid": str(uuid.uuid4())}
                                elif "uid" not in payload["user"]:
                                    payload["user"]["uid"] = str(uuid.uuid4())

                                # Ensure request has reqid
                                if "request" in payload and "reqid" not in payload["request"]:
                                    payload["request"]["reqid"] = str(uuid.uuid4())

                                logger.debug(f"🔊 [TTS Proxy] Injected app credentials. Text: {payload.get('request', {}).get('text', '')[:30]}...")

                                # Rebuild and send the frame
                                new_payload_bytes = json.dumps(payload).encode('utf-8')
                                await full_client_request(volc_ws, new_payload_bytes)
                            else:
                                # Non-JSON or no payload, forward as-is
                                logger.debug("🔊 [TTS Proxy] Forwarding non-JSON frame as-is")
                                await volc_ws.send(data)

                        except Exception as parse_error:
                            logger.warning(f"🔊 [TTS Proxy] Could not parse frame ({parse_error}), forwarding as-is")
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

                        # Parse the message to log details
                        if isinstance(message, bytes):
                            try:
                                parsed_msg = Message.from_bytes(message)
                                if parsed_msg.type == MsgType.Error:
                                    logger.error(f"🔊 [TTS Proxy] ❌ Volc Error: {parsed_msg}")
                                elif parsed_msg.type == MsgType.AudioOnlyServer:
                                    logger.debug(f"🔊 [TTS Proxy] Volc → Client #{volc_to_client_count}: Audio {msg_len} bytes, seq={parsed_msg.sequence}")
                                else:
                                    logger.debug(f"🔊 [TTS Proxy] Volc → Client #{volc_to_client_count}: {parsed_msg}")
                            except Exception:
                                logger.debug(f"🔊 [TTS Proxy] Volc → Client #{volc_to_client_count}: {msg_len} bytes (raw)")

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
