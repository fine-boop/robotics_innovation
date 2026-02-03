import RPi.GPIO as GPIO
import time

# Stepper motor pins
DIR = 18
PUL = 17
ENA = 5

# Motor configuration
STEPS_PER_REV = 200          # full steps per revolution of your motor
MICROSTEP = 1                # e.g., 1 for full step, 16 for 1/16 microstepping
STEPS_PER_20_DEGREES = int((20 / 360) * STEPS_PER_REV * MICROSTEP)
PULSE_DELAY = 0.02           # seconds between pulses, adjust for speed

# GPIO setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(DIR, GPIO.OUT)
GPIO.setup(PUL, GPIO.OUT)
GPIO.setup(ENA, GPIO.OUT)
GPIO.output(ENA, GPIO.HIGH)

def rotate_20_degrees(direction=True):
    """
    Rotate the stepper motor approximately 20 degrees.
    direction=True for one way, False for reverse.
    """
    GPIO.output(DIR, GPIO.HIGH if direction else GPIO.LOW)
    for _ in range(STEPS_PER_20_DEGREES):
        GPIO.output(PUL, GPIO.HIGH)
        time.sleep(PULSE_DELAY)
        GPIO.output(PUL, GPIO.LOW)
        time.sleep(PULSE_DELAY)
