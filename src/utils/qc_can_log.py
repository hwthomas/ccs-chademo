#!/usr/bin/python3
#
# This is simple CAN receive-then-print and log python program loop. 
# All messages received are printed out on screen, and to a log file.
# The log file name is read as command-line argument[1] 
# ie run command:- 'python qc_can_log.py leaf.log'
# For use with Waveshare RS485/CAN boards on the Raspberry Pi
#
# Make sure Python-CAN is installed first - pip3 install python-can
# then 'import can'  as listed below

# This program is not complete - currently prints only to stdout

import can
import time
import os
import sys

print('\n\rCAN Rx...Tx test')
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

# open log file to be written to, as first argument to command line
can_file = sys.argv[1]      # get log filename from command-line
print("Opening log file ", can_file, " for writing")
with open(can_file, 'rw') as file:
    try:
        while True:
            message = bus.recv()    # Blocking wait until a message is received.

                # format timestamp, ID, and dlc first
                c = '{0:f} {1:03X} {2:02X} '.format(message.timestamp, message.arbitration_id, message.dlc)
                # then format the data bytes with single space separator
                s=''
                for i in range(message.dlc ):
                    s +=  '{0:02X} '.format(message.data[i])

                print(' {}'.format(c+s))    # space separator between field of each line in log

                # pause 10mS, then loop for next message or until Ctrl-C
                time.sleep(0.01) 

    except KeyboardInterrupt:
        # Catch keyboard interrupt
        print('\n\rKeyboard interrupt') 

print('\n\rShutting bus and CAN0 down') 
bus.shutdown()
os.system("sudo /sbin/ip link set can0 down")
