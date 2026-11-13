#!/usr/bin/python3
#
# This is special CAN receive-then-print python program loop for testing the QC-CAN bus on the Leaf Tekna+. 
# All messages received are formatted and printed out on screen, and replies 0x108 & 0x109 generated.
# GPIO signals are monitored and output where required for the tests. 
# 
# Comments can be inserted into the log (print("# ")) by starting each comment line with '#'
#
# For use with Waveshare RS485/CAN boards on the Raspberry Pi, and the RPi.GPIO digital i/o package used.
# Make sure Python-CAN is installed first - pip3 install python-can, then 'import can'  as listed below
# 
import can
import RPi.GPIO as GPIO
import time
import os

print("# Nissan Leaf Tekna+ Quick-Charge (QC-CAN) bus Receive...Print loop program")

# set up GPIO outputs and inputs for CHAdeMO hardware signals
GPIO.setmode(GPIO.BOARD)                # set GPIO for board (physical pin) numbering
#   RPI4b GPIO output definitions for interface board (https://github.com/hwthomas/ccs-chademo/wiki/)
pinSS1 = 13     # d1/SS1 Charge sequence signal 1
pinSS2 = 29     # d2/SS2 Charge sequence signal 2
# GPIO input definitions
pin_k = 10      # used for evChargePermit (signal k)
outputs = [pinSS1, pinSS2]
for pin in outputs:                         # process all the outputs defined above
    GPIO.setup(pin, GPIO.OUT)               # set up each of the GPIO pins as outputs
    GPIO.output(pin, GPIO.LOW)              # also set each output LOW at start
    
inputs = [pin_k]
for pin in inputs:
    GPIO.setup(pin, GPIO.IN)

print("# GPIO inputs and outputs set up")
print("# Bring up CAN0....")
os.system("sudo /sbin/ip link set can0 down")    # Prevent 'Busy' error if already UP
os.system("sudo /sbin/ip link set can0 up type can bitrate 500000")

# restrict messages monitored to QC-CAN (CHAdeMO) ones
filters = [
    {"can_id": 0x100, "can_mask": 0x7FF, "extended": False},
    {"can_id": 0x101, "can_mask": 0x7FF, "extended": False},
    {"can_id": 0x102, "can_mask": 0x7FF, "extended": False},
    {"can_id": 0x108, "can_mask": 0x7FF, "extended": False},
    {"can_id": 0x109, "can_mask": 0x7FF, "extended": False} ]
try:
    canbus = can.Bus(channel="can0", interface="socketcan", can_filters=filters, receive_own_messages = True)
except OSError:
    print("# Cannot find CAN board ")
    exit()

print("# GPIO and CAN-bus Ready ")

# define a class with variables for the CHAdeMO 'charger' parameters
class CHAdeMO():
    
    def __init__(self):
        self.GPIO = GPIO
        self.canbus = canbus

        self.evChargePermit = 0
        self.minChargeCurrent = 0       # CAN-ID 0x100
        self.minBatteryVoltage  = 0
        self.maxBatteryVoltage = 435
        self.socPercentFactor = 100
        self.maxChargeTime  = 255       # CAN-ID 0x101
        self.estChargeTime = 0
        self.ratedCapacitykWh = 0
        self.evCdMversion = 2           # CAN-ID 0x102
        self.targetBatteryVoltage = 402
        self.chargeCurrentRequest = 0
        self.evFaultBits = 0
        self.evStatusBits = 0
        self.evStateOfCharge = 50

        self.weldDetect = 1             # CAN-ID 0x108
        self.maxChargerVoltage = 510
        self.maxChargerCurrent = 135
        self.thresholdVoltage = 435
        self.evseCdMversion = 2         # CAN-ID 0x109
        self.chargerVoltage = 0
        self.chargerCurrent = 0
        
        self.voltage_out = 0    # use these values with 0x109 to the EV, rather than self.chargerVoltage and
        self.current_out = 0    # self.chargerCurrent, otherwise decoding 0x109 doesn't print any difference
        
        # end of CHAdeMO variables


    def decode(self, message):  # decodes the CHAdeMO specific messages
        # 
        # The following CAN_ID details are taken from the Nissan Leaf 2+ tables as specified
        # by https://github.com/dalathegreat/leaf_can_bus_messages/QC-CAN_ALL.dbc.  The interpreted
        # dbc files are expanded in https://github.com/hwthomas/ccs-chademo/doc/QC_CAN_messages
        # These dbc files were updated (June 2026) & all 16-bit values are now Intel format
       
        if message.arbitration_id == 0x100:                 # CAN-ID 0x100
            self.minChargeCurrent = message.data[0]
            self.minBatteryVoltage  = int(message.data[2]) + int(message.data[3])*256
            self.maxBatteryVoltage = int(message.data[4]) + int(message.data[5])*256
            self.socPercentFactor = message.data[6]

        if message.arbitration_id == 0x101:                 # CAN-ID 0x101
            self.maxChargeTime  = message.data[2]
            self.estChargeTime = message.data[3]
            self.ratedCapacitykWh = (int(message.data[5]) + int(message.data[6])*256) * 0.1

        if message.arbitration_id == 0x102:                 # CAN-ID 0x102
            self.evCdMversion = message.data[0]
            self.targetBatteryVoltage = int(message.data[1]) + int(message.data[2])*256
            self.chargeCurrentRequest = message.data[3]
            self.evFaultBits = message.data[4]
            self.evStatusBits = message.data[5]
            if self.socPercentFactor > 0:       # (used in this next calculation)
                self.evStateOfCharge = message.data[6] / self.socPercentFactor * 100

        if message.arbitration_id == 0x108:                 # CAN-ID 0x108
            self.weldingDetection = message.data[0]
            self.maxChargerVoltage = int(message.data[1]) + int(message.data[2])*256
            self.maxChargerCurrent = message.data[3]
            self.thresholdVoltage = int(message.data[4]) + int(message.data[5])*256

        if message.arbitration_id == 0x109:                 # CAN-ID 0x109
            self.evseCdMversion = message.data[0]
            self.chargerVoltage = int(message.data[1]) + int(message.data[2])*256
            self.chargerCurrent = message.data[3]


    def estimatedLBCvolts(self, soc_percent):
        # linear interpolation between 338v at SOC=8% and 398v at SOC=100%
        lbcVolts = int(338 + (398-338) * (soc_percent-8) / (100 - 8))
        return lbcVolts
        
    def emulateChargerResponse(self):   # call this after mainfunction has updated all CAN values on each scan
        # This emulates a typical charger by filtering the EV current requests with a first-order filter to produce the
        # 'actual' output lagging current response.  The measured output terminal voltage is then calulated by adding the
        # LBC voltage (estimated from the SOC%) to the volt-drop across the internal resistance of the HV battery.
        # The estimated charger outputs will then be sent back to the EV in CAN message 0x109.
        # The targetBatteryVoltage request from the EV appears not to change throughout the charging cycle.
        # Simulate fast shutdown by setting output current filter to a fast rate if zero current is requested
        # Get the volts and amps inputs from the EV values requested in message 0x102
        current_in = self.chargeCurrentRequest    # updated by CAN message 0x102 from the EV
        # process the current requests with a simple first-order filter
        if(current_in > 0):   
            self.current_out = int(self.chargerCurrent * 0.9 + current_in * 0.1)    # normal 10-sample filter
        else:
            self.current_out = int(self.chargerCurrent * 0.2 + current_in * 0.8)    # more rapid shutdown
        # estimate the charger output voltage from LBC battery volts + (current * internal resistance)
        internalResistance = 0.5       # empirical value based on EV max power output
        self.voltage_out = self.estimatedLBCvolts(self.evStateOfCharge) + internalResistance * self.current_out
        # the EV will be updated with these values when message 0x109 is sent on next scan

    # send CAN message 0x108 to the EV with the Charger parameters (maxChargerVoltage, maxChargerCurrent).
    # this message must be send *after* CAN message 0x100 has been received from the EV with its parameter
    # maxBatteryVoltage.  Parameters maxChargerVoltage/maxChargerCurrent are fixed properties of the charger       
    def canSend0x108(self):
        self.thresholdVoltage = int(min(self.maxBatteryVoltage, self.maxChargerVoltage))     # minimum of what EV 'needs' and what charger can supply
        mv_lo = int(self.maxChargerVoltage) & 0xFF
        mv_hi = int(self.maxChargerVoltage) >> 8
        thr_lo = int(self.thresholdVoltage) & 0xFF
        thr_hi = int(self.thresholdVoltage) >> 8
        msg = can.Message(arbitration_id=0x108, data=[self.weldDetect, mv_lo, mv_hi, self.maxChargerCurrent, thr_lo, thr_hi, 0, 0], is_extended_id=False)
        try:
            self.canbus.send(msg)
        except can.CanError:
            print("# CAN error: - Message NOT sent")
            self.canbus.shutdown()
            exit()
    
    # send CAN message 0x109 to the EV with charging loop 'actual' values (chargerVoltage, chargeCurrent)
    # this message must be send *after* CAN message 0x102 from the EV with *its* voltage and current requests
    # and after the charger emulation has been called to mimic the charger response to these requests          
    def canSend0x109(self):
        status = 4    # always report connector locked (adapter has no lock at present)
        cv_lo = int(self.voltage_out) & 0xFF
        cv_hi = int(self.voltage_out) >> 8
        msg = can.Message(arbitration_id=0x109, data=[self.evseCdMversion, cv_lo, cv_hi, self.current_out, 0, status, 0, 0], is_extended_id=False)
        try:
            self.canbus.send(msg)
        except can.CanError:
            print("# CAN error: - shutting down")
            self.canbus.shutdown()
            exit()
     
    # define GPIO API for d1/SS1, d2/SS hardware interlocks and evChargePermit
    def setSS1_On(self):
        print("# Switching Charge Signal SS1 ON")
        self.GPIO.output(pinSS1, GPIO.HIGH)

    def setSS1_Off(self):
        print("# Switching Charge Signal SS1 OFF")
        self.GPIO.output(pinSS1, GPIO.LOW)
 
    def setSS2_On(self):
        print("# Switching Charge Signal SS2 ON")
        self.GPIO.output(pinSS2, GPIO.HIGH)

    def setSS2_Off(self):
        print("# Switching Charge Signal SS2 OFF")
        self.GPIO.output(pinSS2, GPIO.LOW)

    def readEVchargePermit(self):               # read GPIO input when called
        new_value = not self.GPIO.input(pin_k)  # pin_k is active(LOW)
        if(new_value != self.evChargePermit):
            self.evChargePermit = new_value     # update via direct call on each scan
            print("# GPIO.pin_k evChargePermit = {0:02X}".format(self.evChargePermit))

pass    # end of class CHAdeMO

# -----------------------------     Start of main program loop      ----------------------------

startTime_ms = round(time.time()*1000)          # start the clock

def print_message(message):
    global startTime_ms
    currentTime_ms = round(time.time()*1000)    # update current time
    local_ts = currentTime_ms - startTime_ms    # local timestamp for CAN message printing
    # build format string: timestamp, ID, and dlc first
    c = "{0:.1f} {1:03X} {2:02X} ".format(local_ts, message.arbitration_id, message.dlc)
    # then append the 2-digit hex data bytes with a single space separator after each
    for i in range(message.dlc):
        c +=  "{0:02X} ".format(message.data[i])
    print("{}".format(c))        # print entire message from format string
    
try:
    cdm = CHAdeMO()                                 # create CHAdeMO class and variables
    for scan in range(0, 660):                      # loop for ~20+ Sec at ~31mS per scan
        cdm.readEVchargePermit()                    # poll EVchargePermit GPIO input (signal k) on each scan
        if(cdm.evChargePermit == 1):                # enable EV contactors when EV sets ChargePermit
            cdm.SetSS2_on()
        else:
            cdm.SetSS2_Off()
        
        message = cdm.canbus.recv(0)                # check (non-blocking) for CHAdeMO CAN-bus messages
        if message:
            print_message(message)
            cdm.decode(message)                     # update CHAdeMO variables from message
            cdm.emulateChargerResponse()            # emulate charger response to current/volt requests

            if(message.arbitration_id == 0x102):    # send message 0x108 and 0x109 after 0x102 received
                cdm.canSend0x108()
                time.sleep(0.002)   # delay 2mS  
                cdm.canSend0x109()
                

        # actions initiated at specific scan times  (scan_count * 30mS)               
        if(scan == 0):
            cdm.setSS1_On()         # immediately enable CAN comms on EV
         if(scan == 600):
            cdm.setSS1_Off()        # after ~18secs disable CAN comms on EV

        # pause 30mS, then loop for next message or until Ctrl-C
        time.sleep(0.03) 

except KeyboardInterrupt:
    # Catch keyboard interrupt
    print("# Keyboard interrupt") 

print("# Shutting bus and CAN0 down") 
canbus.shutdown()
os.system("sudo /sbin/ip link set can0 down")
