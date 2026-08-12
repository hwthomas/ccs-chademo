#
# This program reads a CAN log from a file written in csv format
# and generates CAN messages to be passed to the decode program
# which understands some ID meaning and layout, based on the
# HardwareInterface module from myPlc (IDs 0x100, 0x101, 0x102)
# Unrecognised IDs are ignored and not decoded/printed
#
# simple log file 'short.log' extracted from 'ZE1-chademo-charging.log'
# in 'https://github.com/dalathegreat/EV-CANlogs' repo. Layout as per-

# -1688467643234759,00000100,false,Rx,0,8,06,00,00,00,B3,01,FF,00,
# -1688467643224751,00000101,false,Rx,0,8,00,E4,00,00,00,00,00,00,
# -1688467643214763,00000102,false,Rx,0,8,02,9A,01,73,00,81,8F,00,
# -1688467643203801,00000200,false,Rx,0,8,FF,00,00,00,FA,00,1A,FF,

import can      # for message structure, construction and transmission 
import time     # for sleep and timings

class can_decode():
    
    def __init__(self, callbackAddToTrace=None, callbackShowStatus=None):
        self.callbackAddToTrace = callbackAddToTrace
        self.callbackShowStatus = callbackShowStatus
        
        # The following class variables are for testing the CHAdeMO hardware
        self.minChargeCurrent = 0           # CAN-ID 0x100
        self.minBatteryVoltage = 0
        self.maxBatteryVoltage = 0
        self.chargeRateIndication = 100
        
        self.maxChargeTimeMins = 0          # CAN-ID 0x101
        self.estChargeTimeMins = 0
        self.ratedCapacitykWh = 0
            
        self.targetBatteryVolts = 0         # CAN-ID 0x102
        self.chargeCurrentRequest = 0
        self.evFaultBits = 0
        self.evStatusBits = 0
        self.evStateOfCharge = 0
        # end of CHAdeMO current variables
        

    def chademo(message = ''):
        # 
        # message = self.canbus.recv(0)    # non-blocking check for (any) CAN-bus message
        # In operation, the canbus message is received from the hardware interface
        # For this test, we are passed each message as each line is read from the log file
        #
        # The following CAN_ID details are taken from the Nissan Leaf 2+ tables as specified
        # by https://github.com/dalathegreat/leaf_can_bus_messages/QC-CAN_ALL.dbc.  The interpreted
        # dbc files are expanded in https://github.com/hwthomas/ccs-chademo/doc/QC_CAN_messages
        # These dbc files were updated (June 2026) & all 16-bit values are now Intel format
        #
        if message:
            if message.arbitration_id == 0x100:
                new_value = message.data[0]
                if self.minChargeCurrent != new_value:
                    self.addToTrace("CHAdeMO: minChargeCurrent = %d Amps" % new_value)
                    self.minChargeCurrent = new_value
 
                new_value = (message.data[3]<<8 + message.data[2]) * 0.01
                if(self.minBatteryVolts != new_value):
                    self.addToTrace("CHAdeMO: minBatteryVolts = %d V" % new_value)
                    self.minBatteryVolts = new_value
                    
                new_value = (message.data[5]<<8 + message.data[4]) * 0.01
                if(self.maxBatteryVolts != new_value):
                    self.addToTrace("CHAdeMO: maxBatteryVolts = %d V" % new_value)
                    self.maxBatteryVolts = new_value

            if message.arbitration_id == 0x101:
                new_value = (message.data[6]<<8 + message.data[5]) * 0.11
                if(self.ratedCapacitykWh != new_value):
                    self.addToTrace("CHAdeMO: ratedCapacity = %d kWh" % new_value)
                    self.ratedCapacitykWh = new_value
                    
            if message.arbitration_id == 0x102:
                new_value = (message.data[2]<<8 + message.data[1]) * 0.01
                if(self.targetBatteryVolts != new_value):
                    self.addToTrace("CHAdeMO: targetBatteryVolts = %d V" % new_value)
                    self.targetBatteryVolts = new_value
                    
                new_value = message.data[3]
                if(self.chargeCurrentRequest != new_value):
                    self.addToTrace("CHAdeMO: chargeCurrentRequest = %d A" % new_value)
                    self.chargeCurrentRequest = new_value
                    
                new_value = message.data[4]
                if(self.evFaultBits != new_value):
                    self.addToTrace("CHAdeMO: evFaultBits = %X" % new_value)
                    self.evFaultBits = new_value
                    
                new_value = message.data[5]
                if(self.evStatusBits != new_value):
                    self.addToTrace("CHAdeMO: evStatusBits = %X" % new_value)
                    self.evStatusBits = new_value

                new_value = message.data[6]
                if(self.evStateOfCharge != message.data[6]):
                    self.addToTrace("CHAdeMO: evStateOfCharge = %d" % new_value)
                    self.evStateOfCharge = new_value


    def mainfunction(self, can_log_file = None):     # can_decode.mainfunction()
        #if (getConfigValueBool("soc_simulation")):
        #    if(self.simulatedSoc<100):
        pass
    
pass    # end of can_decode class


 startTime_ms = round(time.time()*1000)

# These logging and status functions used as defaults when can_decode class instance created
    
def cbAddToTrace(s):
    currentTime_ms = round(time.time()*1000)
    dT_ms = currentTime_ms - startTime_ms
    print("[" + str(dT_ms) + "ms] " + s)

def cbShowStatus(s, selection=""):
    pass

if __name__ == "__main__":
    print("Testing can_decode using a can.log file for input...")
    # create a can_decode instance, using cbAddToTrace and cbShowStatus functions above
    cdc = can_decode(cbAddToTrace, cbShowStatus)

    can_file = "short.log"                  # select short file to read from or..
    # can_file = "ZE1-chademo-charging.log" # full file from Dala/EV-CANlogs repo

    # read from can log file. Note: 'line' is a string of the *whole* line, including separators
    # eg   "-1688467643250712,00000109,false,Rx,0,8,01,7B,01,64,01,05,D7,24,"
    
    # use a can.Message object for decoding and subsequent sending
    # see https://python-can.readthedocs.io/en/stable/message.html

    # first, read in and decode the can.log
    with open(can_file) as file:
        for line in file:                   # iterate through each line in the file
            items = line.split(',')         # <list> of comma separated <str>
            #id = bytes(items[1], 'utf-8')   # convert arbitration_ID to <bytes>
            id = int(bytes(items[1], 'utf-8'))      # arbitration id to be supplied as an <int>
            dlc = int(bytes(items[5], 'utf-8'))     # ditto for data length code (dlc)
            print(int(id))
            data_bytes = []                 # build data_bytes as <list>
            for i in range(6,14):
                data_bytes.extend(bytes(items[i], 'utf-8') )  # select data bytes
            
            db = bytes(data_bytes)
            print("type of data_bytes = ", type(data_bytes))
            msg = can.Message(arbitration_id=id, dlc=dlc, data=db)
            print(msg)

            
            #for i in range(0,7):
            #    print(data_bytes[i])
            
            #ba = bytes(data_bytes)
            #print("byte array = ", ba)
            
            #bytes_merged = b''.join(data_bytes)
            #byte_data  = bytearray(bytes_merged)
    
            
            # decode the message using cdc.can_decode function
            #cdc.chademo(msg)

            time.sleep(0.1)      # loop every 100mS until file end reached 
    
    print("finished decoding file ", can_file)
