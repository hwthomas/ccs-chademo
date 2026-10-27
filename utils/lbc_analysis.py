#
# Check analysis of group 1 bytearray
#
# Note: on 10/04/2026 the results from the valid reply pasted in from
# a run of lbc_poll.py (as below) gave the correct values of:-
#       hv_volts = 363.1 volts, hv_soc% = 62.55%
# 17/04/2026:-
#   hv_volts =  353.43
#   hv_soc% =  48.7743
#   deltaT: 0.024 mSecs
#
# testing with print statements included: 0.023mS (23 microSec)
# without print statements: 0.0083 mS (8.3 microSec)
#

import logging
import time

hv_volts = 0
hv_soc = 0

def analyse_group(group: bytearray):
    global hv_volts, hv_soc
    # validate group by several checks on known group structure
    if(group[51:53] != bytearray(b'23') or group[68:70] != bytearray(b'24') or group[85:87] != bytearray(b'25')):
        print("group 1 data is invalid")
    else:
        print("continuing with group analysis...")
        hv = group[53:57]       # extract 2-byte number
        hv_volts = int(hv, 16)/100
        print("hv_volts = ", hv_volts)
        soc = group[82:84] + group[87:91]  # extract a 3-byte number
        hv_soc = int(soc,16)/10000
        print("hv_soc% = ", hv_soc)

def main():
    # Paste bytearray data into 'reply' variable and save program
    # This run from 16/04/2026
    reply = bytearray(b'103561010000007C\r2102880000000000\r220000001B584650\r238A0F2F7E039A00\r2401700026780007\r25713F0018AA9180\r2600050000000000\r2700001A01AEFFFF\r\r>')

    if(reply[-1] == ord('>')):          # check for message terminator
        group = bytearray(reply)        # copy (possible) group message
        if( len(group) == 138):         # check for valid group length (138 normally)
            print(group)                # diagnostics only
            start_time = time.perf_counter()
            analyse_group(group)     # analyse group
            deltaT=(time.perf_counter() - start_time)*1000  # mS
            print(f'deltaT: {deltaT:0.6f} mSecs')

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
