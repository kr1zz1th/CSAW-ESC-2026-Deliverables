import time
import serial

PORT = '/dev/ttyUSB0'
BAUD = 115200

# How long to wait for the boot banner to finish before trusting the port
BOOT_SETTLE = 2.0
BOOT_MIN_WAIT = 1.0

# How long to wait for a response to each command before moving on
READ_TIMEOUT = 0.2

# Small pause between commands so late output doesn't leak into the next one
INTER_CMD_DELAY = 0.1


def wait_for_quiet(ser, quiet_for=0.3, max_wait=3.0):
    """Block until the serial line has been silent for `quiet_for` seconds,
    or until max_wait elapses. Drains/prints whatever comes through."""
    start = time.time()
    last_byte_time = time.time()

    while time.time() - start < max_wait:
        if ser.in_waiting:
            chunk = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
            if chunk:
                print(chunk, end='', flush=True)
            last_byte_time = time.time()
        elif time.time() - last_byte_time >= quiet_for:
            return
        time.sleep(0.02)


def send_command(ser, command):
    """Sends a single command and prints all serial output received
    within READ_TIMEOUT of silence."""
    print(f"\n[>] Sending: {command}")
    print("-" * 50)

    ser.reset_input_buffer()
    payload = f"{command}\n"
    ser.write(payload.encode('utf-8'))
    ser.flush()

    start_time = time.time()
    last_byte_time = time.time()
    got_any = False

    while True:
        if ser.in_waiting:
            chunk = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
            if chunk:
                print(chunk, end='', flush=True)
                got_any = True
            last_byte_time = time.time()
        else:
            # Stop once we've been quiet for READ_TIMEOUT, or hit an absolute cap
            if got_any and (time.time() - last_byte_time) >= READ_TIMEOUT:
                break
            if time.time() - start_time >= (READ_TIMEOUT * 3):
                break
            time.sleep(0.01)

    if not got_any:
        print("[!] No response received.")
    print("-" * 50)
    time.sleep(INTER_CMD_DELAY)


def main():
    try:
        ser = serial.Serial(PORT, BAUD, timeout=0.2)
    except Exception as e:
        print(f"Error opening serial port: {e}")
        return

    print("[*] Waiting for initial boot banner to settle...")
    time.sleep(BOOT_MIN_WAIT)
    wait_for_quiet(ser, quiet_for=0.3, max_wait=BOOT_SETTLE)
    ser.reset_input_buffer()

    # Enter developer/command mode
    send_command(ser, "mode developer --help")
    send_command(ser, "212090")

    # Send log1 through log100
    for i in range(1, 101):
        send_command(ser, f"log{i}")

    print("\n[*] Done. Sent mode developer --help and log1..log100.")
    ser.close()


if __name__ == "__main__":
    main()
