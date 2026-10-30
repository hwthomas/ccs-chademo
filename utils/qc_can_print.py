#!/usr/bin/python3
#
# This is special CAN receive-then-print python program loop for testing the QC-CAN bus on the Leaf Tekna+. 
# All messages received are formatted and printed out on screen, and replies 0x108 & 0x109 generated.
# GPIO signals are monitored and output where required for the tests. 
# For use with Waveshare RS485/CAN boards on the Raspberry Pi, and the RPi.GPIO digital i/o package used.
#
# Make sure Python-CAN is installed first - pip3 install python-can, then 'import can'  as listed below
# 
import can
import RPi.GPIO as GPIO
import time
import os

print('\n\rNissan Leaf Tekna+ Quick-Charge (QC-CAN) bus Receive...Print loop program')

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

print("GPIO inputs and outputs set up")
print("\nBring up CAN0....")
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
    canbus = can.Bus(channel='can0', interface='socketcan', can_filters=filters, receive_own_messages = True)
except OSError:
    print('Cannot find CAN board.')
    exit()

print('GPIO and CAN-bus Ready')

# define a class with variables for the CHAdeMO 'charger' parameters
class CHAdeMO():
    
    def __init__(self):
        self.GPIO = GPIO
        self.canbus = canbus
        self.evseCHAdeMO_version = 2
        self.maxBatteryVoltage = 435
        self.maxChargerVoltage = 510
        self.maxChargerCurrent = 135
        self.thresholdVoltage = 435
        self.chargerVoltage = 0
        self.chargerCurrent = 0
        self.weldDetect = 1
        self.evChargePermit = 0

    # send CAN message 0x108 to the EV with the Charger parameters (maxChargerVoltage, maxChargerCurrent).
    # this message must be send after CAN message 0x100 has been received from the EV with its parameter
    # maxBatteryVoltage.  Parameters maxChargerVoltage/maxChargerCurrent are fixed properties of the charger       
    def canSend0x108(self):
        self.thresholdVoltage = int(min(self.maxBatteryVoltage, self.maxChargerVoltage))     # minimum of what EV 'needs' and what charger can supply
        mv_lo = int(self.maxChargerVoltage) & 0xFF
        mv_hi = int(self.maxChargerVoltage) >> 8
        th_lo = int(self.thresholdVoltage) & 0xFF
        th_hi = int(self.thresholdVoltage) >> 8
        msg = can.Message(arbitration_id=0x108, data=[self.weldDetect, mv_lo, mv_hi, self.maxChargerCurrent, th_lo, th_hi, 0, 0], is_extended_id=False)
        try:
            self.canbus.send(msg)
        except can.CanError:
            print("CAN error: - Message NOT sent")
            self.canbus.shutdown()
            exit()
    
    # send CAN message 0x109 to the EV with charging loop *actual* values (chargerVoltage, chargeCurrent)
    # this message must be send after CAN message 0x102 from the EV with *its* voltage and current requests          
    def canSend0x109(self):
        status = 4    # always report connector locked (adapter has no lock at present)
        cv_lo = int(self.chargerVoltage) & 0xFF
        cv_hi = int(self.chargerVoltage) >> 8
        msg = can.Message(arbitration_id=0x109, data=[self.evseCHAdeMO_version, cv_lo, cv_hi, self.chargerCurrent, 0, status, 0, 0], is_extended_id=False)
        try:
            self.canbus.send(msg)
        except can.CanError:
            print("CAN error: - shutting down")
            self.canbus.shutdown()
            exit()
     
    # define GPIO API for d1/SS1, d2/SS hardware interlocks and evChargePermit
    def setSS1_On(self):
        print("Switching Charge Signal SS1 ON")
        self.GPIO.output(pinSS1, GPIO.HIGH)

    def setSS1_Off(self):
        print("Switching Charge Signal SS1 OFF")
        self.GPIO.output(pinSS1, GPIO.LOW)
 
    def setSS2_On(self):
        print("Switching Charge Signal SS2 ON.")
        self.GPIO.output(pinSS2, GPIO.HIGH)

    def setSS2_Off(self):
        print("Switching Charge Signal SS2 OFF")
        self.GPIO.output(pinSS2, GPIO.LOW)

    def readEVchargePermit(self):               # read GPIO input when called
        new_value = not self.GPIO.input(pin_k)  # pin_k is active(LOW)
        if(new_value != self.evChargePermit):
            self.evChargePermit = new_value     # update via mainfunction scan only
            print("GPIO.pin_k evChargePermit = {0:02X}".format(self.evChargePermit))

pass    # end of class CHAdeMO

# -----------------------------     Start of main program loop      ----------------------------

try:
    cdm = CHAdeMO()                                 # create CHAdeMO class and local variables
    startTime_ms = round(time.time()*1000)          # startTime for message loop
    for i in range(0, 660):             # loop for ~20+ Sec at ~31mS per scan
        # GPIO and CAN-bus updates
        cdm.readEVchargePermit()        # poll EVchargePermit GPIO input (signal k) on each scan
        if(i == 5):
            cdm.setSS1_On()             # after ~150mS enable CAN comms on EV
        if(i == 150):
            cdm.setSS2_On()             # after ~05secs enable EV contactors
        if(i == 500):
            cdm.setSS2_Off()            # after ~15secs disable EV contactors
        if(i == 600):
            cdm.setSS1_Off()            # after ~18secs disable CAN comms on EV
            
        message = cdm.canbus.recv(0)    # non-blocking check for (any) CAN-bus message
        if message:
            currentTime_ms = round(time.time()*1000)    # update current time
            local_ts = currentTime_ms - startTime_ms    # local timestamp for CAN message printing
            # format timestamp, ID, and dlc first
            c = "{0:f} {1:03X} {2:02X} ".format(local_ts, message.arbitration_id, message.dlc)
            # then append the data bytes with single space separator
            for i in range(message.dlc):
                c +=  "{0:02X} ".format(message.data[i])
            print(" {}".format(c))    # space separator between fields of each line in log

            if(message.arbitration_id == 0x100):    # send message 0x108 after 0x100 received
                cdm.canSend0x108()  
            if(message.arbitration_id == 0x102):    # send message 0x109 after 0x102 received
                cdm.canSend0x109()  

        # pause 30mS, then loop for next message or until Ctrl-C
        time.sleep(0.03) 

except KeyboardInterrupt:
    # Catch keyboard interrupt
    print('\n\rKeyboard interrupt') 

print('\n\rShutting bus and CAN0 down') 
canbus.shutdown()
os.system("sudo /sbin/ip link set can0 down")
