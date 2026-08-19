#
# This program reads a CAN log from a file written in csv format
# and generates CAN messages to be sent via the Waveshare CAN HAT on the RPi.
#
# simple log file 'short.log' extracted from 'ZE1-chademo-charging.log'
# in 'https://github.com/dalathegreat/EV-CANlogs' repo. Layout as per-

# -1688467643234759,00000100,false,Rx,0,8,06,00,00,00,B3,01,FF,00,
# -1688467643224751,00000101,false,Rx,0,8,00,E4,00,00,00,00,00,00,
# -1688467643214763,00000102,false,Rx,0,8,02,9A,01,73,00,81,8F,00,

import can      # for message structure, construction and transmission
import time     # for sleep and timings
import sys
import os

if __name__ == "__main__":
    print("Testing log_to_can using a can.log file for input...")
    
    # use a can.Message object for decoding and subsequent sending
    # see https://python-can.readthedocs.io/en/stable/message.html

    print('Bringing up CAN0 at 500kbps...')
    os.system("sudo /sbin/ip link set can0 down")   # prevent 'Busy' error if can0 already UP
    os.system("sudo /sbin/ip link set can0 up type can bitrate 500000")
    try:
        bus = can.Bus(channel='can0', interface='socketcan', can_filters=None)  # allow *all* IDs
    except OSError:
        print('Cannot find CAN board.')
        exit()

    # open and read in each line of the CAN log
    # Note: 'line' is a string of the *whole* line, including the separators
    # eg   "-1688467643250712,00000109,false,Rx,0,8,01,7B,01,64,01,05,D7,24,"

    # can_file = "short.log"                  # select short file to read from, or...
    can_file = "ZE1-chademo-charging.log"     # full file from Dala/EV-CANlogs repo

    print("Opening log file ", can_file)
    with open(can_file) as file:
        startTime_ms = round(time.time()*1000)
        for line in file:                   # iterate through each line in the file
            time.sleep(0.1)                 # wait 100mS before next message
            currentTime_ms = round(time.time()*1000)
            ts = currentTime_ms - startTime_ms   # timestamp for CAN message

            items = line.split(',')         # <list> of comma separated <str>
            id = int(bytes(items[1], 'utf-8'), 16)      # extract arbitration id as an <int>
            dlc = int(bytes(items[5], 'utf-8'), 16)     # ditto for data length code (dlc)
            data = bytearray(8)             # build data as <bytearray> of size 8
            for i in range(6,13):
                data[i-6] = int(items[i], 16)   # convert items to hex integers

            msg = can.Message(timestamp=ts, arbitration_id=id, dlc=dlc, data=data, is_extended_id = False)
            print(msg)

            try:
                bus.send(msg)
            except can.CanError:
                print("Message NOT sent")
            except KeyboardInterrupt:
                bus.shutdown()

        print("All lines in log sent")
        bus.shutdown()
