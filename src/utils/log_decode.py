#
# This program reads a CAN log from a file written in csv format
# and decodes & prints those CAN_IDs that are used in the CHAdeMO 
# charging sequence (IDs 0x100, 0x101, 0x102, 0x108, 0x109)
# Unrecognised IDs are ignored and not decoded/printed
#
# the log file to be decoded is read as command-line argument[1] 
# ie run command:- 'python log_decode.py short.log'
#
# below is a short log file 'short.log' extracted from 'ZE1-chademo-charging.log'
# in 'https://github.com/dalathegreat/EV-CANlogs' repo. Layout is as follows:-
#
#   Timestamp uS     CAN_ID   ext         data[0..7] as hex bytes
# -1688467625333184,00000100,false,Rx,0,8,06,00,00,00,B3,01,FF,00,
# -1688467625323152,00000101,false,Rx,0,8,00,E4,00,00,00,00,00,00,
# -1688467625313174,00000102,false,Rx,0,8,02,9A,01,6D,00,81,8F,00,
# -1688467625303120,00000200,false,Rx,0,8,FF,00,00,00,FA,00,1A,FF,
# -1688467625246875,00000108,false,Rx,0,8,00,F4,01,87,B3,01,00,00,
# -1688467625241862,00000109,false,Rx,0,8,01,7C,01,64,01,05,D5,24,

import can      # for message structure  
import time     # for sleep and timings
import sys

from configmodule import getConfigValue, getConfigValueBool

class can_decode():

#
# these functions allow log printing as per pyPlc and are just used for
# convenience and to gain familiarity with that program's structure

    def addToTrace(self, s):
        if not self.traceEnabled:   # set in pyPlc.ini by "evse_printtrace"
            return
        self.callbackAddToTrace("[LOG_DECODE] " + s)

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
        self.minChargeCurrent = 0           # CAN-ID 0x100
        self.minBatteryVoltage = 0
        self.maxBatteryVoltage = 0
        self.chargeRateIndication = 100
        
        self.maxChargeTimeMins = 0          # CAN-ID 0x101
        self.estChargeTimeMins = 0
        self.ratedCapacitykWh = 0
            
        self.targetBatteryVoltage = 0       # CAN-ID 0x102
        self.chargeCurrentRequest = 0
        self.evFaultBits = 0
        self.evStatusBits = 0
        self.evStateOfCharge = 0
        
        self.maxChargerVoltage = 0          # CAN-ID 0x108
        self.maxChargerCurrent = 0
        
        self.chargerVoltage = 0             # CAN-ID 0x109
        self.chargerCurrent = 0
        # end of CHAdeMO test variables
        

    def cdm_decode(self, message):
        # 
        # The following CAN_ID details are taken from the Nissan Leaf 2+ tables as specified
        # by https://github.com/dalathegreat/leaf_can_bus_messages/QC-CAN_ALL.dbc.  The interpreted
        # dbc files are expanded in https://github.com/hwthomas/ccs-chademo/doc/QC_CAN_messages
        # These dbc files were updated (June 2026) & all 16-bit values are now Intel format
        # However....
        # Note that all 16-bit (2-byte) data values are in big-endian format,
        # given that this appears to be how these log files were generated
        
        if message:
            if message.arbitration_id == 0x100:
                new_value = message.data[0]
                if self.minChargeCurrent != new_value:
                    self.addToTrace("0x100: minChargeCurrent = %d A" % new_value)
                    self.minChargeCurrent = new_value
 
                new_value = (int(message.data[2]*256) + int(message.data[3])) * 0.01
                if(self.minBatteryVoltage != new_value):
                    self.addToTrace("0x100: minBatteryVolts = %d V" % new_value)
                    self.minBatteryVoltage = new_value
                    
                new_value = (int(message.data[4]*256) + int((message.data[5])) )* 0.01
                if(self.maxBatteryVoltage != new_value):
                    self.addToTrace("0x100: maxBatteryVolts = %d V" % new_value)
                    self.maxBatteryVoltage = new_value

            if message.arbitration_id == 0x101:
                new_value = (message.data[5]*256 + message.data[6]) * 0.11
                if(self.ratedCapacitykWh != new_value):
                    self.addToTrace("0x101: ratedCapacity = %d kWh" % new_value)
                    self.ratedCapacitykWh = new_value
                    
            if message.arbitration_id == 0x102:
                new_value = (message.data[1]*256 + message.data[2]) * 0.01
                if(self.targetBatteryVoltage != new_value):
                    self.addToTrace("0x102: targetBatteryVoltage = %d V" % new_value)
                    self.targetBatteryVoltage = new_value
                    
                new_value = message.data[3]
                if(self.chargeCurrentRequest != new_value):
                    self.addToTrace("0x102: chargeCurrentRequest = %d A" % new_value)
                    self.chargeCurrentRequest = new_value
                    
                new_value = message.data[4]
                if(self.evFaultBits != new_value):
                    self.addToTrace("0x102: evFaultBits = %X" % new_value)
                    self.evFaultBits = new_value
                    
                new_value = message.data[5]
                if(self.evStatusBits != new_value):
                    self.addToTrace("0x102: evStatusBits = %X" % new_value)
                    self.evStatusBits = new_value

                new_value = message.data[6]
                if(self.evStateOfCharge != message.data[6]):
                    self.addToTrace("0x102: evStateOfCharge = %d" % new_value)
                    self.evStateOfCharge = new_value

            if message.arbitration_id == 0x108:
                new_value = (message.data[1]*256 + message.data[2]) * 0.01
                if(self.maxChargerVoltage != new_value):
                    self.addToTrace("0x108: maxChargerVoltage = %d V" % new_value)
                    self.maxChargerVoltage = new_value
                    
                new_value = message.data[3]
                if(self.maxChargerCurrent != new_value):
                    self.addToTrace("0x108: maxChargerCurrent = %d A" % new_value)
                    self.maxChargerCurrent = new_value

            if message.arbitration_id == 0x109:
                new_value = (message.data[1]*256 + message.data[2]) * 0.01
                if(self.chargerVoltage != new_value):
                    self.addToTrace("0x109: chargerVoltage = %d V" % new_value)
                    self.chargerVoltage = new_value

                new_value = message.data[3]
                if(self.chargerCurrent != new_value):
                    self.addToTrace("0x109: chargerCurrent = %d A" % new_value)
                    self.chargerCurrent = new_value

    def mainfunction(self, can_log_file = None):     # can_decode.mainfunction()
        pass
    
pass    # end of can_decode class


# These logging and status functions used as defaults when can_decode class instance created

startTime_ms = round(time.time()*1000)

def cdcAddToTrace(s):
    currentTime_ms = round(time.time()*1000)
    dT_ms = currentTime_ms - startTime_ms
    print("[" + str(dT_ms) + "ms] " + s)

def cdcShowStatus(s, selection=""):
    pass

if __name__ == "__main__":
    print("Testing log_decode using CAN-log file for  input...")
    # create a can_decode instance, using cbAddToTrace and cbShowStatus functions above
    cdc = can_decode(cdcAddToTrace, cdcShowStatus)

    # open and read in each line of the CAN log
    # Note: 'line' is a string of the *whole* line, including the separators
    # eg   "-1688467643250712,00000109,false,Rx,0,8,01,7B,01,64,01,05,D7,24,"

    can_file = sys.argv[1]                  # select short file to read from, or...
                                            # full file from Dala/EV-CANlogs repo
    print("Opening log file ", can_file)
    with open(can_file) as file:
 
        startTime_ms = round(time.time()*1000)
 
        for line in file:                   # iterate through each line in the file
            time.sleep(0.01)                # wait 10mS before next message
            currentTime_ms = round(time.time()*1000)
            ts = currentTime_ms - startTime_ms   # timestamp for CAN message

            items = line.split(',')         # <list> of comma separated <str>
            id = int(bytes(items[1], 'utf-8'), 16)      # extract arbitration id as an <int>
            dlc = int(bytes(items[5], 'utf-8'), 16)     # ditto for data length code (dlc)
            data = bytearray(8)             # build data as <bytearray> of size 8
            for i in range(6,13):           # log file has data[8] in bytes 0..7
                data[i-6] = int(items[i], 16)   # convert items to hex integers

            # generate a CAN message with the parameters read from the log file
            msg = can.Message(timestamp=ts, arbitration_id=id, dlc=dlc, data=data, is_extended_id = False)
            # print(msg)                     # for diagnostics only

            cdc.cdm_decode(msg)             # decode the message as per LEAF info


    
    print("finished decoding CAN-log input ")
