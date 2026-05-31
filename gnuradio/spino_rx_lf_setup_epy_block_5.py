import numpy as np
from gnuradio import gr
import pmt
import struct

class burst_to_pdu(gr.basic_block):
    def __init__(self, max_len=2064):
        gr.basic_block.__init__(
            self,
            name="burst_to_pdu",
            in_sig=[np.uint8],
            out_sig=[]
        )
        self.max_len = max_len
        self.buffer = []
        self.in_burst = False
        self.expected_len = None   # taille exacte attendue en bits, None = pas encore connue
        self.message_port_register_out(pmt.intern("out"))

    def _bits_to_byte(self, bits):
        """Convertit 8 bits (MSB first) en un entier."""
        val = 0
        for b in bits:
            val = (val << 1) | int(b)
        return val

    def _read_payload_len(self):
        """
        Lit le champ longueur (bits 128..143, Little Endian).
        Retourne le nombre total de bits attendus pour la trame complète,
        ou None si le buffer n'est pas encore assez long.
        """
        if len(self.buffer) < 144:
            return None

        # Lire les 2 octets de longueur (bits 128..143)
        byte_lo = self._bits_to_byte(self.buffer[128:136])  # LSB
        byte_hi = self._bits_to_byte(self.buffer[136:144])  # MSB
        payload_len = struct.unpack("<H", bytes([byte_lo, byte_hi]))[0]

        # Taille totale = 16 octets header + 2 octets len + payload + 2 octets CRC
        total_bytes = 16 + 2 + payload_len + 2
        total_bits  = total_bytes * 8

        # Sanité : refuser les longueurs aberrantes
        if total_bits > self.max_len or payload_len > 222:
            print(f"[burst_to_pdu] LEN aberrante : {payload_len} → fallback max_len")
            return self.max_len

        return total_bits

    def general_work(self, input_items, output_items):
        in0 = input_items[0]
        nitems = len(in0)

        tags = self.get_tags_in_window(0, 0, nitems)
        tag_offsets = set(
            tag.offset - self.nitems_read(0) for tag in tags
            if pmt.symbol_to_string(tag.key) == "burst"
        )

        for i in range(nitems):
            if i in tag_offsets:
                # Nouveau burst : envoyer l'éventuel burst en cours
                if self.in_burst and len(self.buffer) > 10:
                    print(f"[burst_to_pdu] Buffer final : {len(self.buffer)} bits")
                    print(f"Derniers 32 bits : {self.buffer[-32:]}")
                    self.send_pdu()
                self.buffer = []
                self.in_burst = True
                self.expected_len = None  # on ne connaît pas encore la taille

            if self.in_burst:
                self.buffer.append(int(in0[i]))

                # Dès qu'on a 144 bits, on peut lire la longueur
                if self.expected_len is None and len(self.buffer) >= 144:
                    self.expected_len = self._read_payload_len()
                    print(f"[burst_to_pdu] Taille lue : {self.expected_len} bits")

                # Couper exactement quand on a tous les bits attendus
                target = self.expected_len if self.expected_len else self.max_len
                if len(self.buffer) >= target:
                    self.buffer = self.buffer[:target]  # tronquer proprement
                    print(f"[burst_to_pdu] Buffer final : {len(self.buffer)} bits")
                    print(f"Derniers 32 bits : {self.buffer[-32:]}")
                    self.send_pdu()
                    self.buffer = []
                    self.in_burst = False
                    self.expected_len = None

        self.consume(0, nitems)
        return 0

    def send_pdu(self):
        if len(self.buffer) > 10:
            vec = pmt.init_u8vector(len(self.buffer), self.buffer)
            pdu = pmt.cons(pmt.PMT_NIL, vec)
            self.message_port_pub(pmt.intern("out"), pdu)
        self.buffer = []
