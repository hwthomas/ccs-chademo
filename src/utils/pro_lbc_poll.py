#  File pro_lbc_poll.py  Sends commands to the ProScan dongle to
#  poll the Nissan Leaf LBC battery controller for Group 1 data
#
import time
import asyncio
import logging
from ble_serial.bluetooth.ble_client import BLE_client

ble = None                          # global variables
multi_msg = bytearray([])           # multi-section message buffer
rx_available = asyncio.Event()      # for rx buffer handshake

hv_volts = 0                        # define these for group analysis results
hv_soc = 0

def rx_handler(reply: bytes):
    global multi_msg, rx_available
    # a group multi-message reply may come in several sections, but will
    # be terminated by a prompt ('>') character.  Build the full group 
    # message from the partial sections before trying to analyse it.
    multi_msg += reply              # continue building full message
    if(reply[-1] == ord('>')):      # check for message terminator
        group = multi_msg           # copy complete group message
        multi_msg = bytearray([])   # and clear multi-message buffer
        if( len(group) == 138):     # check for valid group length
            analyse_group(group)    # and analyse if OK so far
    rx_available.set()              # mark rx buffer available (always)

async def send_cmd(ble: BLE_client, cmd):  # send command with handshake
    await asyncio.sleep(0.05)       # minimum time between commands
    #print("sending... ", cmd)  # debug code
    rx_available.clear()            # rx *not* available until cmd completed
    ble.queue_send(cmd)             # send cmd to ble device
    await rx_available.wait()       # and wait until it *is* ready

async def lbc_poll_loop(ble: BLE_client):
    ble.queue_send(b'ATZ\r')        # hard reset to ELM327 device
    await asyncio.sleep(2.0)        # wait for device to be ready
    for cmd in lbc_setup_commands:
        await asyncio.sleep(0.01)   # 10mS minimum between commands
        await send_cmd(ble, cmd)
    
    lbc_queries = 0         # Now query LBC Group 1 (2 off only)
    cmd = b"022101\r"
    while (lbc_queries < 2):
        await asyncio.sleep(3.0)
        lbc_queries += 1
        rx_available.clear()        # 
        await send_cmd(ble, cmd)
        await rx_available.wait()   #

    cmd = b"ATZ\r"          # finally send a reset to the ELM327 device
    await send_cmd(ble, cmd)
    await asyncio.sleep(2.0)
    pass                    # lbc_poll_loop task is now complete
    await ble.disconnect()  # shutdown ble-serial
       
lbc_setup_commands = [      # set up elm327 for LBC battery queries
    b"ate0\r",              # command-echo off
    b"atl0\r",              # line feed off
    b"ats0\r",              # spaces off
    b"ath0\r"               # headers off (no arbitration ID, dlc, etc - just data bytes)
    b"atv0\r",              # pad messages to 8 bytes with 0's
    b"atcaf0\r",            # turn off automatic formatting of CAN messages (set own PCI byte)
    b"atsh79b\r",           # set header for subsequent messages to 0x79b (LBC module)
    b"atfcsh79b\r",         # set flow control header for LBC module (straight after atsh79b)
    b"atfcsd300000\r",      # set flow control data - 30(continue to send):00:00(no message gap)
    b"atfcsm1\r",           # set flow control mode to 1
    b"atcra7bb\r",          # filter return messages with ID 0x7bb (LBC reply ID)
]

def analyse_group(group: bytearray):
    global hv_volts, hv_soc
    # validate group by several checks on known group structure
    if(group[51:53] != bytearray(b'23') or group[85:87] != bytearray(b'25') or group[85:87] != bytearray(b'25')):
        print("group 1 data is invalid")
    else:
        print("continuing with group analysis...")
        hv = group[53:57]       # extract 2-byte number
        hv_volts = int(hv, 16)/100
        soc = group[82:84] + group[87:91]  # extract a 3-byte number
        hv_soc = int(soc,16)/10000
        print("HV volts = ", hv_volts, "SOC% = ", hv_soc)

async def main():
    # PROSCAN = "66:1E:87:02:42:D1"
    # LELINK2 = "90:59:AF:26:A4:54"
    ADAPTER = "hci0"
    DEVICE = "66:1E:87:02:42:D1"    # PROSCAN dongle
    SERVICE_UUID = "0000fff0-0000-1000-8000-00805f9b34fb"
    WRITE_UUID = "0000fff2-0000-1000-8000-00805f9b34fb"     # ['write-without-response', 'write']
    READ_UUID  = "0000fff1-0000-1000-8000-00805f9b34fb"     # ['notify']
    WRITE_WITH_RESPONSE = True

    ble = BLE_client(ADAPTER, 'ID')
    ble.set_receiver(rx_handler)

    try:
        await ble.connect(DEVICE, "public", SERVICE_UUID, 30.0)
        print("ProScan device connected...")
        await ble.setup_chars(WRITE_UUID, READ_UUID, 'rw', WRITE_WITH_RESPONSE)
        print("Service Characteristics set up OK...") 

        await asyncio.gather(ble.send_loop(), lbc_poll_loop(ble))
    finally:
        await ble.disconnect()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
