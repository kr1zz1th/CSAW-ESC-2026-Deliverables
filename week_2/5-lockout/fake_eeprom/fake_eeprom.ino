// Fake I2C EEPROM for CSAW ESC 2026 "Minions Lockout".
//
// Your board has no working EEPROM, so every I2C access NAKs and the target's
// diagnostics watchdog drops into BUS FAULT LOCKDOWN. This sketch makes the
// helper ESP32 impersonate the EEPROM: it ACKs on address 0x50 and returns 0
// for every byte read. Result: watchdog is happy (no faults) and the fail
// counter always reads 0 (never locked out) -> brute force freely over UART.
//
// Wiring (helper ESP32 <-> target), REPLACES the old single-SCL hookup:
//   helper GND  <-----------> target GND         (required)
//   helper GPIO21 (SDA) <---> target SDA         (24Cxx pin 5)
//   helper GPIO22 (SCL) <---> target SCL         (24Cxx pin 6)
// Direct wires; the target board already has the I2C pull-ups. No resistor.
//
// NOTE: GPIO21/22 are the default Wire pins on a classic ESP32 dev board.
// If your helper is an S2/S3/C3 etc., tell me and I'll change the pins.

#include <Wire.h>

#define EE_ADDR 0x50

volatile uint32_t rxCount = 0;
volatile uint32_t reqCount = 0;

// Master wrote bytes to us (e.g. the 2-byte memory address pointer). We don't
// care about the pointer since we always return 0 -- just drain the bytes.
void onReceive(int n) {
  rxCount++;
  while (Wire.available()) Wire.read();
}

// Master is reading from us: hand back zeros (counter = 0 = "ready").
void onRequest() {
  reqCount++;
  uint8_t zeros[16] = {0};
  Wire.write(zeros, sizeof(zeros));
}

void setup() {
  Serial.begin(115200);
  // Slave mode: Wire.begin(address, sda, scl, freq)
  Wire.begin((uint8_t)EE_ADDR, 21, 22, 0);
  Wire.onReceive(onReceive);
  Wire.onRequest(onRequest);
  Serial.println("FAKE_EEPROM READY @0x50");
}

void loop() {
  static uint32_t t = 0;
  if (millis() - t > 1000) {
    t = millis();
    Serial.printf("i2c rx=%lu req=%lu\n", rxCount, reqCount);
  }
}
