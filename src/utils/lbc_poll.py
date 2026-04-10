import asyncio
import logging
from ble_serial.bluetooth.ble_client import BLE_client

hv_volts = 0    # define these globals for group analysis results
hv_soc = 0
multi_msg = bytearray[]             # empty multi-section buffer

def receive_callback(reply: bytes):
    # a group multi-message reply may come in several sections, but will
    # be terminated by a prompt ('>') character.  Build the full group 
    # message from the (partial) sections before trying to analyse it.
    multi_msg += reply              # continue building full message
    if(reply[-1] == ord('>'):       # check for message terminator
        group = multi_msg           # copy (possible) group message
        multi_msg = []              # and reset message buffer
    if( len(group) == 138):         # check for valid group length
        print(group)                                    # diagnostics only
        analyse_group(group)        # and analyse if OK

async def lbc_setup_loop(ble: BLE_client):
    ble.queue_send(b'ATZ\r')        # hard reset to ELM327
    await asyncio.sleep(2.0)        # wait for device to settle
    for cmd in elm_commands:
        await asyncio.sleep(0.1)    # 100mS between setup commands
        ble.queue_send(cmd)
    
    lbc_queries = 0         # Now query LBC Group 1 (2 off only)
    cmd = b'022101\r'
    while (lbc_queries < 2):
        await asyncio.sleep(5.0)
        lbc_queries += 1
        ble.queue_send(cmd)
    pass                    # lbc_setup_loop task is now complete 
        
elm_commands = [            # set up elm327 for *computer* parsing of output
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

async def main():
    ADAPTER = "hci0"
    SERVICE_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
    WRITE_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"
    READ_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"
    DEVICE = "90:59:AF:26:A4:54"        # OBDBLE dongle address
    WRITE_WITH_RESPONSE = True

    ble = BLE_client(ADAPTER, 'ID')
    ble.set_receiver(receive_callback)

    try:
        await ble.connect(DEVICE, "public", SERVICE_UUID, 30.0)
        await ble.setup_chars(WRITE_UUID, READ_UUID, "rw", WRITE_WITH_RESPONSE)
        await asyncio.gather(ble.send_loop(), lbc_setup_loop(ble))
    finally:
        await ble.disconnect()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
