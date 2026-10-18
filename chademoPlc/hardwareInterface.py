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
       {"can_id": 0x102, "can_mask": 0x7FF, "extended": False} ]
    try:
        canbus = can.Bus(interface='socketcan', channel="can0", can_filters = filters)
    except OSError:
        print('Cannot find CAN board.')
        exit
        
    print("CAN-bus channel 'can0' opened successfully")
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

    # The next two functions are only called by the CAN-bus update in mainfunction_chademo, and by the test routine __main__ 
    # note that they depend on CAN variables being compared, so these are initialised (above) to valid values, and NOT 'None'
    def setChargerParameters(self, maxVoltage, maxCurrent):
        # when this function is called, construct CAN message 0x108 and send it (even if volts or current haven't changed)
        self.thresholdVoltage = int(min(self.maxBatteryVoltage, self.maxChargerVoltage))     # minimum of what EV 'needs' and what charger can supply
        th_lo = int(self.thresholdVoltage) & 0xFF
        th_hi = int(self.thresholdVoltage) >> 8
        if(self.cdmVersion >= 1):
            cdm = self.cdmVersion
            
        msg = can.Message(arbitration_id=0x108, data=[cdm, self.maxChargerVoltage & 0xFF, self.maxChargerVoltage >> 8, self.maxChargerCurrent, th_lo, th_hi, 0, 0], is_extended_id=False)
        self.canbus.send(msg)

        # if maxVoltage or maxCurrent has changed, log this to trace
        if(maxVoltage != self.maxChargerVoltage):
            self.addToTrace("Setting charger 'available Voltage = %d V" % maxVoltage)
            self.maxChargerVoltage = int(maxVoltage)
        if(maxCurrent != self.maxChargerCurrent):
            self.addToTrace("Setting charger 'available Current = %d A" % maxCurrent)
            self.maxChargerCurrent = int(maxCurrent)
 

    def setChargerVoltageAndCurrent(self, voltageNow, currentNow):
        # when this function is called, construct CAN message 0x109 and send it (even if volts or current haven't changed)
        status = 4    # always report connector locked (adapter has no lock at present)
        msg = can.Message(arbitration_id=0x109, data=[0, self.chargerVoltage & 0xFF, self.chargerVoltage >> 8, self.chargerCurrent, 0, status, 0, 0], is_extended_id=False)
        self.canbus.send(msg)

        # if voltageNow or currentNow has changed, log this to trace
        if(voltageNow != self.chargerVoltage):
            self.addToTrace("Setting charger 'actual' Voltage = %d V" % voltageNow)
            self.chargerVoltage = int(voltageNow)
        if(currentNow != self.chargerCurrent):
            self.addToTrace("Setting charger 'actual' Current = %d A" % currentNow)
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
            self.addToTrace("GPIO.pin_k evChargePermit = %X" % new_value)
            self.evChargePermit = new_value     # update via mainfunction scan only

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

    def initPorts(self):        # no ports required, and CAN-bus already set up
        self.canbus = canbus    # so just set up a class variable

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
        # NB: only use this class variable after class has been created
        if (getConfigValue("charge_parameter_backend")=="chademo"):
            self.chademo_backend = True
            self.canbus = canbus    # set up a class variable for canbus at the same time
        
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

        self.evChargePermit = None          # input of signal_k (active LOW) via GPIO
        self.canActive = False              # set True once CAN messages are seen

        # The following class variables are for comms to/from the CHAdeMO EV
        # some are initialised to valid values because they may be used before CAN has been updated
        self.cdmVersion = 1                 # CHAdeMO version code from EV (0=0.9, 1=1.0/1/2, 2=2.0)
 
        # EV tells the charger the maximum volts & amps it 'needs' via CAN-ID 0x100
        self.evSeqState100 = None           # CAN-ID 0x100 EV sends sequence state in byte 0
        self.minBatteryVoltage = None       
        self.maxBatteryVoltage = 0          # initialise to valid value
        self.socPercentFactor = 100

        self.maxChargeTimeMins = None       # CAN-ID 0x101
        self.estChargeTimeMins = None
        self.ratedCapacitykWh = None

        self.evSeqState102 = 0              # CAN-ID 0x102 EV sends sequence state in byte 0
        self.targetBatteryVoltage = 0       # then charging loop voltage and current requests
        self.chargeCurrentRequest = 0
        self.evFaultBits = None
        self.evStatusBits = 0
        self.evStateOfCharge = None

        self.lastReceptionTime = 0.0        # last time EV requested current from the charger

        # Charger tells the EV the maximum volts and amps available (ie that it can supply) via CAN-ID 0x108
        self.evseSeqState108                # CAN-ID 0x108 - charger sends sequence state in byte 0       
        self.maxChargerVoltage = 0          # then its Maximum Available values
        self.maxChargerCurrent = 0  
        self.thresholdVoltage = 0           # this is the maximum it will use (for protection of the EV)

        self.evseSeqState109                # CAN-ID 0x109 - charger sequence state in byte 0
        self.chargerVoltage = 0             # then sends 'actual' voltage and current being delivered in
        self.chargerCurrent = 0             # response to the EV 0x102 requests during the charging loop

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
        # GPIO and CAN-bus updates
        self.readEVchargePermit()       # poll EVchargePermit GPIO input (signal k) on each scan
        message = self.canbus.recv(0)   # non-blocking check for (any) CAN-bus message
        #
        # The following CAN_ID details are taken from the Nissan Leaf 2+ tables as specified
        # by https://github.com/dalathegreat/leaf_can_bus_messages/QC-CAN_ALL.dbc.  The interpreted
        # dbc files are expanded in https://github.com/hwthomas/ccs-chademo/doc/QC_CAN_messages
        # These dbc files were updated (June 2026) & all 16-bit values are now Intel format
        #
        if message:
            self.canActive = True       # something is happening on the EV CAN-bus
            # EV sends its sequence state (0x20) in ID 0x100 byte 0
            if message.arbitration_id == 0x100:
                new_value = message.data[0]
                if self.evSeqState100 != new_value:
                    self.addToTrace("0x100: evSeqenceState = %X " % new_value)
                    self.evSeqState100 = new_value

                new_value =  int(message.data[2]) + int(message.data[3])*256
                if(self.minBatteryVoltage != new_value):
                    self.addToTrace("0x100: minBatteryVoltage = %d V" % new_value)
                    self.minBatteryVoltage = new_value

                new_value = int(message.data[4]) + int(message.data[5])*256
                if(self.maxBatteryVoltage != new_value):
                    self.addToTrace("0x100 maxBatteryVoltage = %d V" % new_value)
                    self.maxBatteryVoltage = new_value

                new_value = message.data[6]
                if(self.socPercentFactor != new_value):
                    self.addToTrace("0x100 socPercentFactor = %d " % new_value)
                    self.socPercentFactor = new_value

                # set 'available' charger values and send to the EV via ID 0x108 for validation
                self.setChargerParameters(self.maxBatteryVoltage, self.maxChargerCurrent) 

            if message.arbitration_id == 0x102:
            # EV also sends its sequence state (0x26/0x29) (and CHAdeMO version) in ID 0x100 byte 0
                self.lastReceptionTime = time()     # record time of CAN volts and current requests for timeout check
                new_value = message.data[0]
                if(self.evSeqState102 != new_value):
                    self.addToTrace("0x102 evSequenceState102 = %X" % new_value)
                    self.evSeqState102 = new_value
                    
                new_value = int(message.data[1]) + int(message.data[2])*256
                if(self.targetBatteryVoltage != new_value):
                    self.addToTrace("0x102 targetBatteryVoltage = %d V" % new_value)
                    self.targetBatteryVoltage = new_value

                new_value = message.data[3]
                if(self.chargeCurrentRequest != new_value):
                    self.addToTrace("0x102 chargeCurrentRequest = %d A" % new_value)
                    self.chargeCurrentRequest = new_value

                new_value = message.data[4]
                if(self.evFaultBits != new_value):
                    self.addToTrace("0x102 evFaultBits = %X" % new_value)
                    self.evFaultBits = new_value

                new_value = message.data[5]
                if(self.evStatusBits != new_value):
                    self.addToTrace("0x102 evStatusBits = %X" % new_value)
                    self.evStatusBits = new_value

                if self.socPercentFactor > 0:       # (it is used in the next calculation)
                    new_value = message.data[6] / self.socPercentFactor * 100
                    if(self.evStateOfCharge != new_value):
                        self.addToTrace("0x102 evStateOfCharge = %d %%" % new_value)
                        self.evStateOfCharge = new_value

                #  in charging loop, send 'actual' charger values to EV via ID 0x109 to compare with EV request in ID 0x102
                self.setChargerVoltageAndCurrent(self.chargerVoltage, self.chargerCurrent)

            if message.arbitration_id == 0x101:
                new_value = message.data[2]
                if(self.maxChargeTimeMins != new_value):
                    self.addToTrace("0x101 maximum charge time = %d mins" % new_value)
                    self.maxChargeTimeMins = new_value

                new_value = message.data[3]
                if(self.estChargeTimeMins != new_value):
                    self.addToTrace("0x101 estimated charge time = %d mins" % new_value)
                    self.estChargeTimeMins = new_value
                    
                new_value = (int(message.data[5]) + int(message.data[6])*256) * 0.1
                if(self.ratedCapacitykWh != new_value):
                    self.addToTrace("0x101 ratedCapacity = %d kWh" % new_value)
                    self.ratedCapacitykWh = new_value

            if(message.arbitration_id == 0x108):    # we don't normally receive 0x108, only send via setChargerParameters
                new_value = message.data[0]
                if(self.evseSeqState108 != new_value):
                    self.addToTrace("ID 0x108: evseSequenceState = %X" % new_value)
                    self.evseSeqState108 = new_value
                     
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
                    self.addToTrace("ID 0x108: thresholdVoltage = %d V" % new_value)
                    self.thresholdVoltage = new_value

            if(message.arbitration_id == 0x109):    # we don't normally receive 0x109, only send via setChargerVoltageandCurrent
                new_value = message.data[0]
                if(self.evseSeqState109 != new_value):
                    self.addToTrace("ID 0x109: evseSequenceState = %X" % new_value)
                    self.evseSeqState109 = new_value
                    
                new_value = int(message.data[1]) + int(message.data[2])*256
                if(self.chargerVoltage != new_value):
                    self.addToTrace("ID 0x109: actual charger Voltage = %d V" % new_value)
                    self.chargerVoltage = new_value

                new_value = message.data[3]
                if(self.chargerCurrent != new_value):
                    self.addToTrace("ID 0x109: actual charger Current = %d A" % new_value)
                    self.chargerCurrent = new_value

        # if no CAN-ID 0x102 (chargeCurrentRequest) was received for over a second, time out and shut charging down
        if self.lastReceptionTime < (time() - 1):
            if self.accuMaxCurrent != 0:
                self.addToTrace("CHAdeMO: No current limit update for over 1s, setting current to 0")
            self.accuMaxCurrent = 0

pass    # end of class hardwareInterface


# This specific 'addToTrace' function used when hardwareInterface (test) class instance is created
startTime_ms = round(time()*1000)

def hwAddToTrace(s):
    currentTime_ms = round(time()*1000)
    dT_ms = currentTime_ms - startTime_ms
    print("[" + str(dT_ms) + "ms] " + s)

if __name__ == "__main__":
    # The test routine here is set up for different values to be used at different points of the test.
    # The test function 'simulateChargerResponse also allows simulated charge values to be fed back
    # to the EV to observe functional changes and timings as they occur. Once these have been observed
    # and understood (and documented!) a simpler test function can be used
    
    print("Testing hardwareInterface for ~25s...")
    # create instance of hardwareInterface
    hw = hardwareInterface(hwAddToTrace)

    volts_out = 0.0       # initialise simulated charger volts_out & amps_out (typical values)
    amps_out = 0.0
    
    def simulateChargerResponse():      # ONLY call this after the hw.mainfunction has updated all CAN values
        # this filters the EV Current and Voltage requests with a simple first-order filter, and sends the 
        # outputs back to the EV via CAN. Requests are read from CAN-ID 0x102, targetBatteryVoltage and
        # chargeCurrentRequest, and charger values outputVoltage and outputCurrent are reported back to the EV.
        # By calling hw.setChargerVoltageAndCurrent, CAN message 0x109 is sent, (even if values are the same)
        # simulate fast shutdown by setting output current immediately to zero if this is requested
        global volts_out, amps_out
        # process the volts & amps requests with a first-order filter
        volts_out = volts_out * 0.8 + hw.targetBatteryVoltage * 0.2
        if(hw.chargeCurrentRequest == 0):   # mre rapid shutdown (ish)
            amps_out = amps_out * 0.2 + hw.chargeCurrentRequest * 0.8
        else:
            amps_out = amps_out * 0.8 + hw.chargeCurrentRequest * 0.2
        # now update the EV with these filtered values (check whether this sends ID 0x109 twice?)
        hw.setChargerVoltageAndCurrent(int(volts_out), int(amps_out))
        
    hw.plugged_in = True            # charging session starts
    hw.setChargerParameters(500, 135)       # set up typical charger Max (available) volts and amps
                                            # these values are sent to EV via CAN message 0x108
    hw.setChargerVoltageAndCurrent(0, 0)    # set HV volts & amps to zero
                                            # these values are sent to EV via CAN message 0x109
    
    # the following loop is structured so that at various points parameters can be changed, and the EV response
    # monitored for timeouts, etc.  Initially, the loop is set to run for 805 mainfunction scans at ~30mS/scan
    # is just over 25secs  
    try:
        for i in range(0, 960):     # loop for ~30+ Sec at ~31mS per scan
            hw.mainfunction()       # poll hardware interface, updating CAN-bus variables to/from the EV on each scan
            if (i==5):              # after ~150mS...
                print("Start EV CAN-bus and inform charger of EV's Maximum Voltage and Current needs")
                hw.setSS1_On()      # activate charge signal d1/SS1 to start CAN comms and send
                                    # the EV's 'maximum' Voltage and Current requirements to the charger

            if (i==100):            # by now (~3s after SS1), EV should assert signal 'k' ChargePermit 
                print("Activate charge signal d2/SS2 to EV to enable HV contactors")
                hw.setSS2_On()      # EVSE should next assert d2/SS2 to enable EV contactors (when volts align)
                                    # EV requests EVSE to increase volts, with a maximum of 2A current (PreCharge step)

            if (i==300):            # EV requests voltage and current via CAN message 0x102 in charging loop
                hw.setChargerVoltageAndCurrent(0, 0)      # keep charger values at zero

            if (i == 330):
                print("simulatedChargerResponse activated")
            if (i >= 330):
                pass                 #simulateChargerResponse()   # invoke this if required

            if (i==600):            # set EV current demand to zero 
                print("Set test Charger Current request to zero")
                hw.setChargerVoltageAndCurrent(375, 0)
                
            if (i==750):            # set EV current demand to zero
                hw.setSS2_Off()     # EVSE disables d2/SS2 charge signal and EV contactors
            if (i==800):
                hw.setSS1_Off()     # EVSE disables d1/SS1 charge signal and CAN comms

            sleep(0.03)             # wait for approx. scan time. ie 30mS sleep + 1mS computation

    except KeyboardInterrupt:       # ctrl-C quits if all else fails!
            pass
    print("\nShutting down hardwareInterface safely...")
    hw.close()                      # close hardwareInterface cleanly (TODO: needs more work to be safe)
    print("hardwareInterface test finished.")
