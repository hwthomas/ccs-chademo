#
# This hardware interface has been set up to use *only* the CHAdeMO interface, as required by the
# Waveshare Raspberry Pi4 HAT RS485/CAN board.  It also uses the RPi.GPIO interface digital I/O.
# 

from pyPlcModes import *
from time import sleep, time
from configmodule import getConfigValue, getConfigValueBool
import sys # For exit_on_session_end hack
import os  # For os.system calls
from random import random
from cableChecker import *
from environment_info import getLogFileNumber

if (getConfigValue("digital_output_device") == "rpi_gpio"):
    import RPi.GPIO as GPIO   # Raspberry Pi GPIO library

    # RPI4b GPIO output definitions for interface board (https://github.com/hwthomas/ccs-chademo/wiki/)
    pinCp  = 40     # alter these for our interface boards
    pinSS1 = 29     # d1/SS1 Charge sequence signal 1
    pinSS2 = 13     # d2/SS2 Charge sequence signal 2
    pinWdg = 33     # pinWdg WatchDog charge pump (future)

    GPIO.setmode(GPIO.BOARD)                    # set GPIO for board (physical pin) numbering
    pins = [pinCp, pinSS1, pinSS2, pinWdg]
    for pin in pins:                            # process all the outputs defined above
        GPIO.setup(pin, GPIO.OUT)               # set up each of the GPIO pins as outputs
        GPIO.output(pin, GPIO.LOW)              # also set each output LOW at start

if (getConfigValue("charge_parameter_backend")=="chademo"):
    # As we use the CHAdeMO backend, we need to use CAN - (pip3 install python-can)  
    import can

class hardwareInterface():
    def needsSerial(self):
        return False # none of the functions need a serial port.

    def addToTrace(self, s):
        if not self.traceEnabled:
            return
        self.callbackAddToTrace("[CHADEMO_INTERFACE] " + s)

    def displayStateAndSoc(self, infonumber, state, soc):
        # no output display device used
        self.infonumber = infonumber
        if (soc>=0) and (soc<=100):
            self.soc_percent = soc

    def publishChargeProgress(self, value):
        # Publish Start/Stop/Renegotiate explicitly so external orchestrators
        # can act on the EV's intent without inferring it from fsm_state.
        pass    # no action for chademo interface

    def displayVehicleBatteryCapacity(self, batteryCapacity):
        self.addToTrace("displayVehicleBatteryCapacity " + str(batteryCapacity))

    def displayVehicleEVCCID(self, evccid):
        self.addToTrace("displayVehicleEVCCID " + evccid)

    def setStateB(self):
        self.addToTrace("Setting CP line into state B.")
        if (getConfigValue("digital_output_device")=="rpi_gpio"):
            GPIO.output(pinCp, GPIO.LOW)
        self.outvalue &= ~1

    def setStateC(self):
        self.addToTrace("Setting CP line into state C.")
        if (getConfigValue("digital_output_device")=="rpi_gpio"):
            GPIO.output(pinCp, GPIO.HIGH)
        self.outvalue |= 1
#
##################################################
#
# Following digital outputs are dummies
# at present, these are the only ones referenced in fsmPev.py, and
# need to be clarified and updated with CHAdeMO signals
# >> NB getPowerRelayOn is used in hardwareInterface.mainfunction test << #
#
    def setPowerRelayOn(self):
        self.addToTrace("Switching PowerRelay ON.")
#       if (getConfigValue("digital_output_device")=="rpi_gpio"):
#           GPIO.output(PinPowerRelay, GPIO.HIGH)
        self.outvalue |= 0x10

    def setPowerRelayOff(self):
        self.addToTrace("Switching PowerRelay OFF.")
#       if (getConfigValue("digital_output_device")=="rpi_gpio"):
#           GPIO.output(PinPowerRelay, GPIO.LOW)
        self.outvalue &= ~0x10

    def setRelay2On(self):
        self.addToTrace("Switching Relay2 ON.")
        self.outvalue |= 0x20

    def setRelay2Off(self):
        self.addToTrace("Switching Relay2 OFF.")
        self.outvalue &= ~0x20

##################################################

#
# These are the CHAdeMO sequence signals, which need to be activated
# in the fsmCdM code at appropriate points (to be determined)
#
    def setSS1_On(self):
        self.addToTrace("Switching Charge Signal SS1 ON.")
        if (getConfigValue("digital_output_device")=="rpi_gpio"):
            GPIO.output(pinSS1, GPIO.HIGH)
        self.outvalue |= 2

    def setSS1_Off(self):
        self.addToTrace("Switching Charge Signal SS1 OFF.")
        if (getConfigValue("digital_output_device")=="rpi_gpio"):
            GPIO.output(pinSS1, GPIO.LOW)
        self.outvalue &= ~2
 
    def setSS2_On(self):
        self.addToTrace("Switching Charge Signal SS2 ON.")
        if (getConfigValue("digital_output_device")=="rpi_gpio"):
            GPIO.output(pinSS2, GPIO.HIGH)
        self.outvalue |= 4

    def setSS2_Off(self):
        self.addToTrace("Switching Charge Signal SS2 OFF.")
        if (getConfigValue("digital_output_device")=="rpi_gpio"):
            GPIO.output(pinSS2, GPIO.LOW)
        self.outvalue &= ~4

    def setWdog_On(self):
        if (getConfigValue("digital_output_device")=="rpi_gpio"):
            GPIO.output(pinWdg, GPIO.HIGH)
        self.outvalue |= 8

    def setWdog_Off(self):
        if (getConfigValue("digital_output_device")=="rpi_gpio"):
            GPIO.output(pinWdg, GPIO.LOW)
        self.outvalue &= ~8
#
#   This is a first attempt at providing a delay during which the Watchdog is continually fired
#   It defines a preDelay and postDelay, with the time in-between as a 2mS/2mS square wave
#   It probably won't be used to start with, until the asyncio/non-blocking code gets sorted
#
    def fireWdog(self, preDelay, postDelay, totalDelay): 
        squareTime = totalDelay - (preDelay + postDelay)
        sleep(preDelay)
        tSq = 0
        sq = 0.002      # 2mS On and Off squarewave
        while(tSq <= squareTime):
            self.setWdog_On()
            sleep(sq)
            self.setWdog_Off()
            sleep(sq)
            tSq += 2*sq
        sleep(postDelay)

#
# Where is this relay confirmation required in CHAdeMO?  - [fsmPev.py line 603]
#
    def getPowerRelayConfirmation(self):
        if (getConfigValue("digital_output_device")=="rpi_gpio"):
            pass    # return self.contactor_confirmed
        return 1 # todo: self.contactor_confirmed

    def triggerConnectorLocking(self):
        self.addToTrace("Locking CCS2 connector")
        if (getConfigValue("digital_output_device")=="rpi_gpio"):
            pass
            # todo control the lock motor into lock direction until the end (time based or current based stopping?)

    def triggerConnectorUnlocking(self):
        self.addToTrace("Unlocking the connector")
        if (getConfigValue("digital_output_device")=="rpi_gpio"):
            pass
            # todo control the lock motor into unlock direction until the end (time based or current based stopping?)

    def isConnectorLocked(self):
        # TODO: Read the lock= value from the hardware so that this works
        if (getConfigValue("digital_output_device")=="rpi_gpio"):
            pass    #    return self.lock_confirmed
        return 1 # todo: use the real connector lock feedback

    def setChargerParameters(self, maxVoltage, maxCurrent):
        self.addToTrace("Setting charger parameters maxVoltage=%d V, maxCurrent=%d A" % (maxVoltage, maxCurrent))
        self.maxChargerVoltage = int(maxVoltage)
        self.maxChargerCurrent = int(maxCurrent)

    def setChargerVoltageAndCurrent(self, voltageNow, currentNow):
        self.addToTrace("Setting charger present values Voltage=%d V, Current=%d A" % (voltageNow, currentNow))
        self.chargerVoltage = int(voltageNow)
        self.chargerCurrent = int(currentNow)

    def setPowerSupplyVoltageAndCurrent(self, targetVoltage, targetCurrent, strMode):
        # if we are the charger, and have a real power supply which we want to control, we do it here
        # self.homeplughandler.sendSpecialMessageToControlThePowerSupply(targetVoltage, targetCurrent)
        # here we can publish the voltage and current requests received from the PEV side
        self.evseModePowerSupplyTargetVoltage = targetVoltage
        self.evseModePowerSupplyTargetCurrent = targetCurrent
        self.evseModePowerSupplyMode = strMode
        if (strMode == "precharge"):
            self.psu.selectDriverForPrecharge()
            self.psu.setVoltage(targetVoltage)
        if (strMode == "currentdemand"):
            self.psu.selectDriverForCurrentDemand()
            self.psu.setVoltage(targetVoltage)
        if (strMode == "weldingdetection"):
            self.psu.selectDriverForWeldingDetection()
            self.psu.setVoltage(targetVoltage)

    def getInletVoltage(self):
        # uncomment this line, to take the simulated inlet voltage instead of the really measured
        # self.inletVoltage = self.simulatedInletVoltage
        return self.inletVoltage

    def getEvsePhysicalVoltage(self):
        return self.EvsePhysicalVoltage

    def getEvsePhysicalCurrent(self):
        return self.EvsePhysicalCurrent

    def getAccuVoltage(self):
        if (getConfigValue("charge_parameter_backend") == "chademo"):
            return self.accuVoltage
        #todo: get real measured voltage from the accu
        self.accuVoltage = 230
        return self.accuVoltage

    def getAccuMaxCurrent(self):
        if (getConfigValue("digital_output_device")=="rpi_gpio"):
            # The overall current limit is currently hardcoded in
            # OpenV2Gx/src/test/main_commandlineinterface.c
            EVMaximumCurrentLimit = 250
            if self.accuMaxCurrent >= EVMaximumCurrentLimit:
                return EVMaximumCurrentLimit
            return self.accuMaxCurrent
        #todo: get max charging current from the BMS
        self.accuMaxCurrent = 10
        return self.accuMaxCurrent

    def getAccuMaxVoltage(self):
        if (getConfigValue("charge_parameter_backend")=="chademo"):
            return self.accuMaxVoltage #set by CAN
        elif getConfigValue("charge_target_voltage"):
            self.accuMaxVoltage = getConfigValue("charge_target_voltage")
        else:
            #todo: get max charging voltage from the BMS using ELM327 dongle
            self.accuMaxVoltage = 230
        return self.accuMaxVoltage

    def getIsAccuFull(self):
        #todo: get "full" indication from the BMS
        self.IsAccuFull = (self.simulatedSoc >= 98)
        return self.IsAccuFull

    def getSoc(self):
        if self.callbackShowStatus:
            self.callbackShowStatus(format(self.soc_percent,".1f"), "soc")
       #todo: get SOC from the BMS using ELM327 dongle
        self.callbackShowStatus(format(self.simulatedSoc,".1f"), "soc")
        return self.simulatedSoc

    def stopRequest(self):
        return not self.enabled

    def isUserAuthenticated(self):
        # If the user needs to authorize, fill this function in a way that it returns False as long as
        # we shall wait for the users authorization, and returns True if the authentication was successfull.
        # Discussing here: https://github.com/uhi22/pyPLC/issues/28#issuecomment-2230656379
        # For testing purposes, we just use a counter to decide that we return
        # once "ongoing" and then "finished".
        if (self.demoAuthenticationCounter<1):
            self.demoAuthenticationCounter += 1
            return False
        else:
            return True

    def initPorts(self):
        if (getConfigValue("charge_parameter_backend") == "chademo"):
            filters = [
               {"can_id": 0x100, "can_mask": 0x7FF, "extended": False},
               {"can_id": 0x101, "can_mask": 0x7FF, "extended": False},
               {"can_id": 0x102, "can_mask": 0x7FF, "extended": False}]
            self.canbus = can.Bus(interface='socketcan', channel="can0", can_filters = filters)


    def __init__(self, callbackAddToTrace=None, callbackShowStatus=None, homeplughandler=None, mode=C_PEV_MODE):
        self.callbackAddToTrace = callbackAddToTrace
        self.callbackShowStatus = callbackShowStatus
        self.homeplughandler = homeplughandler
        self.mode = mode
        # Cache the trace flag once at startup. It is used by addToTrace()
        # which is called many times per second; we avoid re-reading the
        # config file on every call. Must be set before any addToTrace() call,
        # so it stays right at the top of __init__.
        self.traceEnabled = getConfigValueBool("evse_printtrace")

        # The following conditional code enables (future) hardware charger extensions
        if (self.mode==C_EVSE_MODE):
            if (getConfigValueBool('evse_simulate_precharge')):
                self.isPhysicalVoltageSimulated = True
                self.simulatedPhysicalVoltage = 2.2 # simulate a small offset in measurement
            else:
                 # We have a physical voltage measurement. The physical voltage
                 # is available in self.EvsePhysicalVoltage.
                self.isPhysicalVoltageSimulated = False
            if (getConfigValue("evsemode_environment") == "focccicape"):
                from powersupplyInterface_DiDeBoCCS import powersupplyInterface
                self.isFoccciCape = True
            else:
                from powersupplyInterface_other import powersupplyInterface
                self.isFoccciCape = False

            self.psu = powersupplyInterface()
            self.cableChecker = cableChecker(self.psu)
            # print("PowerSupply Type = ", type(self.psu))    # HWT debug code
            # print("CableCheckerType = ", type(self.cableChecker))    # ditto

            if (getConfigValueBool('evse_pretended_cable_check')):
                self.cableChecker.setPretendedMode()

        self.loopcounter = 0
        self.outvalue = 0       # keep track internally of GPIO digital outputs
                                # bit 0 = pinCP  (State_B = 0; State_C = 1)
                                # bit 1 = pinSS1 (SS1 signal [off = 0; on = 2] )
                                # bit 2 = pinSS2 (SS2 signal [off = 0; on = 4] )
                                # bit 3 = pinWdg (RPi Watchdog: flip HIGH/LOW  )

                                # bit 4 = pinPowerRelay (off = 0; on = 0x10)
                                # bit 5 = pinRelay2     (off = 0; on = 0x20)

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
        
        self.simulatedSoc = 20.0    # percent
        self.demoAuthenticationCounter = 0
        self.enabled = True         # Charging enabled
        self.buttonDebounceCounter = 0
        self.buttonStopPhaseCounter = 0

        self.inletVoltage = 0.0 # volts ring-buffer
        self.accuVoltage = 0.0
        self.lock_confirmed = False  # Confirmation from hardware
        self.cp_pwm = 0.0
        self.soc_percent = 0.0
        self.capacity = 0.0
        self.accuMaxVoltage = 0.0
        self.accuMaxCurrent = 0.0
        self.contactor_confirmed = False    # Confirmation from hardware
        self.plugged_in = None              # None means "not known yet"
        self.lastReceptionTime = 0

        self.maxChargerVoltage = 0
        self.maxChargerCurrent = 10
        self.chargerVoltage = 0
        self.chargerCurrent = 0
        
        self.infonumber = 0     # these are new, and only for Charger project?
        self.focccicapeCycleCounter = 0
        self.evseModePowerSupplyTargetVoltage = 0
        self.evseModePowerSupplyTargetCurrent = 0
        self.evseModePowerSupplyMode = "init"
        self.EvsePhysicalVoltage = 1
        self.EvsePhysicalCurrent = 0
        self.evseModeSlacState = 0
        self.evseModeSlacStateValidityTimer = 0
        self.evseModePevMac = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

        self.logged_inlet_voltage = None
        self.logged_dc_link_voltage = None
        self.logged_cp_pwm = None
        self.logged_max_charge_a = None
        self.logged_soc_percent = None
        self.logged_contactor_confirmed = None
        self.logged_plugged_in = None

        self.rxbuffer = ""

        self.lastStatePublish = 0
        self.lastPowerReqPublish = 0
        self.initPorts()

    def resetSimulation(self):
        self.simulatedInletVoltage = 0.0 # volts
        self.simulatedSoc = 20.0 # percent
        self.demoAuthenticationCounter = 0

    def pevMode_simulatePreCharge(self):
        if (self.simulatedInletVoltage<230):
            self.simulatedInletVoltage = self.simulatedInletVoltage + 1.0 # simulate increasing voltage during PreCharge

    def evseMode_physicalVoltageSimulationMainfunction(self):
        # - in precharge state, increase the voltage.
        # - in current demand, keep the voltage (with random jitter).
        # - in welding detection state, ramp down the voltage.

        if (self.evseModePowerSupplyMode == "init"):
             self.EvsePhysicalCurrent = 0
             self.simulatedPhysicalVoltage = 2*random() # simulate a small offset in voltage measurement

        if (self.evseModePowerSupplyMode == "precharge"):
            self.batteryVoltageDuringPrecharge = self.evseModePowerSupplyTargetVoltage
            # simulating preCharge
            if (self.simulatedPhysicalVoltage<self.batteryVoltageDuringPrecharge/2):
                self.simulatedPhysicalVoltage = self.batteryVoltageDuringPrecharge/2
            if (self.simulatedPhysicalVoltage<self.batteryVoltageDuringPrecharge-30):
                self.simulatedPhysicalVoltage += 2
            if (self.simulatedPhysicalVoltage<self.batteryVoltageDuringPrecharge):
                self.simulatedPhysicalVoltage += 0.5
            self.EvsePhysicalCurrent = 0 # no current flow during precharge

        if (self.evseModePowerSupplyMode == "currentdemand"):
            # We have no hardware voltage measurement, and so we faked the precharge, and also keep
            # faking the EVSEPresentVoltage in the CurrentDemand loop.
            # The simulated charger provides the battery voltage which we have seen during
            # precharge. Not the voltage which is demanded by the car, because this may be much
            # higher. Discussion here: https://github.com/uhi22/pyPLC/issues/44
            # We add a small jitter to avoid frozen-looking value.
            self.simulatedPhysicalVoltage = self.batteryVoltageDuringPrecharge + 3*random()
            self.EvsePhysicalCurrent = self.getAccuMaxCurrent() # just say 10A

        if (self.evseModePowerSupplyMode == "weldingdetection"):

            # simulate the decreasing voltage during the weldingDetection:
            self.simulatedPhysicalVoltage = self.simulatedPhysicalVoltage*0.95 + 3*random()
            self.EvsePhysicalCurrent = 0 # no current flow during welding detection

        # finally transfer the float simulated voltage to an integer "official" voltage
        self.EvsePhysicalVoltage = int(self.simulatedPhysicalVoltage*10)/10 # e.g.345

    def resetCableCheck(self):
        self.cableChecker.resetCableCheck()

    def triggerCableCheck(self):
        self.cableChecker.triggerCableCheck()

    def isCableCheckFinished(self):
        return self.cableChecker.isCableCheckFinished()

    def isCableCheckOk(self):
        return self.cableChecker.isCableCheckOk()

    def close(self):
        if (self.isSerialInterfaceOk):
            self.ser.close()
    def close(self):
        if (self.isSerialInterfaceOk):
            self.ser.close()

    def showOnDisplay(self, s1, s2, s3):
        pass
        # show the given string s on the display which is connected to the serial port
        # this is just a stub, as there is no serial display on the RPi4 test rig

    def visualizeStatus(self, s, strSelection, strAux1, strAux2):
        pass
        # distribute the status info to the user
        # this is just a stub, and no Status Visualisation at present on Rpi4b rig (HWT)

    def mainfunction(self):         # hardwareInterface.mainfunction()
        if (getConfigValueBool("soc_simulation")):
            if(self.simulatedSoc<100):
                if ((self.outvalue & 0x10)!=0):    # getPowerRelayOn/Off
                    # while the relay is closed, simulate increasing SOC
                    deltaSoc = 0.01 # how fast the simulated SOC shall rise.
                    # Examples:
                    #  0.01 charging needs some minutes, good for light bulb tests
                    #  0.5 charging needs ~8s, good for automatic test case runs.
                    self.simulatedSoc = self.simulatedSoc + deltaSoc

        if (getConfigValue("charge_parameter_backend")=="chademo"):
           self.mainfunction_chademo()

        if (self.mode==C_EVSE_MODE):
            self.cableChecker.mainfunction()
            if (self.isPhysicalVoltageSimulated):
                self.evseMode_physicalVoltageSimulationMainfunction()

        if getConfigValueBool("exit_on_session_end"):
            # TODO: This is a hack. Do this in fsmPev instead and publish some
            # of these values into there if needed.
            if (self.plugged_in is not None and self.plugged_in == False and
                    self.inletVoltage < 50):
                sys.exit(0)

    def mainfunction_chademo(self):
        message = self.canbus.recv(0)    # non-blocking check for (any) CAN-bus message
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

            # now send charger parameters back to the car for validation 
            msg = can.Message(arbitration_id=0x108, data=[ 0, self.maxChargerVoltage & 0xFF, self.maxChargerVoltage >> 8, self.maxChargerCurrent, 0, 0, 0, 0], is_extended_id=False)
            self.canbus.send(msg)

            status = 4 if self.maxChargerVoltage > 0 else 0  #report connector locked
            msg = can.Message(arbitration_id=0x109, data=[ 10, self.chargerVoltage & 0xFF, self.chargerVoltage >> 8, self.chargerCurrent, 0, status, 0, 0], is_extended_id=False)
            self.canbus.send(msg)

        ############################################## HWT edit  ########################
        if message.arbitration_id == 0x102:
            new_value = (message.data[2]<<8 + message.data[1])
            if(  ##HWT edit here...
            vtg = (message.data[2] << 8) + message.data[1]
            if self.accuMaxVoltage != new_value:
                 self.addToTrace("CHAdeMO: Set target voltage to %d V" % new_value)
            self.accuMaxVoltage = new_value

            if self.accuMaxCurrent != message.data[3]:
                self.addToTrace("CHAdeMO: Set current request to %d A" % message.data[3])
            self.accuMaxCurrent = message.data[3]
            self.lastReceptionTime = time()

            if self.capacity > 0:
                soc = message.data[6] / self.capacity * 100
                if self.simulatedSoc != soc:
                    self.addToTrace("CHAdeMO: Set SoC to %d %%" % soc)
                self.simulatedSoc = soc

        #if nothing was received for over a second, time out
        if self.lastReceptionTime < (time() - 1):
            if self.accuMaxCurrent != 0:
                self.addToTrace("CHAdeMO: No current limit update for over 1s, setting current to 0")
            self.accuMaxCurrent = 0

pass    # end of class hardwareInterface

def myPrintfunction(s):
    print("myprint " + s)

if __name__ == "__main__":
    print("Testing hardwareInterface...")
    hw = hardwareInterface(myPrintfunction)
    for i in range(0, 350):
        hw.mainfunction()
        if (i==20):
            hw.setChargerParameters(500, 125)
            hw.setChargerVoltageAndCurrent(360, 100)
        if (i==50):
            hw.setStateC()
        if (i==100):
            hw.setStateB()
        if (i==150):
            hw.setStateC()
            hw.setPowerRelayOn()
        if (i==200):
            hw.setStateB()
            hw.setPowerRelayOff()
        if (i==250):
            hw.setRelay2On()
        if (i==300):
            hw.setRelay2Off()
        sleep(0.01)
    hw.close()
    print("finished.")
