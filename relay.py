from RPi import GPIO

# GPIO pin for answering machine relay
ANS_MACH_RELAY = 36

# Initialize all GPIO related to relays
def init_relay_gpio():
    # Use Board pin numbers
    GPIO.setmode(GPIO.BOARD)
    init_ans_machine_relay_pin()

# Initialize answering machine relay pin
def init_ans_machine_relay_pin():
    GPIO.setup(ANS_MACH_RELAY, GPIO.OUT)
    # Set to low as starting value
    GPIO.output(ANS_MACH_RELAY, GPIO.LOW)

# Set answering machine relay pin
# Accepts boolean: sets relay pin to high if TRUE, sets relay pin to low if FALSE
def set_ans_machine_relay_pin(set_high):
    state = GPIO.HIGH if set_high else GPIO.LOW
    GPIO.output(ANS_MACH_RELAY, state)

