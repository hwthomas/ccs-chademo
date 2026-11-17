#
# This program reads a CAN log from a file written in can-print format &
# generates CAN messages to be sent via the Waveshare CAN HAT on the RPi.
#
# It is a special version of log_to_can.py which reads can_print/qc-print logs only
#
# the log file to be decoded is read as command-line argument[1] 
# ie run command:- 'python qc-log-to-can.py leaf.log'
#
# below is a short extract from a can_print.py generated log...
#
#  Timestamp mS    ID  dlc  data[0..7] as hex bytes
#     [0]          [1][2][3][4][5][6][7][8][9][10]
#    3152.0        100 08 06 00 00 00 B3 01 FF 00
#    3174.0        101 08 00 E4 00 00 00 00 00 00
#    3184.0        102 08 02 9A 01 6D 00 81 8F 00 
#

import can      # for message structure, construction and transmission
import time     # for sleep and timings
import sys      # for starting CAN-bus via 'ip link' commands
import os

if __name__ == "__main__":
    print("Testing qc-to-can.py using a can-print.log file for input...")
    
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
    # Note: 'line' is a string of the *whole* line, including the ' ' separators
    # if a line starts with '#' it is a comment and is skipped

    can_file = sys.argv[1]                  # select log file to read from

    print("Opening log file ", can_file)
    with open(can_file) as file:
        startTime_ms = round(time.time()*1000)
        for line in file:                   # iterate through each line in the file
            is_comment = (line[0] == '#')   # check first character of first item in line
            if is_comment:
                comment = line.rstrip('\n') # remove last '\n'
                continue                    # and ignore for CAN message purposes

            items = line.split(' ')         # <list> of ' ' separated <str>
            currentTime_ms = round(time.time()*1000)
            ts = currentTime_ms - startTime_ms          # delta timestamp for CAN message
            id = int(bytes(items[1], 'utf-8'), 16)      # extract arbitration id as an <int>
            dlc = int(bytes(items[2], 'utf-8'), 16)     # ditto for data length code (dlc)
            data = bytearray(8)                         # build data as <bytearray> of size 8
            for i in range(3,10):                       # log file has data[8] in bytes 0..7
                data[i-3] = int(items[i], 16)           # convert items to hex integers

            msg = can.Message(timestamp=ts, arbitration_id=id, dlc=dlc, data=data, is_extended_id = False)
            try:
                bus.send(msg)
                time.sleep(0.05)                # wait 50mS before next message
            except can.CanError:
                print("CAN error: - Message NOT sent")  # exit 'for' loop
                bus.shutdown()
                break
            except KeyboardInterrupt:
                print("Ctrl-C typed to exit program")   # exit 'for' loop
                bus.shutdown()
                break
        pass    # end of for loop
    pass     # can_file gets closed at end of with...
    print("Normal program end - log file closed")
    bus.shutdown()
    os.system("sudo /sbin/ip link set can0 down")
pass    # end of main



