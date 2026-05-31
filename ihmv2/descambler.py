def descrambler(input_bytes: bytes) -> bytes:
    """
    Descrambler G3RUH – état initial à zéro.
    Inverse du scrambler appliqué côté satellite.

    Le scrambler G3RUH est auto-synchronisant : le bit de rétroaction
    est le bit d'ENTRÉE (reçu/scramblé), et non le bit de sortie.
    Cela permet de reconstruire l'état du registre à partir des données
    reçues et de retrouver le flux original.

    Taps : positions 5, 12, 16  (indices 4, 11, 15 dans le tableau)
    Longueur du registre : 17 bits
    """
    s = [0] * 17  # état initial : tous bits à 0
    output = bytearray()

    for byte in input_bytes:
        descrambled_byte = 0

        for i in range(7, -1, -1):  # MSB first
            s_bit = (byte >> i) & 1          # bit reçu (scramblé) = entrée du registre

            # Reconstruction du bit original :
            # scrambler : s_out = bit_original ^ s[4] ^ s[11] ^ s[15]
            # donc       : bit_original = s_out ^ s[4] ^ s[11] ^ s[15]
            # avec s_out = s_bit (car c'est ce bit qui a été mis dans le registre)
            # Attention : ici on lit l'état AVANT de décaler
            original_bit = s_bit ^ s[4] ^ s[11] ^ s[15]

            descrambled_byte = (descrambled_byte << 1) | original_bit

            # Décalage du registre et rétroaction avec le bit REÇU (scramblé)
            s[1:17] = s[0:16]
            s[0] = s_bit

        output.append(descrambled_byte)

    return bytes(output)


# Exemple : décoder le payload d'une trame AX.25 SPINO reçue
# payload_scrambled = bytes([0xAB, 0xCD, ...])  # bytes extraits de la trame
# payload_original = descrambler(payload_scrambled)
# print(payload_original.decode("ascii"))
