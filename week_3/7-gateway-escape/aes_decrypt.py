#!/usr/bin/env python3
# AES-256-CBC, IV = first 16 bytes of the file, PKCS#7 padding
import sys
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

enc = "log_055.enc"
key_hex = "ad6d69bc2a2afd7cffec3094baad96d4abb048e19628c628780835a1420367be"
key = bytes.fromhex(key_hex)

data = open(enc, "rb").read()
iv, ct = data[:16], data[16:]

dec = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
pt = dec.update(ct) + dec.finalize()

unpad = padding.PKCS7(128).unpadder()
pt = unpad.update(pt) + unpad.finalize()

open(enc.replace(".enc", ".csv"), "wb").write(pt)
print(pt[:200].decode())
