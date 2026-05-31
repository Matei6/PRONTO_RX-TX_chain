"""
uplink.py - TX command handling for FOSM-1
"""

import threading
import time
from pathlib import Path
from typing import Optional
import zmq

from config import (
    ZMQ_TX_URL,
    UPLINK_SEND_REPEAT,
    UPLINK_COMMANDS_DIR,
    UPLINK_DEFAULT_CALLSIGN,
    zmq_context,
)
from utils import (
    tx_crc_spino,
    string_to_shifted_bytes,
    normalize_callsign,
    parse_hex_command,
    read_command_bytes_from_file,
)


# Global state for persistent uplink socket
uplink_lock = threading.Lock()
uplink_socket = None


def build_uplink_frame(command: bytes, operator_callsign: str) -> bytes:
    """
    Build an AX.25-like TX frame in the SPINO format.
    
    Frame structure:
    - Preamble (16x 0xAA)
    - Sync (0x2E 0xFC 0x98 0x27)
    - Header (dest, src, ctrl, pid)
    - Length field
    - Command payload
    - CRC-16/XMODEM (big endian)
    """
    preamble = bytes([0xAA] * 16)
    sync = bytes([0x2E, 0xFC, 0x98, 0x27])

    emitter = string_to_shifted_bytes(operator_callsign) + b'\x02'
    receiver = string_to_shifted_bytes("FOSM1D") + b'\x1E'
    control_field = bytes([0x03])
    protocol_id = bytes([0xF0])
    header = receiver + emitter + control_field + protocol_id
    length_field = (len(command)).to_bytes(2, byteorder="little")
    data_to_crc = tx_crc_spino(header + length_field + command)

    return preamble + sync + header + length_field + command + data_to_crc


def get_available_uplink_commands() -> list[str]:
    """Get list of available command files from the commands directory."""
    if not UPLINK_COMMANDS_DIR.is_dir():
        return []
    return sorted([
        file_path.name
        for file_path in UPLINK_COMMANDS_DIR.iterdir()
        if file_path.is_file() and file_path.suffix.lower() == ".txt"
    ])


def resolve_command_file(command_name: str) -> Optional[Path]:
    """Resolve a command name to its file path (case-insensitive matching)."""
    available = get_available_uplink_commands()
    if not available:
        return None

    wanted = command_name.strip()
    candidates = [wanted]
    if not wanted.lower().endswith(".txt"):
        candidates.append(f"{wanted}.txt")

    available_lower = {name.lower(): name for name in available}
    for candidate in candidates:
        match = available_lower.get(candidate.lower())
        if match:
            return UPLINK_COMMANDS_DIR / match

    return None


def send_uplink_bytes(command_bytes: bytes, operator_callsign: str) -> int:
    """
    Send command bytes over ZMQ (PUSH socket).
    Uses a persistent socket to avoid losing the first message.
    """
    global uplink_socket

    frame = build_uplink_frame(command_bytes, operator_callsign)

    with uplink_lock:
        if uplink_socket is None:
            uplink_socket = zmq_context.socket(zmq.PUSH)
            uplink_socket.connect(ZMQ_TX_URL)

        for _ in range(UPLINK_SEND_REPEAT):
            uplink_socket.send(frame)
            print(f"[TX] Sent frame of length {len(frame)} bytes : {frame.hex(' ').upper()}")
            time.sleep(0.1)

    return len(frame)


def is_uplink_socket_open() -> bool:
    """Check if uplink socket is open."""
    return uplink_socket is not None


def close_uplink_socket() -> None:
    """Close the persistent uplink socket if it exists."""
    global uplink_socket

    with uplink_lock:
        if uplink_socket is not None:
            try:
                uplink_socket.close(linger=0)
            finally:
                uplink_socket = None
