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
    canbus = can.Bus(channel='can0', interface='socketcan', can_filters=filters, receive_own_messages = True)
except OSError:
    print('Cannot find CAN board.')
    exit()

print('Ready')

# define some fixed parameters for the 2 'charger' messages following, which are sent after receiving 0x100/0x102 from the EV
evseCHAdeMO_version = 2
maxBatteryVoltage = 0
maxChargerVoltage = 0
thresholdVoltage = 0
maxChargerCurrent = 0
chargerVoltage) = 0
chargerCurrent = 0
weldDetect = 0

# send CAN message 0x108 to the EV with the Charger parameters (maxChargerVoltage, maxChargerCurrent).
# this message must be send after CAN message 0x100 has been received from the EV with its parameter
# maxBatteryVoltage.  Parameters maxChargerVoltage/maxChargerCurrent are fixed properties of the charger       
def canSend0x108(self):
    # construct CAN message 0x108 and send it (even if maxVolts or maxCurrent haven't changed)
    thresholdVoltage = int(min(maxBatteryVoltage, maxChargerVoltage))     # minimum of what EV 'needs' and what charger can supply
    mv_lo = int(maxChargerVoltage) & 0xFF
    mv_hi = int(maxChargerVoltage) >> 8
    th_lo = int(thresholdVoltage) & 0xFF
    th_hi = int(thresholdVoltage) >> 8
    try:
        msg = can.Message(arbitration_id=0x108, data=[weldDetect, mv_lo, mv_hi, maxChargerCurrent, th_lo, th_hi, 0, 0], is_extended_id=False)
        canbus.send(msg)
    except can.CanError:
        print("CAN error: - Message NOT sent")
        canbus.shutdown()
        exit()

# send CAN message 0x109 to the EV with charging loop *actual* values (chargerVoltage, chargeCurrent)
# this message must be send after CAN message 0x102 from the EV with *its* voltage and current requests          
def canSend0x109(self):
    # construct CAN message 0x109 and send it (even if volts or current haven't changed)
    status = 4    # always report connector locked (adapter has no lock at present)
    cv_lo = int(chargerVoltage) & 0xFF
    cv_hi = int(chargerVoltage) >> 8
    try:
        msg = can.Message(arbitration_id=0x109, data=[evseCHAdeMO_version, cv_lo, cv_hi, chargerCurrent, 0, status, 0, 0], is_extended_id=False)
        canbus.send(msg)
    except can.CanError:
        print("CAN error: - shutting down")
        canbus.shutdown()
        exit()



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
