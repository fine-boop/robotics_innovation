#!/usr/bin/env python3
import sys
import time

# --- Configurable parameters via argv ---
DT_PIN = int(sys.argv[1]) if len(sys.argv) > 1 else 5
SCK_PIN = int(sys.argv[2]) if len(sys.argv) > 2 else 6
REFERENCE_UNIT = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
SAMPLES = int(sys.argv[4]) if len(sys.argv) > 4 else 10

def console_log(msg, level="info"):
    return f"[{level.upper()}] {msg}"

def get_average_weight(samples=SAMPLES, dt_pin=DT_PIN, sck_pin=SCK_PIN, reference_unit=REFERENCE_UNIT):
    # --- Import HX711 and GPIO ---
    try:
        from hx711 import HX711
        import RPi.GPIO as GPIO
    except ImportError as e:
        print(console_log(f'HX711 or RPi.GPIO import failed: {e}', 'error'), file=sys.stderr)
        print("None")
        return

    # --- Fix HX711 read_median bug ---
    def fixed_read_median(self, times=3):
        values = []
        for _ in range(times):
            try:
                values.append(self.read_long())
            except Exception:
                continue
        if not values:
            raise ValueError("No valid HX711 readings")
        values.sort()
        mid = len(values) // 2
        if len(values) % 2 == 1:
            return values[mid]
        else:
            return (values[mid - 1] + values[mid]) / 2

    HX711.read_median = fixed_read_median

    # --- Setup GPIO ---
    try:
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
    except Exception as e:
        print(console_log(f'GPIO setup warning: {e}', 'warn'), file=sys.stderr)

    hx = None
    try:
        hx = HX711(dt_pin, sck_pin)
        hx.set_reading_format('MSB', 'MSB')
        hx.reset()
        
        # Set reference unit safely
        try:
            hx.set_reference_unit(reference_unit)
        except Exception as e:
            print(console_log(f'Failed to set reference unit: {e}', 'warn'), file=sys.stderr)

        # --- Take multiple readings ---
        readings = []
        for _ in range(samples):
            try:
                val = hx.get_weight(1)
                if val is not None:
                    readings.append(val)
            except Exception as e:
                print(console_log(f'HX711 read error: {e}', 'warn'), file=sys.stderr)
            
            # Power cycle HX711 to stabilize readings
            try:
                hx.power_down()
                time.sleep(0.05)
                hx.power_up()
            except Exception:
                pass

            time.sleep(0.05)

        if not readings:
            print("None")
            return

        avg = sum(readings) / len(readings)
        print(round(avg, 2))

    finally:
        # Clean up HX711
        try:
            if hx:
                hx.power_down()
        except Exception:
            pass
        try:
            GPIO.cleanup()
        except Exception:
            pass

if __name__ == "__main__":
    get_average_weight(SAMPLES, DT_PIN, SCK_PIN, REFERENCE_UNIT)
