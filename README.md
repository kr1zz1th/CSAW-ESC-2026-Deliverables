# CSAW ESC 2026 – Final Phase Deliverables

All challenges were solved **black-box** through the gateway's UART, Wi-Fi, BLE,
RFID and EEPROM interfaces. No flag was obtained by reverse engineering the
provided binaries. The full write-up is `report/final_report.tex` (PDF submitted
on HotCRP).

Board-specific values (MAC, keystream, PIN, tokens, BLE keys) are read from the
device at run time, and several of them regenerate on every reset. The constants
inside the scripts are the values from **our** board and must be replaced with
yours.

## Layout

```
report/final_report.tex   write-up (IEEEtran; needs -shell-escape for minted)
report/figures/           the figures it includes, named ch<N>-<what>
report/_unused/           superseded screenshots and earlier drafts (safe to delete)
week_1/ week_2/ week_3/   solve scripts, one folder per challenge
```

## Requirements

- Python 3.11+ with [`pyserial`](https://pyserial.readthedocs.io/) and
  [`cryptography`](https://cryptography.io/)
- [`esptool`](https://docs.espressif.com/projects/esptool/) — flashing, `read-mac`
- `tcpdump`, `ufw` — Ch. 3
- [`exiftool`](https://exiftool.org/), [`zsteg`](https://github.com/zed-0xff/zsteg) — Ch. 4
- `bluetoothctl` (BlueZ) — Ch. 6, 7
- [`arduino-cli`](https://arduino.github.io/arduino-cli/) or the Arduino IDE, plus a
  second ESP32 dev board — Ch. 5 only

```sh
pip install pyserial cryptography esptool
```

## Flashing a challenge image

Each challenge ships as its own merged binary. Flash at offset `0x0`, then press
EN with a serial console open at 115200 8N1:

```sh
esptool --chip esp32 --port /dev/ttyUSB0 --baud 460800 \
        write-flash 0x0 <challenge>_merged.bin
arduino-cli monitor -p /dev/ttyUSB0 -c baudrate=115200
```

## Solve scripts

| Challenge | Script | Usage |
|---|---|---|
| 1 Serial Gateway | `week_1/1-serial/bruteforce.py` | `python3 bruteforce.py` – DFS prefix-oracle command discovery, RTS auto-reset every 8 queries |
| 1 Serial Gateway | `week_1/1-serial/log.py` | `python3 log.py` – enters `mode developer --help` with the MAC suffix and dumps `log1`..`log100` |
| 2 EEPROM Secrets | `week_1/2-eeprom/decode_eeprom.py` | paste `get_mac` + `dump_eeprom` output into the script, run; then `write_block 5 <master_suffix>99` and tap the card |
| 3 Airwave Template | `week_2/3-udp/probe.py` | `sudo ufw allow from 192.168.4.1 to any port 4210:4219 proto udp`; then type `PORT {{secret_cmd}}` and send the reply on UART |
| 4 Hidden Portal | `week_2/4-web/gray_decode.py` | `zsteg admin.png` → PIN; unlock `/vault`; `python3 gray_decode.py <hex>`; send the result on UART |
| 5 Minions Lockout | `week_2/5-lockout/fake_eeprom/` | Arduino sketch for a helper ESP32 — see below. Must be running before `brute.py`. |
| 5 Minions Lockout | `week_2/5-lockout/brute.py` | `python3 brute.py` (run from this folder; needs `minions_wordlist.txt`) – timing sweep on `proc_ms` for the first name, then brute-forces the second |
| 6 Silicon Badge | `week_3/6-badge/xor.py` | put your `read_block 8` / `my_keys` hex in, run; pair BLE with the `ble key`; answer the riddle on UART |
| 7 Gateway Escape | `week_3/7-gateway-escape/aes_decrypt.py` | decrypts `log_055.enc` (AES-256-CBC, IV prefix) with the key read over BLE |
| 7 Gateway Escape | `week_3/7-gateway-escape/analyze.py` | `python3 analyze.py log_055.csv` → epoch of the unguarded window; write it to the clock characteristic; `escape` |

## Ch. 5: building and flashing the fake EEPROM

`fake_eeprom.ino` turns a **second** ESP32 into a stand-in for the AT24C256. It
acknowledges at address `0x50` and returns zero for every byte read. Without it
the gateway sees a silent I²C bus, its diagnostics watchdog declares
`BUS FAULT LOCKDOWN`, and every `unlock_key` is refused — so this has to be
running and wired up before `brute.py` will get anywhere.

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

Verified against `arduino-cli` 1.5.1 with esp32 core 3.3.12 — the sketch builds
clean and uses about 22% of program storage.

In the Arduino IDE instead: open `week_2/5-lockout/fake_eeprom/fake_eeprom.ino`,
select **Tools → Board → ESP32 Dev Module**, pick the helper's port, and upload.
(The sketch lives in a folder matching its own name because both the IDE and
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
rather than `"bus_fault_lockdown"`. Then:

```sh
cd week_2/5-lockout && python3 brute.py
```

`brute.py` exits early with a `BUS FAULT` message if the emulator stops
answering mid-run.
