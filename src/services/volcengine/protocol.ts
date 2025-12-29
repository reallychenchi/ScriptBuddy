// src/services/volcengine/protocol.ts
import { v4 as uuidv4 } from 'uuid';

// Protocol Constants
export const PROTOCOL_VERSION = 0b0001;
export const DEFAULT_HEADER_SIZE = 0b0001;

export enum MessageType {
    CLIENT_FULL_REQUEST = 0b0001,
    CLIENT_AUDIO_ONLY_REQUEST = 0b0010,
    SERVER_FULL_RESPONSE = 0b1001,
    SERVER_ACK = 0b1011,
    SERVER_ERROR_RESPONSE = 0b1111,
}

export enum MessageTypeSpecificFlags {
    NO_SEQUENCE = 0b0000,
    POS_SEQUENCE = 0b0001,
    NEG_SEQUENCE = 0b0010,
    NEG_WITH_SEQUENCE = 0b0011,
}

export enum SerializationType {
    NO_SERIALIZATION = 0b0000,
    JSON = 0b0001,
    THRIFT = 0b0011,
}

export enum CompressionType {
    NO_COMPRESSION = 0b0000,
    GZIP = 0b0001,
}

// Helper to create header bytes (4 bytes)
export function createHeader(
    messageType: MessageType,
    messageTypeSpecificFlags: MessageTypeSpecificFlags,
    serializationType: SerializationType,
    compressionType: CompressionType
): Uint8Array {
    const header = new Uint8Array(4);
    header[0] = (PROTOCOL_VERSION << 4) | DEFAULT_HEADER_SIZE;
    header[1] = (messageType << 4) | messageTypeSpecificFlags;
    header[2] = (serializationType << 4) | compressionType;
    header[3] = 0x00;
    return header;
}

/**
 * Build a FullClientRequest frame for TTS/ASR initial request.
 * 
 * VolcEngine protocol format for FullClientRequest with NoSeq:
 * - Header (4 bytes): version|headerSize, msgType|flags, serialization|compression, reserved
 * - Payload Size (4 bytes, big endian uint32)
 * - Payload (JSON bytes)
 * 
 * Note: NO sequence field for NoSeq flag!
 */
export function buildFullClientRequest(
    payload: any,
    seq: number = 0,
    enableGzip: boolean = false
): Uint8Array {
    const header = createHeader(
        MessageType.CLIENT_FULL_REQUEST,
        MessageTypeSpecificFlags.NO_SEQUENCE,
        SerializationType.JSON,
        CompressionType.NO_COMPRESSION
    );

    const payloadStr = JSON.stringify(payload);
    const payloadBytes = new TextEncoder().encode(payloadStr);
    const payloadSize = payloadBytes.length;

    // Frame format: header(4) + payloadSize(4) + payload
    // NO sequence field for NoSeq!
    const buffer = new ArrayBuffer(4 + 4 + payloadSize);
    const view = new DataView(buffer);

    new Uint8Array(buffer).set(header, 0);
    view.setUint32(4, payloadSize, false); // big endian
    new Uint8Array(buffer).set(payloadBytes, 8);

    console.log(`[Protocol] Built FullClientRequest: ${buffer.byteLength} bytes`);
    return new Uint8Array(buffer);
}

/**
 * Build an AudioOnlyRequest frame for ASR audio streaming.
 * 
 * VolcEngine protocol format for AudioOnlyClient with sequence:
 * - Header (4 bytes)
 * - Sequence (4 bytes, signed int32, big endian) - negative if last
 * - Payload Size (4 bytes, big endian uint32)
 * - Payload (audio data)
 */
export function buildAudioOnlyRequest(
    audioData: Uint8Array,
    seq: number,
    isLast: boolean
): Uint8Array {
    const flags = isLast ? MessageTypeSpecificFlags.NEG_WITH_SEQUENCE : MessageTypeSpecificFlags.POS_SEQUENCE;

    const header = createHeader(
        MessageType.CLIENT_AUDIO_ONLY_REQUEST,
        flags,
        SerializationType.NO_SERIALIZATION,
        CompressionType.NO_COMPRESSION
    );

    const finalSeq = isLast ? -seq : seq;
    const payloadSize = audioData.length;

    // Frame format: header(4) + seq(4) + payloadSize(4) + payload
    const buffer = new ArrayBuffer(4 + 4 + 4 + payloadSize);
    const view = new DataView(buffer);

    new Uint8Array(buffer).set(header, 0);
    view.setInt32(4, finalSeq, false); // signed int32, big endian
    view.setUint32(8, payloadSize, false); // big endian
    new Uint8Array(buffer).set(audioData, 12);

    return new Uint8Array(buffer);
}

// Response Parser
export interface ParsedResponse {
    messageType: MessageType;
    payload: any;
    seq: number;
    isLast: boolean;
}

export function parseResponse(data: ArrayBuffer): ParsedResponse | null {
    if (data.byteLength < 8) {
        console.warn("[Protocol] Response too short:", data.byteLength);
        return null;
    }

    const view = new DataView(data);
    const headerArr = new Uint8Array(data.slice(0, 4));

    const version = (headerArr[0] >> 4) & 0x0F;
    const headerSize = headerArr[0] & 0x0F;
    const messageType = (headerArr[1] >> 4) & 0x0F;
    const flags = headerArr[1] & 0x0F;
    const serialization = (headerArr[2] >> 4) & 0x0F;
    const compression = headerArr[2] & 0x0F;

    const actualHeaderSize = headerSize * 4;
    let cursor = actualHeaderSize;
    let seq = 0;
    let isLast = false;

    // Read sequence if flags indicate it
    if (flags === MessageTypeSpecificFlags.POS_SEQUENCE ||
        flags === MessageTypeSpecificFlags.NEG_SEQUENCE ||
        flags === MessageTypeSpecificFlags.NEG_WITH_SEQUENCE) {
        if (data.byteLength < cursor + 4) {
            console.warn("[Protocol] Response too short for sequence");
            return null;
        }
        seq = view.getInt32(cursor, false);
        cursor += 4;

        if (seq < 0) {
            isLast = true;
        }
    }

    // Read payload size
    if (data.byteLength < cursor + 4) {
        console.warn("[Protocol] Response too short for payload size");
        return null;
    }
    const payloadSize = view.getUint32(cursor, false);
    cursor += 4;

    // Read payload
    if (data.byteLength < cursor + payloadSize) {
        console.warn("[Protocol] Response too short for payload");
        return null;
    }
    const payloadBytes = new Uint8Array(data.slice(cursor, cursor + payloadSize));

    // Parse based on message type
    if (messageType === MessageType.SERVER_FULL_RESPONSE) {
        // JSON payload
        if (compression === CompressionType.GZIP) {
            console.warn("[Protocol] Received GZIP payload, cannot decompress");
            return null;
        }

        const textStruct = new TextDecoder().decode(payloadBytes);
        try {
            return { messageType, payload: JSON.parse(textStruct), seq, isLast };
        } catch (e) {
            console.error("[Protocol] JSON Parse Error", e);
            return null;
        }
    } else if (messageType === MessageType.SERVER_ACK) {
        // Audio payload
        return { messageType, payload: payloadBytes, seq, isLast };
    } else if (messageType === MessageType.SERVER_ERROR_RESPONSE) {
        // Error response
        const textStruct = new TextDecoder().decode(payloadBytes);
        console.error("[Protocol] Server error:", textStruct);
        return { messageType, payload: textStruct, seq, isLast: true };
    }

    // Generic fallback
    return { messageType, payload: payloadBytes, seq, isLast };
}
