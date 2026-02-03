#!/usr/bin/env python3
import RPi.GPIO as GPIO
from hx711 import HX711
import time

# --- CONFIGURATION ---
DT_PIN = 5   # Data pin
SCK_PIN = 6  # Clock pin

# --- SETUP ---
GPIO.setmode(GPIO.BCM)
hx = HX711(DT_PIN, SCK_PIN)
hx.set_reading_format("MSB", "MSB")

def get_raw_value(samples=10):
    """Read multiple samples safely"""
    values = []
    for _ in range(samples):
        try:
            val = hx.get_value()
            values.append(val)
        except Exception as e:
            print(f"Error reading HX711: {e}")
        time.sleep(0.1)  # small delay
    if not values:
        raise RuntimeError("No valid readings from HX711")
    values.sort()
    median = values[len(values)//2]
    return median

def calibrate():
    try:
        # Step 1: Tare the scale
        input("Remove all weight from the scale and press Enter...")
        hx.reset()
        hx.tare()
        print("Scale tared. Zeroed weight.")

        # Step 2: Place known weight
        known_weight = float(input("Place a known weight on the scale (grams) and enter its value: "))
        input("Press Enter when ready to measure...")

        # Step 3: Read raw weight
        raw_value = get_raw_value(10)
        print(f"Raw reading from scale: {raw_value:.2f}")

        # Step 4: Compute REFERENCE_UNIT
        reference_unit = raw_value / known_weight
        print(f"Calculated REFERENCE_UNIT: {reference_unit:.4f}")
        print("\nUse this REFERENCE_UNIT in your scripts:")
        print(f"hx.set_reference_unit({reference_unit:.4f})")

    except KeyboardInterrupt:
        print("Calibration cancelled.")
    finally:
        hx.power_down()
        hx.power_up()
        GPIO.cleanup()

if __name__ == "__main__":
    calibrate()
