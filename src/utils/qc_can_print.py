#!/usr/bin/python3
#
# This is special CAN receive-then-print python program loop for testing the QC-CAN bus on the Leaf Tekna+. 
# All messages received are formatted and printed out on screen, and replies 0x108 & 0x109 generated.
# GPIO signals are monitored and output where required for the tests. 
# For use with Waveshare RS485/CAN boards on the Raspberry Pi, and the RPi.GPIO digital i/o package used.
#
# Make sure Python-CAN is installed first - pip3 install python-can, then 'import can'  as listed below
# 
import can
import RPi.GPIO as GPIO
import time
import os

print('\n\rNissan Leaf Tekna+ Quick-Charge (QC-CAN) Rx...Print loop program')

# set up GPIO outputs and input
GPIO.setmode(GPIO.BOARD)                # set GPIO for board (physical pin) numbering
#   RPI4b GPIO output definitions for interface board (https://github.com/hwthomas/ccs-chademo/wiki/)
pinSS1 = 13     # d1/SS1 Charge sequence signal 1
pinSS2 = 29     # d2/SS2 Charge sequence signal 2
# GPIO input definitions
pin_k = 10      # used for evChargePermit (signal k)
outputs = [pinSS1, pinSS2]
for pin in outputs:                         # process all the outputs defined above
    GPIO.setup(pin, GPIO.OUT)               # set up each of the GPIO pins as outputs
    GPIO.output(pin, GPIO.LOW)              # also set each output LOW at start
    
inputs = [pin_k]
for pin in inputs:
    GPIO.setup(pin, GPIO.IN)

print('Bring up CAN0....')
os.system("sudo /sbin/ip link set can0 down")    # Prevent 'Busy' error if already UP
os.system("sudo /sbin/ip link set can0 up type can bitrate 500000")

# restrict messages monitored to QC-CAN (CHAdeMO) ones
filters = [
    {"can_id": 0x100, "can_mask": 0x7FF, "extended": False},
    {"can_id": 0x101, "can_mask": 0x7FF, "extended": False},
    {"can_id": 0x102, "can_mask": 0x7FF, "extended": False},
    {"can_id": 0x108, "can_mask": 0x7FF, "extended": False},
    {"can_id": 0x109, "can_mask": 0x7FF, "extended": False} ]
try:
    bus = can.Bus(channel='can0', interface='socketcan', can_filters=filters, receive_own_messages = True)
except OSError:
    print('Cannot find CAN board.')
    exit()

print('Ready')

try:
    startTime_ms = round(time.time()*1000)          # startTime for message loop
    while True:
        message = bus.recv()    # Blocking wait until a message is received.

        currentTime_ms = round(time.time()*1000)    # update current time
        local_ts = currentTime_ms - startTime_ms    # local timestamp for CAN message
        
        # format timestamp, ID, and dlc first
        c = "{0:f} {1:03X} {2:02X} ".format(local_ts, message.arbitration_id, message.dlc)
        # then append the data bytes with single space separator
        for i in range(message.dlc):
            c +=  "{0:02X} ".format(message.data[i])

        print(" {}".format(c))    # space separator between fields of each line in log
    
        # pause 10mS, then loop for next message or until Ctrl-C
        time.sleep(0.01) 

except KeyboardInterrupt:
    # Catch keyboard interrupt
    print('\n\rKeyboard interrupt') 

print('\n\rShutting bus and CAN0 down') 
bus.shutdown()
os.system("sudo /sbin/ip link set can0 down")
