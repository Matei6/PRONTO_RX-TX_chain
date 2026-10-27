import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "ihmv2"))

from downlink import parse_spino_frame
from uplink import build_uplink_frame
from utils import (
    crc_spino,
    parse_hex_command,
    string_to_shifted_bytes,
    tx_crc_spino,
)


def bytes_to_bits(data: bytes) -> list[int]:
    return [
        (byte >> bit_position) & 1
        for byte in data
        for bit_position in range(7, -1, -1)
    ]


def build_spino_rx_frame(payload: bytes) -> bytes:
    destination = string_to_shifted_bytes("FOSM1D") + b"\x1e"
    source = string_to_shifted_bytes("N0CALL") + b"\x02"
    header = destination + source + b"\x03\xf0"
    body = header + len(payload).to_bytes(2, "little") + payload
    return body + tx_crc_spino(body)


class HexCommandTests(unittest.TestCase):
    def test_parses_spaced_and_comma_separated_bytes(self):
        self.assertEqual(parse_hex_command("AA BB, CC"), b"\xaa\xbb\xcc")

    def test_parses_contiguous_hex(self):
        self.assertEqual(parse_hex_command("AABBCC"), b"\xaa\xbb\xcc")

    def test_rejects_empty_and_odd_length_commands(self):
        for command in ("", "ABC"):
            with self.subTest(command=command):
                with self.assertRaises(ValueError):
                    parse_hex_command(command)


class CrcTests(unittest.TestCase):
    def test_crc_matches_xmodem_check_value(self):
        self.assertEqual(crc_spino(b"123456789"), 0x31C3)
        self.assertEqual(tx_crc_spino(b"123456789"), b"\x31\xc3")


class UplinkFrameTests(unittest.TestCase):
    def test_builds_frame_with_expected_fields_and_crc(self):
        command = b"\xaa\x55"
        frame = build_uplink_frame(command, "N0CALL")
        prefix = b"\xaa" * 16 + b"\x2e\xfc\x98\x27"
        body = frame[len(prefix):-2]

        self.assertTrue(frame.startswith(prefix))
        self.assertEqual(body[:7], string_to_shifted_bytes("FOSM1D") + b"\x1e")
        self.assertEqual(body[7:14], string_to_shifted_bytes("N0CALL") + b"\x02")
        self.assertEqual(body[14:16], b"\x03\xf0")
        self.assertEqual(body[16:18], len(command).to_bytes(2, "little"))
        self.assertEqual(body[18:], command)
        self.assertEqual(int.from_bytes(frame[-2:], "big"), crc_spino(body))


class DownlinkFrameTests(unittest.TestCase):
    def test_decodes_valid_spino_frame(self):
        payload = b"telemetry"
        frame = parse_spino_frame(bytes_to_bits(build_spino_rx_frame(payload)))

        self.assertIsNotNone(frame)
        self.assertEqual(frame["type"], "spino")
        self.assertEqual(frame["length"], len(payload))
        self.assertEqual(frame["payload_ascii"], payload.decode("ascii"))
        self.assertTrue(frame["crc_ok"])

    def test_marks_corrupt_spino_crc_as_invalid(self):
        raw_frame = bytearray(build_spino_rx_frame(b"telemetry"))
        raw_frame[-1] ^= 0x01

        frame = parse_spino_frame(bytes_to_bits(bytes(raw_frame)))

        self.assertIsNotNone(frame)
        self.assertFalse(frame["crc_ok"])

    def test_rejects_frame_shorter_than_header(self):
        frame = parse_spino_frame(bytes_to_bits(b"\x00" * 15))

        self.assertIsNone(frame)


if __name__ == "__main__":
    unittest.main()