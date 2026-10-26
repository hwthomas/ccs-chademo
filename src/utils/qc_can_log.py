#!/usr/bin/python3
#
# This is simple CAN receive-then-print and log python program loop,
# which listens specifically on the Leaf ZE1 QuichCharge (QC) Can bus. 
# All messages received are printed out on screen, and to a log file.
# The log file name is read as command-line argument[1] 
# ie run command:- 'python qc_can_log.py leaf.log'
# For use with Waveshare RS485/CAN boards on the Raspberry Pi
#
# Make sure Python-CAN is installed first - pip3 install python-can
# then 'import can'  as listed below

# This program is not complete - currently prints only to stdout

import time
import os
import sys
import RPi.GPIO as GPIO   # Raspberry Pi GPIO library
import can

print('\n\rCAN Rx...log test')


# class qcCanLog has a main purpose of waiting for a QC-CAN (Quick Charge CAN-bus) message and printing it.
# However it also decodes some of the Nissan Leaf messages in order to construct and send back the main
# charger (EVSE) messages to the EV (car) which affect how the car then responds.  It is this response which
# needs to be investigated and checked, and this is a first step towards that. 
# In operation, creating an instance of qcCanLog creates the log file and the CAN-bus as class variables, and
# calling 'qcCanLog.close()' tidies up at the end.

class qcCanLog:
    
    # define class variables
    self.loopcounter = 0
    self.canbus = None
    self.logfile = None
    self.startTime_mS = 0.0             # time in mS at which class is created
        
    # EV tells the charger the maximum volts it 'needs' via CAN-ID 0x100
    self.maxBatteryVoltage = 402        # initialise to valid value

    # EV voltage and current requests received in CAN-ID 0x102
    self.targetBatteryVoltage = 0       # target voltage request
    self.chargeCurrentRequest = 0       # target current request
    
    # EVSE tells the EV the maximum volts and amps available (ie that it can supply) via CAN-ID 0x108
    self.weldDetect = 0                 # CAN-ID 0x108 limit values from the charger to the car
    self.maxChargerVoltage = 0          # its maximum available voltage
    self.maxChargerCurrent = 0          # its maximum available current  
    self.thresholdVoltage = 0           # this is the maximum it will *use* (for protection of the EV)

    self.evseCHAdeMO_version = 2        # CAN-ID 0x109 - CHAdeMO version charger can use
    self.chargerVoltage = 0             # then the actual voltage and current being delivered in
    self.chargerCurrent = 0             # response to the EV 0x102 requests in the charging loop

    # send CAN message 0x108 to the EV with the Charger parameters (maxChargerVoltage, maxChargerCurrent).
    # this message must be send after CAN message 0x100 has been received from the EV with its parameter
    # maxBatteryVoltage.  Parameters maxChargerVoltage/maxChargerCurrent are fixed properties of the charger       
    def canSend0x108(self):
        # construct CAN message 0x108 and send it (even if maxVolts or maxCurrent haven't changed)
        self.thresholdVoltage = int(min(self.maxBatteryVoltage, self.maxChargerVoltage))     # minimum of what EV 'needs' and what charger can supply
        mv_lo = int(self.maxChargerVoltage) & 0xFF
        mv_hi = int(self.maxChargerVoltage) >> 8
        th_lo = int(self.thresholdVoltage) & 0xFF
        th_hi = int(self.thresholdVoltage) >> 8
        try:
            msg = can.Message(arbitration_id=0x108, data=[self.weldDetect, mv_lo, mv_hi, self.maxChargerCurrent, th_lo, th_hi, 0, 0], is_extended_id=False)
            self.canbus.send(msg)
        except can.CanError:
            print("CAN error: - Message NOT sent")
            bus.shutdown(
            exit()

    
    # send CAN message 0x109 to the EV with charging loop *actual* values (chargerVoltage, chargeCurrent)
    # this message must be send after CAN message 0x102 from the EV with *its* voltage and current requests          
    def canSend0x109(self):
        # construct CAN message 0x109 and send it (even if volts or current haven't changed)
        status = 4    # always report connector locked (adapter has no lock at present)
        cv_lo = int(self.chargerVoltage) & 0xFF
        cv_hi = int(self.chargerVoltage) >> 8
        try:
            msg = can.Message(arbitration_id=0x109, data=[self.evseCHAdeMO_version, cv_lo, cv_hi, self.chargerCurrent, 0, status, 0, 0], is_extended_id=False)
            self.canbus.send(msg)
        except can.CanError:
            print("CAN error: - shutting down")
            bus.shutdown(
            exit()


    # Check CAN message and decode if necessary to extract EV variables, and then send charger messages back to EV
    def decode_message(self, message):
        if(message.arbitration_id == 0x100):
            self.maxBatteryVoltage = int(message.data[4]) + int(message.data[5])*256
            self.canSend0x108()      # send reply 0x108 to EV

        if(message.arbitration_id == 0x102):
            self.targetBatteryVoltage = int(message.data[1]) + int(message.data[2])*256
            self.chargeCurrentRequest = message.data[3]
        self.canSend0x109()      # send reply 0x109 to EV
            
    def __init__(self):
        # open log file to be written to, as first argument to command line
        if(sys.argv[1] != ''):
            self.logfile = sys.argv[1]      # get log filename from command-line
            print("Opening log file ", logfile, " for writing")
            open(self.logfile, 'rw')
        else:
            print("Please supply log file name as first program argument")
        exit

        print('Bring up CAN0....')
        os.system("sudo /sbin/ip link set can0 down")    # Prevent 'Busy' error if already UP
        os.system("sudo /sbin/ip link set can0 up type can bitrate 500000")
        time.sleep(0.1) 

        # set up filters to listen for the following CHAdeMO CAN messages only
        # and listen for (receive) our own transmitted messages as well
        filters = [
            {"can_id": 0x100, "can_mask": 0x7FF, "extended": False},
            {"can_id": 0x101, "can_mask": 0x7FF, "extended": False},
            {"can_id": 0x102, "can_mask": 0x7FF, "extended": False},
            {"can_id": 0x108, "can_mask": 0x7FF, "extended": False},
            {"can_id": 0x109, "can_mask": 0x7FF, "extended": False} ]
        try:
            self.canbus = can.Bus(channel='can0', interface='socketcan', can_filters=filters, receive_own_messages = True)
        except OSError:
            print('Cannot find CAN board.')
            exit()

        print('CAN-bus Ready...')
        
        currentTime_mS = round(time()*1000)
        self.startTime_mS = currentTime_mS      # snapshot start time in mS
  

    # qcCanLog mainfunction is written as a non-blocking routine, which is called to monitor the CAN-bus for a message
    # and to format and print it to stdout as well as the log file.  It also checks which CAN message has been received
    # because IDs 0x100 and 0x102 from the car have parameters which are used in IDs 0x108 and 0x109 back to the EV
    
    def mainfunction(self): 
        try:
            message = self.canbus.recv(0)   # non-blocking check for relevant CAN-bus message
            if message:
                self.canActive = True       # something is happening on the EV CAN-bus
                currentTime_mS = round(time()*1000)
                dT_mS = currentTime_mS - self.startTime_mS
                
                # format timestamp, ID, and dlc first
                c = '{0:f} {1:03X} {2:02X} '.format(dT_mS, message.arbitration_id, message.dlc)
                # then format the data bytes with single space separator
                for i in range(message.dlc ):
                    c +=  '{0:02X} '.format(message.data[i])

                print(' {}'.format(c))    # print to stdout (write to log will come later...)
                
                self.decode_message(message)    # check message and decode if necessary
                
        except KeyboardInterrupt:
        # Catch keyboard interrupt
        print('\n\rKeyboard interrupt') 
        
    def close(self):
        self.logfile.close()        # close log file  
        self.canbus.shutdown()      # shut CAN-bus down cleanly
        os.system("sudo /sbin/ip link set can0 down")

pass    # end of class qcCanLog


# -----------------------test code for class cqCanLog--------------------------

if __name__ == "__main__":
   
    print("Running program qcCanLog for ~30s...")

    # create instance of qcCanLog
    qc = qcCanLog()
    qc.maxChargerVoltage = 500      # set up typical charger Max (available) volts and amps
    qc.maxChargerCurrent = 135      # these values are sent to EV via 0x108 after 0x100 received
    qc.chargerVoltage = 0           # set actual HV volts & amps output to zero
    qc.chargerCurrent = 0           # these values are sent to EV via 0x109 after 0x102 received
 
    # the following loop is structured so that at various points parameters can be changed, and the EV response
    # monitored for timeouts, etc.  Initially, the loop is set to run for 1000 mainfunction scans at ~31mS/scan
    # which is approximately 30secs  
    try:
        for i in range(0, 1000):    # loop for ~30+ Sec at ~31mS per scan
            qc.mainfunction()       # poll Nissan Leaf+, updating CAN-bus variables to/from the EV on each scan
            if (i==100):            # after ~3s...
                print("Start EV CAN-bus and log all EV canbus responses")

            if (i==300):            # by now (~10s after SS1), EV should assert signal 'k' ChargePermit 
                print("Activate charge signal d2/SS2 to EV to enable HV contactors")

            if (i==400):           # 
                pass
            if (i==700):            # 
                pass
            if (i==800):            # set EV current demand to zero
                print("Turn d2/SS2 off")
            if (i==900):
                print("Turn d1/SS1 off")

            sleep(0.03)             # wait for approx. scan time. ie 30mS sleep + 1mS computation

    except KeyboardInterrupt:       # ctrl-C quits if all else fails!
            pass
    print("\nShutting down QC_CAN-bus program safely...")
    qc.close()                      # close lof  file and QC_CAN cleanly 
    print("Nissan Leaf QC bus test finished.")

