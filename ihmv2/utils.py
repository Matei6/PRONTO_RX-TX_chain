"""
utils.py - Utility functions for FOSM-1 Ground Station
"""

import socket
from pathlib import Path
from typing import Optional


def crc_spino(data: bytes) -> int:
    """
    CRC-16/XMODEM for RX frame validation
    - poly=0x1021, init=0x0000
    - MSB first (no reflect)
    - final XOR=0x0000
    """
    crc = 0x0000
    for byte in data:
        crc ^= (byte << 8)
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if (crc & 0x8000) else (crc << 1)
            crc &= 0xFFFF
    return crc


def tx_crc_spino(data: bytes) -> bytes:
    """Return CRC-16/XMODEM (big endian) for TX frames."""
    crc = 0x0000
    for byte in data:
        crc ^= (byte << 8)
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if (crc & 0x8000) else (crc << 1)
            crc &= 0xFFFF
    return bytes([(crc >> 8) & 0xFF, crc & 0xFF])


def string_to_shifted_bytes(text: str, left_shift: int = 1) -> bytes:
    """Convert string to shifted bytes (AX.25 encoding)."""
    shifted_bytes = bytearray()
    for char in text:
        shifted_bytes.append((ord(char) << left_shift) & 0xFF)
    return bytes(shifted_bytes)


def normalize_callsign(callsign: Optional[str], default: str = "F4AKAG") -> str:
    """Normalize a callsign to uppercase and apply default if empty."""
    value = (callsign or default).strip().upper()
    return value if value else default


def parse_hex_command(command_text: str) -> bytes:
    """Parse hexadecimal command from various formats."""
    cleaned = command_text.replace(",", " ").strip()
    if not cleaned:
        raise ValueError("Empty command")

    tokens = cleaned.split()
    if all(len(token) == 2 for token in tokens):
        return bytes(int(token, 16) for token in tokens)

    if len(cleaned) % 2 != 0:
        raise ValueError("Hex command must contain an even number of hex characters")

    return bytes.fromhex(cleaned)


def read_command_bytes_from_file(file_path: Path) -> bytes:
    """Read and parse command bytes from a file."""
    content = file_path.read_text(encoding="utf-8").strip()
    return parse_hex_command(content)


def probe_tcp_port(host: str, port: int, timeout: float = 1.0) -> bool:
    """Check if a TCP port is open and responding."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False
