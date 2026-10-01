#
# file fsmCdM.py:   State machine for the car CHAdeMO sequence
#
# The state machine can be in only one of its states at any time, so that on each
# call of its mainfunction only one stateFunction will be executed.
#

import time     # for time.sleep()

from helpers import prettyHexMessage, compactHexMessage, combineValueAndMultiplier
from configmodule import getConfigValue, getConfigValueBool

stateNotYetInitialized = 0
stateAssertSS1 = 1
stateAwaitingCANmessage = 2
stateExchangingChargingLimits = 3
stateCheckingCompatibility = 4
stateCableCheckRequest = 5
statePrechargeRequest = 6
stateEVready = 7
statePowerDelivery = 8
stateChargeFinished = 9
stateCANerror = 10
stateShuttingDown = 20
stateEnd = 50

class fsmCHdeMO():
    def addToTrace(self, s):
        self.callbackAddToTrace("[CHAdeMO] " + s)

    def publishStatus(self, s, strAuxInfo1="", strAuxInfo2=""):
        self.callbackShowStatus(s, "cdmState", strAuxInfo1, strAuxInfo2)

    def prettifyState(self, statenumber):
        s="unknownState"
        if (statenumber == stateNotYetInitialized):
            s = "NotYetInitialized"
        if (statenumber == stateAssertSS1):
            s = "Asserting d1/SS1 to EV"
        if (statenumber == stateAwaitingCANmessage):
            s = "Waiting for CAN messages"
        if (statenumber == stateExchangingChargingLimits):
            s = "Exchanging Charging Limits
        if (statenumber == stateCheckingCompatibility):
            s = "Checking EV and Charger compatibility"
        if (statenumber == stateCableCheckRequest):
            s = "Waiting for CableCheck Response"
        if (statenumber == statePrechargeRequest):
            s = "Waiting for Precharge Response"
        if (statenumber == stateEVready):
            s = "EV ready to charge"
        if (statenumber == statePowerDelivery):
            s = "Power Delivery Loop"
        if (statenumber = stateChargeFinished):
            s = "Charging Finished"
        if (statenumber == stateCANerror):
            s = "CAN Error"
        if (statenumber == stateShuttingDown):
            s = "Sequence ShutDown"
        if (statenumber == stateEnd):
            s = "End"
        return s

    def enterState(self, n):    # call to transition from stateCurrent to stateNext (n)
        self.stateNext = n      # set up next state to be entered
        # Check for fsm single-step enabled, and if so wait for confirmation via self.stateNextConfirmed
        if (self.fsm_single_step and self.stateNextConfirmed):
            self.addToTrace("from " + str(self.stateCurrent) + ":" + self.prettifyState(self.stateCurrent) + " entering " + str(n) + ":" + self.prettifyState(n))
            self.stateCurrent = n
            self.cyclesInState = 0
            self.stateNextConfirmed = False
        else:
            pass    # enter another scan with the current state unchanged

    def stateFunctionNotYetInitialized(self):
        if(self.cyclesInState = 1):         # print only on first call
            self.addToTrace("Waiting for 'n' command to move to next state, or 'q' to quit")
        if (self.cyclesInState<30):         # The first second in the state just do nothing.
            return
        self.enterState(stateAssertSS1)     # then move on to start CAN messages from EV

    def stateFunctionAssertSS1(self):
        if (self.cyclesInState<30): # The first second in the state just do nothing.
            return
        else:
            self.addToTrace("Assert d1/SS1 to start CAN bus in EV")
            self.isUserStopRequest = False
            self.enterState(stateAwaitingCANmessage)
            return

    def stateFunctionAwaitingCANmessage(self):
        # waiting for CAN driver to have a CAN message ready

    def stateFunctionExchangingChargingLimits(self):
        # We have received one (or more) CAN messages.  
        # Decode the message and evaluate the data values.
        # stay in this loop until the user decides to move on
        
    def stateFunctionCheckingCompatibility(self):
        # check charger and EV limits for compatibility

    def stateFunctionCANerror(self):
        # Here we end, if the CAN reports any errors.
        self.publishStatus("ERROR reported")
        # Initiate the safe-shutdown-sequence.
        self.addToTrace("Shutdown-sequence: setting CP state B")
        self.hardwareInterface.setStateB() # setting CP line to B disables the charger current flow.
        self.DelayCycles = 66 # 66*30ms=2s for charger shutdown
        self.enterState(stateShuttingDown)

    def stateFunctionShuttingDown(self):
        # wait state, to allow car to request zero current and remove charge permit
        if (self.DelayCycles>0):
            self.DelayCycles-=1
            return
        # Now the current flow is stopped by the charger. We can safely open the contactors:
        self.addToTrace("Safe-shutdown-sequence: opening contactors")
        self.hardwareInterface.setPowerRelayOff()
        self.hardwareInterface.setRelay2Off()
        self.DelayCycles = 33 # 33*30ms=1s for opening the contactors
        self.enterState(stateSafeShutDownWaitForContactorsOpen)

        self.addToTrace("Shutdown-sequence: remove CHAdeMO signal SS1")
        self.addToTrace("Shutdown-sequence: Set CCS Control Pilot (CP) to StateB")
        self.hardwareInterface.triggerConnectorUnlocking()
        # This is the end of the shutdown-sequence
        self.enterState(stateEnd)

    def stateFunctionEnd(self):
        # Just stay here, until program Quit
        pass

    stateFunctions = {
            stateNotYetInitialized: stateFunctionNotYetInitialized,
            stateAssertSS1: stateFunctionAssertSS1,
            stateAwaitingCANmessage: stateFunctionAwaitingCANmessage,
            stateExchangingChargingLimits: stateFunctionExchangingChargingLimits,
            stateCheckingCompatibility: stateFunctionCheckingCompatibility,
            stateCableCheckRequest: stateFunctionCableCheckRequest,
            statePrechargeRequest: stateFunctionPrechargeRequest,
            stateEVready: stateFunctionEVready,
            statePowerDelivery: stateFunctionPowerDelivery,
            stateChargeFinished: stateFunctionChargeFinished,
            stateCANerror: stateFunctionCANerror,
            stateShuttingDown: stateFunctionShuttingDown,
            stateEnd: stateFunctionEnd
        }

    def stopCharging(self):
        # API function to stop the charging.
        self.isUserStopRequest = True
        self.fsm_single_step = False
        self.enterState(stateShuttingDown)

    def reInit(self):
        self.addToTrace("re-initializing fsmCHdeMO")
        self.hardwareInterface.setStateB()
        self.hardwareInterface.setPowerRelayOff()
        self.hardwareInterface.setRelay2Off()
        self.isBulbOn = False
        self.cyclesLightBulbDelay = 0
        self.stateCurrent = stateNotYetInitialized
        self.cyclesInState = 0

    def __init__(self, callbackAddToTrace, hardwareInterface, callbackShowStatus):
        self.callbackAddToTrace = callbackAddToTrace
        self.callbackShowStatus = callbackShowStatus
        self.addToTrace("initializing fsmCHdeMO")
        self.exiLogFile = open('CdmExiLog.log', 'a')
        self.exiLogFile.write("Initialising CHAdeMO state machine log\n")
        self.hardwareInterface = hardwareInterface
        self.stateCurrent = stateNotYetInitialized  # current state 
        self.stateNext = None                       # next state to be entered
        self.stateNextConfirmed = False             # when single-stepping
        self.fsm_single_step = getConfigValueBool("fsm_single_step")
        self.cyclesInState = 0
        self.DelayCycles = 0
        self.isLightBulbDemo = getConfigValueBool("light_bulb_demo")
        self.isBulbOn = False
        self.cyclesLightBulbDelay = 0
        self.isUserStopRequest = False
        # we do NOT call reInit, because we want to wait with the connection until external trigger comes

    def __del__(self):
        self.exiLogFile.write("closing\n")
        self.exiLogFile.close()

    def mainfunction(self):
        # run the state machine: each program scan take 30mS (ish), set by pyPlcWorker loop
        self.cyclesInState += 1     # for first-call and timeout handling, count how long we are in a state
        self.stateFunctions[self.stateCurrent](self)   # call current stateFunction

pass    # end of class fsmCHdeMO

if __name__ == "__main__":
    print("Testing the CHAdeMO state machine")
    cdm = fsmCdM()       # create CHAdeMO state machine, and initialise to stateNotYetInitialised
    print("Press Ctrl-C to end loop")
    while (True):
        time.sleep(0.03)    # 30mS sets scan period for the State Machine test loop
        cdm.mainfunction()


