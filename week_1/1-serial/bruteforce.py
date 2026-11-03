import time
import serial

PORT = '/dev/ttyUSB0'
BAUD = 115200

# Supported character set accepted by the CLI interface
CHARS_TO_TEST = "abcdefghijklmnopqrstuvwxyz !@-_"

# Read timeout per candidate (increased from 0.5s)
READ_TIMEOUT = 0.9

# Small pause after each candidate so late output can't leak into the next one
INTER_CANDIDATE_DELAY = 0.15

# How long to wait for the boot banner to finish before trusting the port
BOOT_SETTLE = 4.0

# Always wait this long after a reset before even checking for quiet
BOOT_MIN_WAIT = 1.5


def wait_for_quiet(ser, quiet_for=0.6, max_wait=3.0):
    """Block until the serial line has been silent for `quiet_for` seconds,
    or until max_wait elapses."""
    start = time.time()
    last_byte_time = time.time()

    while time.time() - start < max_wait:
        if ser.in_waiting:
            ser.read(ser.in_waiting)  # drain whatever boot text is there
            last_byte_time = time.time()
        elif time.time() - last_byte_time >= quiet_for:
            return
        time.sleep(0.02)


def reset_esp32(ser):
    """Triggers a hardware reset using DTR/RTS serial control lines,
    then waits for the boot banner to finish."""
    print("\n[*] Triggering hardware reset (8-attempt threshold reached)...")
    ser.reset_input_buffer()
    ser.setDTR(False)
    ser.setRTS(True)
    time.sleep(0.5)
    ser.setRTS(False)

    # Boot output can take a moment to even start, so wait first
    time.sleep(BOOT_MIN_WAIT)
    wait_for_quiet(ser, quiet_for=0.6, max_wait=BOOT_SETTLE)
    ser.reset_input_buffer()
    time.sleep(0.3)


def test_candidate(ser, candidate, attempt_counter):
    """Sends a candidate string and checks if it returns a valid prefix match.
    Manages the strict 8-attempt reset counter."""
    print(f"Testing candidate: '{candidate}'".ljust(50), end="\r", flush=True)

    # Clear anything left over from the previous candidate
    wait_for_quiet(ser, quiet_for=0.1, max_wait=0.5)
    ser.reset_input_buffer()

    payload = f"{candidate}\n"
    ser.write(payload.encode('utf-8'))
    ser.flush()
    attempt_counter[0] += 1

    start_time = time.time()
    valid_prefix_matched = False
    buf = ""

    while time.time() - start_time < READ_TIMEOUT:
        if ser.in_waiting:
            buf += ser.read(ser.in_waiting).decode('utf-8', errors='ignore')

            if "one or more commands start with" in buf:
                valid_prefix_matched = True
                break
        else:
            time.sleep(0.01)

    # Let the rest of the reply finish arriving before moving on
    time.sleep(INTER_CANDIDATE_DELAY)

    # Reset hardware strictly every 8 attempts (unchanged behavior)
    if attempt_counter[0] >= 8:
        reset_esp32(ser)
        attempt_counter[0] = 0

    return valid_prefix_matched


def dfs_enumerate(ser, current_prefix, attempt_counter, discovered_commands):
    """Recursively explores command branches (DFS).
    Backtracks when a character branch yields no further sub-matches."""
    has_children = False

    for c in CHARS_TO_TEST:
        candidate = current_prefix + c

        if test_candidate(ser, candidate, attempt_counter):
            has_children = True
            print(f"\n[+] Valid prefix confirmed: '{candidate}'")

            # Recurse deeper into this branch
            dfs_enumerate(ser, candidate, attempt_counter, discovered_commands)

    # If this prefix matched but had no child extensions, it is a terminal command
    if not has_children and current_prefix:
        print(f"\n[!] Discovered complete command: '{current_prefix}'")
        discovered_commands.append(current_prefix)


def main():
    try:
        ser = serial.Serial(PORT, BAUD, timeout=0.2)
    except Exception as e:
        print(f"Error opening serial port: {e}")
        return

    # Opening the port typically toggles DTR/RTS on ESP32 boards (auto-reset),
    # so wait for the initial boot banner to finish before enumerating.
    print("[*] Waiting for initial boot banner to settle...")
    time.sleep(BOOT_MIN_WAIT)
    wait_for_quiet(ser, quiet_for=0.6, max_wait=BOOT_SETTLE)
    ser.reset_input_buffer()
    time.sleep(0.3)

    attempt_counter = [0]  # List wrapper used for mutable counter across recursion
    discovered_commands = []

    print("[*] Starting DFS prefix enumeration with backtracking...")

    # Start top-level DFS exploration
    dfs_enumerate(ser, "", attempt_counter, discovered_commands)

    print("\n" + "=" * 50)
    print("[*] DFS Enumeration Complete.")
    print(f"Discovered Commands ({len(discovered_commands)}):")
    for cmd in discovered_commands:
        print(f" - {cmd}")
    print("=" * 50)

    ser.close()


if __name__ == "__main__":
    main()
