#!/usr/bin/env python3
"""
Decode the /vault blob: hex string where each byte is Gray-coded (g = b ^ (b >> 1)).

  python3 gray_decode.py 4b4f59304e5c5d4a...
  python3 gray_decode.py            # then paste the hex and press Enter
  python3 gray_decode.py -e "text"  # encode (to sanity-check)
"""
import re, sys


def gray_decode(g):
    b = g
    for s in (1, 2, 4):
        b ^= b >> s
    return b


def main():
    args = sys.argv[1:]
    if args[:1] == ["-e"]:
        text = " ".join(args[1:]).encode()
        print("".join("%02x" % (b ^ (b >> 1)) for b in text))
        return
    blob = " ".join(args) if args else input("hex> ")
    blob = re.sub(r"[^0-9a-fA-F]", "", blob)  # tolerate spaces/newlines/0x
    if len(blob) % 2:
        sys.exit("odd number of hex digits — did the copy get cut off?")
    print(bytes(gray_decode(g) for g in bytes.fromhex(blob)).decode(errors="replace"))


if __name__ == "__main__":
    main()
