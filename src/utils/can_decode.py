#
# This program reads CAN messages from a Waveshare CAN HAT interface,
# and decodes and prints those messages.
#
# The following CAN_ID details are taken from the Nissan Leaf 2+ tables as specified
# by https://github.com/dalathegreat/leaf_can_bus_messages/QC-CAN_ALL.dbc.  The interpreted
# dbc files are expanded in https://github.com/hwthomas/ccs-chademo/doc/QC_CAN_messages
# These dbc files were updated (June 2026) & all 16-bit values are now Intel format, and
# multiplication factor changed from 0,01 to 1
#
# Only report when message data values change from the previous ones

import can      # for message structure, construction and transmission 
import time     # for sleep and timings
import os
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
        self.minChargeCurrent = None        # CAN-ID 0x100
        self.minBatteryVoltage = None
        self.maxBatteryVoltage = None
        self.chargeRateIndication = None
        
        self.maxChargeTimeMins = None       # CAN-ID 0x101
        self.estChargeTimeMins = None
        self.ratedCapacitykWh = None

        self.targetBatteryVolts = None      # CAN-ID 0x102
        self.chargeCurrentRequest = None
        self.evFaultBits = None
        self.evStatusBits = None
        self.evStateOfCharge = None

        self.maxChargerVoltage = None       # CAN-ID 0x108
        self.maxChargerCurrent = None
        self.thresholdVoltage = None        # threshold voltage for EV protection
        
        self.chargerVoltage = None          # CAN-ID 0x109
        self.chargerCurrent = None

        # end of CHAdeMO test variables
        

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

            if message.arbitration_id == 0x108:
                new_value = int(message.data[1]) + int(message.data[2])*256
                if(self.maxChargerVoltage != new_value):
                    self.addToTrace("ID 0x108: maxChargerVoltage = %d V" % new_value)
                    self.maxChargerVoltage = new_value
                    
                new_value = message.data[3]
                if(self.maxChargerCurrent != new_value):
                    self.addToTrace("ID 0x108: maxChargerCurrent = %d A" % new_value)
                    self.maxChargerCurrent = new_value

                new_value = int(message.data[4]) + int(message.data[5])*256
                if(self.thresholdVoltage != new_value):
                    self.addToTrace("ID 0x108: ThresholdVoltage = %d V" % new_value)
                    self.thresholdVoltage = new_value

            if message.arbitration_id == 0x109:
                new_value = int(message.data[1]) + int(message.data[2])*256
                if(self.chargerVoltage != new_value):
                    self.addToTrace("ID 0x109: actual charger Voltage = %d V" % new_value)
                    self.chargerVoltage = new_value

                new_value = message.data[3]
                if(self.chargerCurrent != new_value):
                    self.addToTrace("ID 0x109: actual charger Current = %d A" % new_value)
                    self.chargerCurrent = new_value

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

    print('Bring up CAN0....')
    os.system("sudo /sbin/ip link set can0 down")    # Prevent 'Busy' error if already UP
    os.system("sudo /sbin/ip link set can0 up type can bitrate 500000")
    time.sleep(0.1) 
    
    try:
        bus = can.Bus(channel='can0', interface='socketcan', can_filters=None)    # allow all CAN-IDs
    except OSError:
        print('Cannot find CAN board.')
        exit()

    print("Testing can_decode using CAN-bus input...")

    # create a can_decode instance, using cbAddToTrace and cbShowStatus functions above
    cdc = can_decode(cdcAddToTrace, cdcShowStatus)

    with bus:           # this is the hardware channel 'can0' created above
        print('Ready')
        while True:
            msg = bus.recv(0)   # non-blocking wait for canbus message
            if msg:
                # decode the message using cdc.can_decode function
                cdc.chademo(msg)

            time.sleep(0.01)      # loop every 10mS until end of data reached 
    
    print("finished decoding data input ")
