#!/usr/bin/env python3
import time
import sys
import RPi.GPIO as GPIO

from hx711 import HX711

# -------------------
# CONFIG
# -------------------
DT_PIN = 5
SCK_PIN = 6
SAMPLE_DELAY = 1.0  # seconds between readings

# -------------------
# FIX BROKEN hx711 LIB (Python 3.11 issue)
# -------------------
def fixed_read_median(self, times=3):
    values = []
    for _ in range(times):
        values.append(self.read_long())
    values.sort()
    mid = len(values) // 2
    if len(values) % 2 == 1:
        return values[mid]
    else:
        return (values[mid - 1] + values[mid]) / 2

# Monkey-patch the broken function
HX711.read_median = fixed_read_median

# -------------------
# SETUP
# -------------------
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

hx = HX711(DT_PIN, SCK_PIN)
hx.set_reading_format("MSB", "MSB")

hx.reset()

print("Taring... remove all weight from the scale.")
time.sleep(2)
hx.tare()
print("Tare done!")

# -------------------
# CALIBRATION
# -------------------
print("\n=== CALIBRATION MODE ===")
print("Place a known weight on the scale.")
known_weight = float(input("Enter the weight you placed (e.g. 1000 for 1000g): "))

print("Reading raw values...")
time.sleep(2)

raw = hx.get_weight(15)  # average a few readings

if raw == 0:
    print("Error: got zero reading. Check wiring.")
    GPIO.cleanup()
    sys.exit(1)

reference_unit = raw / known_weight

print("\n=== CALIBRATION RESULT ===")
print(f"Raw reading: {raw}")
print(f"Known weight: {known_weight}")
print(f"\n>>> Your reference unit is: {reference_unit}")
print(">>> Copy this number into REFERENCE_UNIT in the script!\n")

# Apply calibration
hx.set_reference_unit(reference_unit)

# -------------------
# CLEAN EXIT
# -------------------
def clean_and_exit():
    print("\nCleaning up GPIO and exiting...")
    GPIO.cleanup()
    sys.exit(0)

# -------------------
# MAIN LOOP
# -------------------
print("Now showing live weight readings:\n")

try:
    while True:
        weight = hx.get_weight(10)
        print(f"Weight: {weight:.2f}")

        hx.power_down()
        time.sleep(0.1)
        hx.power_up()

        time.sleep(SAMPLE_DELAY)

except (KeyboardInterrupt, SystemExit):
    clean_and_exit()