# File pro_terminal.py. Set up to communicate with OBDBLE device at address "66:1E:87:02:42:D1" 
#
import sys
import time
import asyncio
import logging

from ble_serial.bluetooth.ble_client import BLE_client

ble = None                      # global variables 
multi_msg = bytearray([])       # multi-section message buffer
rx_available = asyncio.Event()  # for send/receive handshake
                            
def rx_handler(reply: bytes):           # handle 'notify' replies from ELM327 device
    global multi_msg, rx_available
    multi_msg += reply                  # append reply to multi-section message
    if(reply[-1] == ord('>')):          # '>' terminates each multi-message
        print("Full message = ", multi_msg)
        multi_msg = bytearray([])       # clear message buffer
    rx_available.set()                  # mark rx buffer available again

async def send_ble(ble: BLE_client, cmd):   # send to ble device with handshake
    global rx_available
    await asyncio.sleep(0.05)       # minimum time between commands
    #print("sending...", cmd)
    rx_available.clear()            # rx *not* available until cmd completed
    ble.queue_send(cmd)             # send cmd to actual ble device
    await rx_available.wait()       # and wait until rx_handler finished

# set up elm327 device for CAN multi-message query/replies on ID 0x79b/0x7bb (Li-Ion battery (LBC) ) 
# see https://mynissanleaf.com/threads/my-nissan-leaf-2021-obd2-elm327-bluetooth-adventure.35042/
async def setup_elm327(ble: BLE_client):
    elm_setup_commands = [      # set up elm327 for *computer* parsing of output
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
    for command in elm_setup_commands:    # add elm327 configuration commands to queue
        await send_ble(ble, command)

#
# task - keyboard_input/send_to_ELM_device loop
#
async def console_loop(ble: BLE_client):
    print("Setting up ELM327 device...")
    await send_ble(ble, b"AT Z\r")       # send hard reset as first command
    # await asyncio.sleep(2.00)           # delay before sending more commands. Just use handshake??
    await setup_elm327(ble)     # complete setup before starting keyboard loop
    print("\nStarting serial terminal loop...")
    print("Type a line and press ENTER...\n>")
    while True:
        # Wait until a line is typed and ENTER is pressed
        # Characters are echo'd to stdout as they are typed
        # To quit, type CTRL+D (EOF) to break out of this loop

        loop = asyncio.get_running_loop()
        line = await loop.run_in_executor(None, sys.stdin.buffer.readline)
        if not line:     # will be empty on EOF (ie CTRL+D on linux)
            break
            
        # replace final '\n' with '\r' to suit ELM327 device
        data = bytearray(line)
        data[-1] = ord('\r')
        await send_ble(ble, data)
        
    print("EOF (CTRL-D) typed...  disconnecting")
    await ble.disconnect()
    raise asyncio.CancelledError    # Cancel all tasks in asyncio.gather()

#
# Start of ble_startup code
#
async def ble_startup():
    print("Starting program pro_terminal.py to query Leaf Tekna+ \n")

    # Connect to BLE device with the following parameters
    # PROSCAN = "66:1E:87:02:42:D1"
    # LELINK2 = "90:59:AF:26:A4:54"
    ADAPTER = "hci0"
    DEVICE = "66:1E:87:02:42:D1"                            # Address of PROSCAN dongle
    SERVICE_UUID =  "0000fff0-0000-1000-8000-00805f9b34fb"  #
    WRITE_UUID =    "0000fff2-0000-1000-8000-00805f9b34fb"  # ['write-without-response', 'write']
    READ_UUID  =    "0000fff1-0000-1000-8000-00805f9b34fb"  # ['notify']
    WRITE_WITH_RESPONSE = True
 
    ble = BLE_client(ADAPTER, 'ID')
    ble.set_receiver(rx_handler)
    try:
        await ble.connect(DEVICE, "public", SERVICE_UUID, 30.0)
        print("ProScan device connected...")
        await ble.setup_chars(WRITE_UUID, READ_UUID, 'rw', WRITE_WITH_RESPONSE)
        print("Service Characteristics set up OK...") 
        await asyncio.sleep(2.0)
        
        await asyncio.gather(ble.send_loop(), console_loop(ble))    # note: return_exceptions=False (default)
        
    except asyncio.CancelledError:
        print("asyncio.CancelledError caught...")
    finally:
        await ble.disconnect()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)	   # logging.INFO / .DEBUG
    
    try:
        asyncio.run(ble_startup())
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass        # task is cancelled on disconnect, so ignore this error


    
