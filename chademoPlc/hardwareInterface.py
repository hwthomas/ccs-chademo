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

if (getConfigValue("digital_output_device") == "rpi_gpio"):
    import RPi.GPIO as GPIO   # Raspberry Pi GPIO library

    # RPI4b GPIO output definitions for interface board (https://github.com/hwthomas/ccs-chademo/wiki/)
    pinCp  = 40     # alter these for our interface boards
    pinSS1 = 13     # d1/SS1 Charge sequence signal 1
    pinSS2 = 29     # d2/SS2 Charge sequence signal 2
    pinWdg = 33     # pinWdg WatchDog charge pump (future)

    # GPIO input definitions
    pin_k = 10      # used for evChargePermit (signal k)

    GPIO.setmode(GPIO.BOARD)                    # set GPIO for board (physical pin) numbering
    outputs = [pinCp, pinSS1, pinSS2, pinWdg]
    for pin in outputs:                         # process all the outputs defined above
        GPIO.setup(pin, GPIO.OUT)               # set up each of the GPIO pins as outputs
        GPIO.output(pin, GPIO.LOW)              # also set each output LOW at start
    inputs = [pin_k]
    for pin in inputs:
        GPIO.setup(pin, GPIO.IN)

# As we use the CHAdeMO backend, we need to use CAN - (pip3 install python-can)  
if (getConfigValue("charge_parameter_backend")=="chademo"):
    import can
    print('Bringing up CAN (channel can0) at 500kbps...')
    os.system("sudo /sbin/ip link set can0 down")    # Prevent 'Busy' error if already UP
    os.system("sudo /sbin/ip link set can0 up type can bitrate 500000")

    filters = [
       {"can_id": 0x100, "can_mask": 0x7FF, "extended": False},
       {"can_id": 0x101, "can_mask": 0x7FF, "extended": False},
       {"can_id": 0x102, "can_mask": 0x7FF, "extended": False}]
    try:
        canbus = can.Bus(interface='socketcan', channel="can0", can_filters = filters)
    except OSError:
        print('Cannot find CAN board.')
        exit
    # Allow some time for CAN to start up
    sleep(1.0)

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
#----------------------------------------------------------------
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

#-----------------------------------------------------------------
#
# These are the CHAdeMO sequence signals, which need to
#  be activated in the fsmCdM code at appropriate points
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

# Where is this relay confirmation required in CHAdeMO?  - [fsmPev.py line 603]
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
        self.addToTrace("Setting charger *available* maxVoltage=%d V, maxCurrent=%d A" % (maxVoltage, maxCurrent))
        self.maxChargerVoltage = int(maxVoltage)
        self.maxChargerCurrent = int(maxCurrent)
        # send updated charger values immediately to the EV via ID-0x108
        msg = can.Message(arbitration_id=0x108, data=[0, self.maxChargerVoltage & 0xFF, self.maxChargerVoltage >> 8, self.maxChargerCurrent, 0, 0, 0, 0], is_extended_id=False)
        self.canbus.send(msg)


    def setChargerVoltageAndCurrent(self, voltageNow, currentNow):
        self.addToTrace("Setting charger *actual* values Voltage=%d V, Current=%d A" % (voltageNow, currentNow))
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
        self.inletVoltage = self.simulatedInletVoltage
        return self.inletVoltage

    def getEvsePhysicalVoltage(self):
        return self.EvsePhysicalVoltage

    def getEvsePhysicalCurrent(self):
        return self.EvsePhysicalCurrent

    def getAccuVoltage(self):
        if self.chademo_backend:
            return self.accuVoltage
        #todo: get real measured voltage from the accu. (via OBDII dongle?)
        self.accuVoltage = 230
        return self.accuVoltage

    def getAccuMaxCurrent(self):
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
        if self.chademo_backend:
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

    def readEVchargePermit(self):               # read GPIO input when called
        new_value = not GPIO.input(pin_k)       # pin_k is active(LOW)
        if(new_value != self.evChargePermit):
            self.addToTrace("CHAdeMO: EVchargePermit = %X" % new_value)
            self.evChargePermit = new_value     # update via mainfunction only

    def getEVchargePermit(self):                # return EVchargePermit
        return self.evChargePermit              # public API for external users

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
        self.canbus = canbus    # just set up class variable for can0

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

        # ditto for the CHAdeMO backend, which is checked many times on each scan
        # NB: only use this class variable short-form after class has been created
        if (getConfigValue("charge_parameter_backend")=="chademo"):
            self.chademo_backend = True
        
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

        self.evChargePermit = 0             # input of signal_k (LOW) via GPIO

        # The following class variables are for testing the CHAdeMO hardware

        # EV tells charger what it *needs* via CAN-ID 0x100
        self.minChargeCurrent = None        # CAN-ID 0x100
        self.minBatteryVoltage = None
        self.maxBatteryVoltage = None
        self.chargeRateIndication = None

        self.maxChargeTimeMins = None       # CAN-ID 0x101
        self.estChargeTimeMins = None
        self.ratedCapacitykWh = None

        self.targetBatteryVoltage = None    # CAN-ID 0x102 EV requests during charge phase
        self.chargeCurrentRequest = None
        self.evFaultBits = None
        self.evStatusBits = None
        self.evStateOfCharge = None

        self.lastReceptionTime = 0.0        # records CAN volts & amps requests from EV

        # Charger tells EV the maximum it can supply via CAN-ID 0x108
        self.maxChargerVoltage = None       # CAN-ID 0x108 charger sends maxAvailable
        self.maxChargerCurrent = None

        self.chargerVoltage = None          # CAN-ID 0x109 charger sends actual to EV
        self.chargerCurrent = None


        # end of CHAdeMO current variables

        self.simulatedSoc = 20.0    # percent
        self.demoAuthenticationCounter = 0
        self.enabled = True         # Charging enabled
        self.buttonDebounceCounter = 0
        self.buttonStopPhaseCounter = 0

        self.inletVoltage = 0.0     # volts ring-buffer
        self.accuVoltage = 0.0
        self.lock_confirmed = False # Confirmation from hardware
        self.cp_pwm = 0.0
        self.soc_percent = 0.0
        self.capacity = 0.0
        self.accuMaxVoltage = 0.0
        self.accuMaxCurrent = 0.0
        self.contactor_confirmed = False    # Confirmation from hardware
        self.plugged_in = None              # None means "not known yet"

        self.infonumber = 0     # the following are new, and only for Charger project?
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
        self.initPorts()                # set up CAN driver class variable 

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

    def close(self):            # close hardwareInterface cleanly
        if(getConfigValue("digital_output_device") == "rpi_gpio"):
            GPIO.cleanup()
        if self.chademo_backend:
            self.canbus.shutdown()  # shut CAN-bus down cleanly  

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

        if self.chademo_backend:
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
        self.readEVchargePermit()       # poll EVchargePermit input (signal k) on each scan
        message = self.canbus.recv(0)   # non-blocking check for (any) CAN-bus message
        #
        # The following CAN_ID details are taken from the Nissan Leaf 2+ tables as specified
        # by https://github.com/dalathegreat/leaf_can_bus_messages/QC-CAN_ALL.dbc.  The interpreted
        # dbc files are expanded in https://github.com/hwthomas/ccs-chademo/doc/QC_CAN_messages
        # These dbc files were updated (June 2026) & all 16-bit values are now Intel format
        #
        if message:
            # EV sends maximum volts needed from the charger in ID 0x100
            if message.arbitration_id == 0x100:
                new_value = message.data[0]
                if self.minChargeCurrent != new_value:
                    self.addToTrace("CHAdeMO: minChargeCurrent = %d Amps" % new_value)
                    self.minChargeCurrent = new_value

                new_value =  int(message.data[2]) + int(message.data[3])*256
                if(self.minBatteryVoltage != new_value):
                    self.addToTrace("CHAdeMO: minBatteryVoltage = %d V" % new_value)
                    self.minBatteryVoltage = new_value

                new_value = int(message.data[4]) + int(message.data[5])*256
                if(self.maxBatteryVoltage != new_value):
                    self.addToTrace("CHAdeMO: maxBatteryVoltage = %d V" % new_value)
                    self.maxBatteryVoltage = new_value

                # send 'available' charger values immediately to the EV via ID-0x108 for validation 
                msg = can.Message(arbitration_id=0x108, data=[0, self.maxChargerVoltage & 0xFF, self.maxChargerVoltage >> 8, self.maxChargerCurrent, 0, 0, 0, 0], is_extended_id=False)
                self.canbus.send(msg)

            if message.arbitration_id == 0x102:
                self.lastReceptionTime = time()     # record CAN volts and current requests
                new_value = int(message.data[1]) + int(message.data[2])*256
                if(self.targetBatteryVoltage != new_value):
                    self.addToTrace("CHAdeMO: targetBatteryVoltage = %d V" % new_value)
                    self.targetBatteryVoltage = new_value

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
                if(self.evStateOfCharge != new_value):
                    self.addToTrace("CHAdeMO: evStateOfCharge = %d" % new_value)
                    self.evStateOfCharge = new_value

                #  in charging loop, send 'actual' charger values to EV via ID 0x109 to compare with requested values from ID 0x102
                status = 4          # also in ID 0x109 'always' report connector locked (adapter has no lock at present)
                msg = can.Message(arbitration_id=0x109, data=[0, self.chargerVoltage & 0xFF, self.chargerVoltage >> 8, self.chargerCurrent, 0, status, 0, 0], is_extended_id=False)
                self.canbus.send(msg)
                
            if message.arbitration_id == 0x101:
                new_value = int(message.data[5]) + int(message.data[6])*256
                if(self.ratedCapacitykWh != new_value):
                    self.addToTrace("CHAdeMO: ratedCapacity = %d kWh" % new_value)
                    self.ratedCapacitykWh = new_value

        # if no CAN-ID 0x102 (chargeCurrentRequest) was received for over a second, time out and shut charging down
        if self.lastReceptionTime < (time() - 1):
            if self.accuMaxCurrent != 0:
                self.addToTrace("CHAdeMO: No current limit update for over 1s, setting current to 0")
            self.accuMaxCurrent = 0

pass    # end of class hardwareInterface

def myPrintfunction(s):
    print("myprint " + s)

if __name__ == "__main__":
    print("Testing hardwareInterface for ~30s...")
    # create instance of hardwareInterface
    hw = hardwareInterface(myPrintfunction)
    hw.plugged_in = True        # charging session starts
    hw.setChargerParameters(500, 135)   # set typical EVSE Max (available) volts and amps

    try:
        # loop 1000 times to give ~30s at ~30mS per scan, and start scanning hardwareInterface.mainfunction each time
        for i in range(0, 1000):
            hw.mainfunction()       # poll hardware interface, updating CAN-bus variables to/from the EV
            if (i==33):             # after ~1s...
                print("Start EV CAN-bus and inform charger of Maximum Voltage and Current needs")
                hw.setChargerVoltageAndCurrent(0, 0)      # set HV volts & amps to zero to start
                print("Activate charge signal d1/SS1 to EV to start CAN-bus comms")
                hw.setSS1_On()      # activate charge signal d1/SS1 to start CAN comms and send
                hw.setChargerParameters(500, 135)   # set typical EVSE Max (available) volts and amps
                                    # the EV's maximum Voltage and Current requirements to the charger
            if (i==99):             # by now (2s after SS1), EV should assert signal 'k' ChargePermit 
                hw.setSS2_On()      # EVSE should next assert d2/SS2 to enable EV contactors (when volts align)
                print("Activate charge signal d2/SS2 to EV to enable HV contactors")
                                    # EV requests EVSE to increase volts, with a maximum of 2A current (PreCharge step)
            if (i==200):            # EV requests voltage and current via CAN message 0x102
                print("Set test Charger Voltage and Current values to send back to EV")
                hw.setChargerVoltageAndCurrent(370, 2)      # set typical HV volts for 60% SOC (40% - 70%)
                                    # these values are sent hence back to EV via CAN message 0x109
            if (i==500):            # 
                pass
            if (i==700):            # set EV current demand to zero
                print("Set test Charger Current request to zero")
                hw.setChargerVoltageAndCurrent(375, 0)
            if (i==800):            # set EV current demand to zero
                hw.setChargerVoltageAndCurrent(375, 0)
                hw.setSS2_Off()     # EVSE disables d2/SS2 charge signal and EV contactors
            if (i==900):
                hw.setSS1_Off()     # EVSE disables d1/SS1 charge signal and CAN comms
            sleep(0.03)             # wait for approx. scan time

    except KeyboardInterrupt:       # ctrl-C quits if all else fails!
            pass
    print("\nShutting down hardwareInterface safely...")
    hw.close()                      # close hardwareInterface cleanly (TODO: needs more work to be safe)
    print("hardwareInterface test finished.")
