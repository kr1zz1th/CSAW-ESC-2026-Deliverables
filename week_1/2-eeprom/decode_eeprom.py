# Output of `get_mac` on the board - this is the XOR key
MAC = "FC:B4:67:21:20:90"

# Paste the `dump_eeprom` output here
DUMP = """
0010: B0 DB 05 43 59 CF BB E3 67 21 20 90 EC 94 57 20 
0020: 6F F6 9A DD 04 44 7F D7 AB B4 67 21 01 B0 6C B6 
0030: 21 4D 4F FF 8E 85 38 66 77 90 FC B4 23 74 46 93 
0040: BA D8 08 4E 52 A2 A3 F3 30 21 20 90 8B 3C FE 22 
0050: 73 F5 8E C2 02 53 7F D7 AB B4 67 21 A8 09 56 B1 
0060: 34 55 4F E2 9D D3 02 7E 67 C7 FC B4 76 03 13 91 
0070: B1 D5 14 55 45 E2 A3 F3 30 21 20 90 4E 94 53 B8 
0080: 67 F1 8E D5 00 44 7F D7 AB B4 67 21 FE 3D 42 B6 
0090: 20 40 52 F4 99 DA 38 66 77 90 FC B4 32 47 57 91 
00A0: AA D5 12 4D 54 CF BB E3 67 21 20 90 02 59 9D 31 
00B0: 8C 8D 8E 8F 88 89 8A 8B 84 85 86 87 80 81 82 83 
00C0: FC FD FE FF F8 F9 FA FB F4 F5 F6 F7 F0 F1 F2 F3 
00D0: EC ED EE EF E8 E9 EA EB E4 E5 E6 E7 E0 E1 E2 E3 
00E0: DC DD DE DF D8 D9 DA DB D4 D5 D6 D7 D0 D1 D2 D3 
00F0: CC CD CE CF C8 C9 CA CB C4 C5 C6 C7 C0 C1 C2 C3 
"""

key = bytes.fromhex(MAC.replace(":", ""))

# Join the hex bytes, dropping the "0010:" address at the start of each line
data = bytes.fromhex("".join(line.split(":")[1] for line in DUMP.strip().splitlines()))

# XOR with the MAC, repeating every 6 bytes
decoded = bytes(b ^ key[i % 6] for i, b in enumerate(data))

# Print 16 bytes per line: hex and ASCII
for i in range(0, len(decoded), 16):
    row = decoded[i:i + 16]
    text = "".join(chr(c) if 32 <= c < 127 else "." for c in row)
    print(f"{0x10 + i:04X}: {row.hex(' ').upper()}  {text}")

