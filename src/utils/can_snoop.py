#!/usr/bin/python3
#
# This is simple CAN receive-then-print python program loop. 
# All messages received are printed out on screen.
# It is a special version of 'can_print.py' which assumes that the 'can0' driver
# is already up and running and CAN comms are in progress between 2 users.
# because of this, the can driver is neither set up nor shut down here.
#
# Make sure Python-CAN is installed first - pip3 install python-can
# then 'import can'  as listed below

import can
import time
import os

print("\n\Snooping Monitor on existing CAN comms. This is a simple Receive...Print loop")
print("Don't bring up CAN0, it should be in use already....")
# os.system("sudo /sbin/ip link set can0 down")    # Prevent "Busy" error if already UP
# os.system("sudo /sbin/ip link set can0 up type can bitrate 500000")

# try and connect to running kernel driver can0, with filters for just the CHAdeMO CAN-IDs
filters = [
    {"can_id": 0x100, "can_mask": 0x7FF, "extended": False},
    {"can_id": 0x101, "can_mask": 0x7FF, "extended": False},
    {"can_id": 0x102, "can_mask": 0x7FF, "extended": False},
    {"can_id": 0x108, "can_mask": 0x7FF, "extended": False},
    {"can_id": 0x109, "can_mask": 0x7FF, "extended": False} ]
try:
    canbus = can.Bus(interface='socketcan', channel="can0", can_filters = filters)

try:
    bus = can.Bus(channel='can0', interface='socketcan', can_filters=None)    # allow *all* CAN-IDs
except OSError:
    print('Cannot find CAN board.')
    exit()

print("Ready")

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
    print("\n\rKeyboard interrupt") 

# bus.shutdown()
# os.system("sudo /sbin/ip link set can0 down")
print("\n\rExiting without shutting CAN bus down - let other (running) user do this") 


