ks_ct = bytes.fromhex("46D86DEBF45715C49F7F36C230452ECB")
vault = bytes.fromhex("178B3EBEB7141FD4F30352B64F4B2FF8119130FBA808469FE91A55B4454837D2148438FBAF025CCEF30955B74F4D26D2058130FBB40E4BCEF31A58B74E4837D21A892DAFAB171FD4E20E53B44B4920C5")

xor = lambda a, b: bytes(x ^ y for x, y in zip(a, b))

for pt in (b"LEVEL99900000000", b"00000000LEVEL999"):
    key = xor(ks_ct, pt)
    print(pt, key.hex())
    for i in range(0, len(vault), 16):
        print("   ", xor(vault[i:i+16], key))
