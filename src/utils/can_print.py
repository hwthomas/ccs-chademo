#!/usr/bin/python3
#
# This is simple CAN receive-then-print python program loop. 
# All messages received are printed out on screen.
# For use with Waveshare RS485/CAN boards on the Raspberry Pi
#
# Make sure Python-CAN is installed first - pip3 install python-can
# then 'import can'  as listed below

import can
import time
import os

print('\n\rCAN Rx...Print loop')
print('Bring up CAN0....')
os.system("sudo /sbin/ip link set can0 down")    # Prevent 'Busy' error if already UP
os.system("sudo /sbin/ip link set can0 up type can bitrate 500000")
time.sleep(0.1) 

try:
    bus = can.Bus(channel='can0', interface='socketcan', can_filters=None)    # allow all CAN-IDs
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
        # then format the data bytes with single space separator
        s=''
        for i in range(message.dlc ):
            s +=  "{0:02X} ".format(message.data[i])

        print(" {}".format(c+s))    # space separator between fields of each line in log
    
        # pause 10mS, then loop for next message or until Ctrl-C
        time.sleep(0.01) 

except KeyboardInterrupt:
    # Catch keyboard interrupt
    print('\n\rKeyboard interrupt') 

print('\n\rShutting bus and CAN0 down') 
bus.shutdown()
os.system("sudo /sbin/ip link set can0 down")
