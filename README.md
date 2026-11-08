# CSAW ESC 2026 — Final Phase Deliverables

Team **Fugazi** — Cybersecurity Club, IIT Madras.

Every challenge was solved **black-box**, through the interfaces an attacker
would really have: the UART console, the gateway's Wi-Fi AP and its UDP and HTTP
services, BLE, the MFRC522 RFID reader and the I²C EEPROM. No flag was obtained
by reverse engineering the provided binaries, and every script here talks only
to the board's external interfaces.

## Results

| # | Challenge | Pts | Flag |
|---|---|---|---|
| 0 | Built-in Self-Test | — | `esc_2026{hw_s3lft3st_p4ss_ea5y}` |
| 1 | Serial Gateway | 100 | `esc_2026{Challenge_1_UART_cli_a1a23ee935f7d98e}` |
| 2 | EEPROM Secrets | 200 | `esc_2026{eeprom_master_18e6c70dd2e87759}` |
| 3 | Airwave Template | 200 | `esc_2026{ss7i_udp_pivot_c49d3d60353281de}` |
| 4 | Hidden Portal | 250 | `esc_2026{50_shades_of_grey_6c6eb0fcfc1bde79}` |
| 5 | Minions Lockout | 350 | `esc_2026{minions_lockout_2ab7320b32363d9f}` |
| 6 | Silicon Badge | 450 | `esc_2026{silicon_badge_ab8dfaca}` |
| 7 | Smart Gateway Escape | 400 | `esc_2026{Challenge_7_WiFi_MotionDetection_ebe2e2cc}` |
| | **Total** | **1950** | |

The full write-up is not kept in this repo; the PDF was submitted on HotCRP.

## Layout

```
week_1/1-serial/          bruteforce.py, log.py
week_1/2-eeprom/          decode_eeprom.py
week_2/3-udp/             probe.py
week_2/4-web/             gray_decode.py, admin.png  (the stego asset from /api/admin)
week_2/5-lockout/         brute.py, minions_wordlist.txt, fake_eeprom/ (Arduino sketch)
week_3/6-badge/           xor.py
week_3/7-gateway-escape/  aes_decrypt.py, analyze.py, log_055.enc, log_055.csv
```

## Requirements

- Python 3.11+ with [`pyserial`](https://pyserial.readthedocs.io/) and
  [`cryptography`](https://cryptography.io/)
- [`esptool`](https://docs.espressif.com/projects/esptool/) — flashing, `read-mac`
- `tcpdump`, `ufw` — Ch. 3
- [`exiftool`](https://exiftool.org/), [`zsteg`](https://github.com/zed-0xff/zsteg) — Ch. 4
- `bluetoothctl` (BlueZ) — Ch. 6, 7
- [`arduino-cli`](https://arduino.github.io/arduino-cli/) or the Arduino IDE, and a
  **second** ESP32 dev board — Ch. 5 only

```sh
pip install pyserial cryptography esptool
```

## Read this before running anything

Several values are specific to our board or regenerate on every reset. The
constants in the scripts are **ours** and will not work on your board:

| Script | Replace |
|---|---|
| `bruteforce.py`, `log.py`, `brute.py` | `PORT` / `TARGET_PORT` if your board is not `/dev/ttyUSB0` |
| `log.py` | `212090` — your MAC suffix, from `esptool read-mac` |
| `decode_eeprom.py` | `MAC` and the pasted `DUMP` block |
| `xor.py` | `ks_ct` (block 8) and `vault` (`my_keys`) hex |
| `aes_decrypt.py` | `key_hex` — read over BLE |
| `probe.py` | `GW` if the AP is not on `192.168.4.1` |

The Ch. 4 PIN/token, the Ch. 6 keystream and BLE key, and the Ch. 3 UDP port all
change on reboot, so each of those chains has to be completed inside a single
power cycle.

## Flashing a challenge image

Each challenge ships as its own merged binary. Flash at offset `0x0`, then press
EN with a serial console open at 115200 8N1:

```sh
esptool --chip esp32 --port /dev/ttyUSB0 --baud 460800 \
        write-flash 0x0 <challenge>_merged.bin
arduino-cli monitor -p /dev/ttyUSB0 -c baudrate=115200
```

## Reproducing each challenge

### 1 — Serial Gateway

The CLI confirms valid command *prefixes*, which turns command discovery into a
linear search instead of an exponential one.

```sh
python3 week_1/1-serial/bruteforce.py   # DFS over the prefix oracle
esptool --port /dev/ttyUSB0 read-mac    # password = last 3 bytes, e.g. 212090
python3 week_1/1-serial/log.py          # dumps log1..log100
```

`bruteforce.py` hardware-resets the board over RTS every 8 attempts to clear the
CLI's escalating penalty delay. Log 37 names the command `claim_flag_uart_s1`,
which only works once in developer mode.

### 2 — EEPROM Secrets

Paste the output of `get_mac` and `dump_eeprom` into the script, then run it. It
XORs the dump with the 6-byte MAC repeating, which recovers ten gateway records.

```sh
python3 week_1/2-eeprom/decode_eeprom.py
```

Take `Master_GW`'s suffix and status byte, write them into card block 5, and tap
the card:

```
write_block 5 B2203499
```

### 3 — Airwave Template

The UDP server hops over ports 4210–4219 and replies from a *random* source
port, so the host firewall drops the answers until you allow them:

```sh
sudo ufw allow from 192.168.4.1 to any port 4210:4219 proto udp
python3 week_2/3-udp/probe.py
```

Input is `PORT message`. The server renders input as a template:

```
> 4216 {{7*7}}             -> 49
> 4216 {{__globals__}}     -> device_id,uptime,clients,secret_cmd
> 4216 {{secret_cmd}}      -> diag_dump <token>
```

Send that `diag_dump` command on UART in the **same** boot session.

### 4 — Hidden Portal

The portal's page source leaks an unlinked `/api/admin` endpoint serving a
64×48 PNG (`admin.png`). The PIN is in the LSB of its red channel:

```sh
zsteg week_2/4-web/admin.png        # -> "PIN:8628"
```

Unlock `/vault` with that PIN, then Gray-decode the blob it shows:

```sh
python3 week_2/4-web/gray_decode.py <hex>
```

That prints another `diag_dump <token>` to send on UART.

### 5 — Minions Lockout

Needs the helper ESP32 running first — see the next section.

```sh
cd week_2/5-lockout && python3 brute.py
```

Stage 1 sweeps all 158 first names and watches `proc_ms`: wrong names are
rejected in ~11 ms, the correct one takes ~41 ms because the check only reaches
the second half once the first matches. Stage 2 brute-forces the second name.

### 6 — Silicon Badge

Run `clear_card` then `enroll_master`, so block 8 holds a known plaintext
(`LEVEL999` zero-padded to 16 bytes). Put that block's ciphertext and the
`my_keys` blob into the script:

```sh
python3 week_3/6-badge/xor.py
```

XOR recovers the keystream, and the same keystream decrypts `my_keys` — giving a
`ble key`. Pair with it:

```sh
bluetoothctl
> scan on                               # Silicon_Badge_6
> pair FC:B4:67:21:20:92                # passkey = the ble key
> menu gatt
> select-attribute 4bf0ff03-2a01-4c1d-9e6b-123456789abc
> read
```

The characteristic returns a quote. Type its author (`richard clarke`) on UART
while still bonded.

### 7 — Smart Gateway Escape

Three BLE characteristics on `Gateway_Escape_7`, none needing pairing: a note, a
JSON blob with `log_id` and `aes_key_hex`, and a writable clock.

```sh
python3 week_3/7-gateway-escape/aes_decrypt.py        # log_055.enc -> log_055.csv
python3 week_3/7-gateway-escape/analyze.py log_055.csv
```

`analyze.py` ranks every quiet stretch by subcarrier variance. Decoy periods sit
near 0.34; the real window is ~100× quieter at 0.0036. Write that epoch to the
clock characteristic as **ASCII digits**, then send `escape` on UART with the
BLE link still up:

```
select-attribute cba1d466-344c-4be3-ab3f-189f80dd7518
write "0x31 0x37 0x36 0x37 0x32 0x37 0x31 0x36 0x38 0x30"
```

A mistimed `escape` costs a 20 s lockout, so get the window right first.

## Ch. 5: building and flashing the fake EEPROM

`fake_eeprom.ino` turns a **second** ESP32 into a stand-in for the AT24C256. It
acknowledges at address `0x50` and returns zero for every byte read. Without it
the gateway sees a silent I²C bus, its diagnostics watchdog declares
`BUS FAULT LOCKDOWN`, and every `unlock_key` is refused — so it has to be wired
up and running before `brute.py` will get anywhere. It also pins the fail
counter at zero, so the one-strike lockout can never arm.

### 1. Wire the helper to the gateway

Direct jumper wires; the gateway board already has the I²C pull-ups, so no
resistors are needed.

| Helper ESP32 | Gateway |
|---|---|
| `GND` | `GND` (required — without a common ground nothing works) |
| `GPIO21` (SDA) | `SDA` (24Cxx pin 5) |
| `GPIO22` (SCL) | `SCL` (24Cxx pin 6) |

> GPIO21/22 are the default `Wire` pins on a **classic** ESP32 dev board. On an
> S2/S3/C3 helper, change the pins in the `Wire.begin()` call in the sketch.

### 2. One-time toolchain setup

```sh
arduino-cli config init
arduino-cli config add board_manager.additional_urls \
    https://espressif.github.io/arduino-esp32/package_esp32_index.json
arduino-cli core update-index
arduino-cli core install esp32:esp32
```

### 3. Compile and upload

Both boards enumerate as `/dev/ttyUSB*`. Plug the helper in **last** and check
`arduino-cli board list` so you don't flash the gateway by mistake.

```sh
arduino-cli compile --fqbn esp32:esp32:esp32 week_2/5-lockout/fake_eeprom
arduino-cli upload  --fqbn esp32:esp32:esp32 -p /dev/ttyUSB1 week_2/5-lockout/fake_eeprom
```

Verified with `arduino-cli` 1.5.1 and esp32 core 3.3.12 — builds clean, ~22% of
program storage.

In the Arduino IDE instead: open `week_2/5-lockout/fake_eeprom/fake_eeprom.ino`,
select **Tools → Board → ESP32 Dev Module**, pick the helper's port, upload. (The
sketch sits in a folder matching its own name because both the IDE and
`arduino-cli` require that.)

### 4. Check it is alive

```sh
arduino-cli monitor -p /dev/ttyUSB1 -c baudrate=115200
```

You should see `FAKE_EEPROM READY @0x50`, then a once-a-second
`i2c rx=<n> req=<n>` line with both counters climbing — that is the gateway
polling the emulator. If they stay at zero, the wiring is wrong or the gateway
is not powered.

On the gateway's own console, `status` should now report `"reason":"ready"`
instead of `"bus_fault_lockdown"`. `brute.py` exits early with a `BUS FAULT`
message if the emulator stops answering mid-run.
