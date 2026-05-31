"""
downlink.py - RX frame parsing and ZMQ listening for FOSM-1
"""

import struct
from datetime import datetime
from flask_socketio import SocketIO

from descambler import descrambler
from utils import crc_spino


def bits_to_bytes_msb(bits: list) -> bytearray:
    """Convert bit list to bytes (MSB first)."""
    n = len(bits) - (len(bits) % 8)
    raw = bytearray()
    for i in range(0, n, 8):
        byte_val = 0
        for bit in bits[i:i+8]:
            byte_val = (byte_val << 1) | int(bit)
        raw.append(byte_val)
    return raw


def find_best_alignment(bits: list, expected_bytes: int) -> list | None:
    """Sliding window search for valid CRC alignment."""
    target = expected_bytes * 8
    for start in range(min(17, len(bits) - target + 1)):
        candidate = bits[start:start + target]
        if len(candidate) < target:
            break
        raw = bits_to_bytes_msb(candidate)
        if len(raw) < 20:
            continue
        try:
            payload_len = struct.unpack_from("<H", raw, 16)[0]
            if payload_len > 222:
                continue
            data_end = 18 + payload_len
            if data_end + 2 > len(raw):
                continue
            crc_c = crc_spino(bytes(raw[:data_end]))
            crc_r = struct.unpack_from(">H", raw, data_end)[0]
            if crc_c == crc_r:
                return candidate
        except (struct.error, IndexError):
            continue
    return None


def parse_spino_frame(bits: list) -> dict | None:
    """
    Parse an AX.25 SPINO frame.
    Supports SPINO frames (with length) and Beacon UI (without length).
    """
    raw_full = bits_to_bytes_msb(bits)
    if len(raw_full) < 16:
        return None

    ctrl = raw_full[14]
    pid = raw_full[15]
    dest = "".join(chr(b >> 1) for b in raw_full[0:7]).strip().rstrip('\x00')
    src = "".join(chr(b >> 1) for b in raw_full[7:14]).strip().rstrip('\x00')
    raw_hex = ' '.join(f'{b:02X}' for b in raw_full)

    # ── Beacon UI AX.25 (no length field) ──────────────────────────────
    if ctrl == 0x04 and pid == 0xF0:
        payload = raw_full[16:]
        msg_ascii = payload.decode('ascii', errors='replace').rstrip('\x00')

        try:
            descrambled = descrambler(payload)
            descrambled_ascii = descrambled.decode('ascii', errors='replace')
        except Exception:
            descrambled_ascii = None

        return {
            'type': 'beacon',
            'dest': dest,
            'src': src,
            'ctrl': f'{ctrl:02X}',
            'pid': f'{pid:02X}',
            'length': None,
            'payload': payload.hex(' ').upper(),
            'payload_ascii': msg_ascii,
            'descrambled_payload': descrambled.hex(' ').upper() if descrambled else None,
            'descrambled_payload_ascii': descrambled_ascii,
            'crc': None,
            'crc_ok': None,
            'raw': raw_hex,
            'timestamp': datetime.now().strftime('%H:%M:%S'),
        }

    # ── SPINO frame with length field ──────────────────────────────────
    if len(raw_full) < 18:
        return None

    try:
        payload_len = struct.unpack_from("<H", raw_full, 16)[0]
    except struct.error:
        return None

    expected_bytes = 18 + payload_len + 2

    # Attempt alignment correction if CRC is invalid
    aligned_bits = find_best_alignment(bits, expected_bytes)
    raw = bits_to_bytes_msb(aligned_bits) if aligned_bits else raw_full

    if len(raw) < expected_bytes:
        return None

    dest = "".join(chr(b >> 1) for b in raw[0:7]).strip().rstrip('\x00')
    src = "".join(chr(b >> 1) for b in raw[7:14]).strip().rstrip('\x00')
    ctrl = raw[14]
    pid = raw[15]
    data_end = 18 + payload_len
    payload = raw[18:data_end]

    crc_computed = crc_spino(bytes(raw[:data_end]))
    try:
        crc_received = struct.unpack_from(">H", raw, data_end)[0]
    except struct.error:
        return None

    crc_ok = (crc_computed == crc_received)

    if not crc_ok:
        print(f"[CRC] ❌ computed={crc_computed:04X} received={crc_received:04X}")

    try:
        payload_ascii = payload.decode('ascii', errors='replace')
    except Exception:
        payload_ascii = None

    try:
        descrambled = descrambler(payload)
        descrambled_ascii = descrambled.decode('ascii', errors='replace')
    except Exception:
        descrambled = None
        descrambled_ascii = None

    return {
        'type': 'spino',
        'dest': dest,
        'src': src,
        'ctrl': f'{ctrl:02X}',
        'pid': f'{pid:02X}',
        'length': payload_len,
        'payload': payload.hex(' ').upper(),
        'payload_ascii': payload_ascii,
        'descrambled_payload': descrambled.hex(' ').upper() if descrambled else None,
        'descrambled_payload_ascii': descrambled_ascii,
        'crc': f'{crc_received:04X}',
        'crc_ok': crc_ok,
        'raw': ' '.join(f'{b:02X}' for b in raw),
        'timestamp': datetime.now().strftime('%H:%M:%S'),
    }


def zmq_listener_thread(socketio: SocketIO, recording_callback, zmq_url: str, pmt):
    """
    Background thread that listens to GNU Radio telemetry via ZMQ.
    Emits decoded frames to all connected browsers via WebSocket.
    """
    import zmq as zmq_module
    
    context = zmq_module.Context()
    sock = context.socket(zmq_module.SUB)
    sock.connect(zmq_url)
    sock.setsockopt_string(zmq_module.SUBSCRIBE, "")
    print(f"[ZMQ RX] Listening on {zmq_url}")

    while True:
        try:
            raw_pdu = sock.recv()
            pmt_msg = pmt.deserialize_str(raw_pdu)

            if not pmt.is_pair(pmt_msg):
                continue
            data_pmt = pmt.cdr(pmt_msg)
            if not pmt.is_u8vector(data_pmt):
                continue

            bits = list(pmt.u8vector_elements(data_pmt))
            frame = parse_spino_frame(bits)

            if frame:
                socketio.emit('new_telemetry', frame)
                recording_callback(frame['raw'])
                print(f"[RX] {frame['src']} → {frame['dest']} | "
                      f"type={frame['type']} | crc={frame.get('crc', 'N/A')}")

        except Exception as e:
            print(f"[ZMQ RX ERR] {e}")
