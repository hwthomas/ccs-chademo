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
import sys

from configmodule import getConfigValue, getConfigValueBool

class can_decode():
    
    def addToTrace(self, s):
        if not self.traceEnabled:
            return
        self.callbackAddToTrace("[CAN_DECODE] " + s)

    def showStatus(s, selection=""):
        pass
    
    def __init__(self, callbackAddToTrace=None, callbackShowStatus=None):
        self.callbackAddToTrace = callbackAddToTrace
        self.callbackShowStatus = callbackShowStatus
        self.showStatus = callbackShowStatus
  
        # Cache the trace flag once at startup. It is used by addToTrace()
        # which is called many times per second; we avoid re-reading the
        # config file on every call. Must be set before any addToTrace() call,
        # so it stays right at the top of __init__.
        self.traceEnabled = getConfigValueBool("evse_printtrace")
       
        # The following class variables are for testing the CHAdeMO hardware
        self.minChargeCurrent = -1          # CAN-ID 0x100
        self.minBatteryVoltage = -1
        self.maxBatteryVoltage = -1
        self.chargeRateIndication = -1
        
        self.maxChargeTimeMins = -1         # CAN-ID 0x101
        self.estChargeTimeMins = -1
        self.ratedCapacitykWh = -1
            
        self.targetBatteryVolts = -1        # CAN-ID 0x102
        self.chargeCurrentRequest = -1
        self.evFaultBits = -
        self.evStatusBits = -1
        self.evStateOfCharge = -1
        # end of CHAdeMO current variables
        

    def chademo(self, message):
        # 
        # The following CAN_ID details are taken from the Nissan Leaf 2+ tables as specified
        # by https://github.com/dalathegreat/leaf_can_bus_messages/QC-CAN_ALL.dbc.  The interpreted
        # dbc files are expanded in https://github.com/hwthomas/ccs-chademo/doc/QC_CAN_messages
        # These dbc files were updated (June 2026) & all 16-bit values are now Intel format, with
        # the voltage scaling factor changed from 0.01 to 1
        #
        #print("chademo called with message = ", message)
        if message:
            if message.arbitration_id == 0x100:
                new_value = message.data[0]
                if self.minChargeCurrent != new_value:
                    self.addToTrace("CHAdeMO: minChargeCurrent = %d Amps" % new_value)
                    self.minChargeCurrent = new_value
 
                new_value = int(message.data[2]) + int(message.data[3])*256
                if(self.minBatteryVoltage != new_value):
                    self.addToTrace("CHAdeMO: minBatteryVolts = %d V" % new_value)
                    self.minBatteryVoltage = new_value
                    
                new_value = int(message.data[4]) + int(message.data[5])*256
                if(self.maxBatteryVoltage != new_value):
                    self.addToTrace("CHAdeMO: maxBatteryVolts = %d V" % new_value)
                    self.maxBatteryVoltage = new_value

            if message.arbitration_id == 0x101:
                new_value = (int(message.data[5]) + int(message.data[6])*256) * 0.11
                if(self.ratedCapacitykWh != new_value):
                    self.addToTrace("CHAdeMO: ratedCapacity = %d kWh" % new_value)
                    self.ratedCapacitykWh = new_value
                    
            if message.arbitration_id == 0x102:
                new_value = int(message.data[1]) + int(message.data[2])*256
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
    
def cdcAddToTrace(s):
    currentTime_ms = round(time.time()*1000)
    dT_ms = currentTime_ms - startTime_ms
    print("[" + str(dT_ms) + "ms] " + s)

def cdcShowStatus(s, selection=""):
    pass

if __name__ == "__main__":
    print("Testing can_decode using CAN-bus input...")
    # create a can_decode instance, using cbAddToTrace and cbShowStatus functions above
    cdc = can_decode(cdcAddToTrace, cdcShowStatus)

    # use a can.Message object for decoding and subsequent sending
    # see https://python-can.readthedocs.io/en/stable/message.html
    
    with can.Bus() as bus:
        while True:
            msg = can.recv(0)   # non-blocking wait for canbus message

            if msg:
                print(msg)
                # In operation, the canbus message is received from the hardware interface
        
                # decode the message using cdc.can_decode function
                cdc.chademo(msg)

            time.sleep(0.01)      # loop every 10mS until end of data reached 
    
    print("finished decoding data input ")
