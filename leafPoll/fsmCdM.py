#
# file fsmCdM.py:   State machine for the car CHAdeMO polling loop
#
#-----------------------------------------------------------------

import time # for time.sleep()
from helpers import prettyHexMessage, compactHexMessage, combineValueAndMultiplier

from configmodule import getConfigValue, getConfigValueBool

stateNotYetInitialized = 0
stateStartingCANbus = 1
stateCANreceived = 2
stateCANdecoding = 3
stateCANerror = 10
stateShutDown = 20
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
        if (statenumber == stateStartingCANbus):
            s = "Sarting CAN bus"
        if (statenumber == stateCANreceived):
            s = "CAN messages received"
        if (statenumber == stateCANdecoding ):
            s = "CANdecoding "
        if (statenumber == stateCANerror):
            s = "CAN Error"
        if (statenumber == stateShuttingDown):
            s = "ShutDown"
        if (statenumber == stateEnd):
            s = "End"
        return s

    def enterState(self, n):
        self.addToTrace("from " + str(self.state) + ":" + self.prettifyState(self.state) + " entering " + str(n) + ":" + self.prettifyState(n))
        self.state = n
        self.cyclesInState = 0

    def stateFunctionNotYetInitialized(self):
        pass # nothing to do, just wait for external event for re-initialization

    def stateFunctionStartCANbus(self):
        if (self.cyclesInState<30): # The first second in the state just do nothing.
            return
        evseIp = self.addressManager.getSeccIp() # the chargers IP address which was announced in SDP
        seccTcpPort = self.addressManager.getSeccTcpPort() # the chargers TCP port which was announced in SDP
        self.addToTrace("Checkpoint301: connecting")
        self.Tcp.connect(evseIp, seccTcpPort) # This is a blocking call. If we come back, we are connected, or not.
        if (not self.Tcp.isConnected):
            # Bad case: Connection did not work. May happen if we are too fast and the charger needs more
            # time until the socket is ready. Or the charger is defective. Or somebody pulled the plug.
            # No matter what is the reason, we just try again and again. What else would make sense?
            self.addToTrace("Connection failed. Will try again.")
            self.reInit() # stay in same state, reset the cyclesInState and try again
            return
        else:
            # Good case: We are connected. Change to the next state.
            self.addToTrace("connected")
            self.publishStatus("TCP connected")
            self.isUserStopRequest = False
            self.enterState(stateConnected)
            return

    def stateFunctionCANreceived(self):
        # CAN driver has a CAN message ready

    def stateFunctionCANdecoding(self):
        # We have received one (or more) CAN messages.  
        # Decode the message and evaluate the data values.
        # stay in this loop until the user decides to move on
        #self.hardwareInterface.resetSimulation()
        #self.enterState(stateWaitForSupportedApplicationProtocolResponse)

    def stateFunctionCANerror(self):
        # Here we end, if the CAN reports any errors.
        self.publishStatus("ERROR reported")
        # Initiate the safe-shutdown-sequence.
        self.addToTrace("Shutdown-sequence: setting CP state B")
        self.hardwareInterface.setStateB() # setting CP line to B disables the charger the current flow.
        self.DelayCycles = 66 # 66*30ms=2s for charger shutdown
        self.enterState(stateShutDown)


    def stateFunctionShuttingDown(self):
        # wait state, to allow car to stop CAN messages and set CCS StateC -> StateB
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
            stateStartCANbus: stateFunctionStartingCANbus,
            stateCANreceived: stateFunctionCANreceived,
            stateCANdecoding: stateFunctionCANdecoding,
            stateCANError: stateFunctionCANerror,
            stateShutDown: stateFunctionShutDown,
            stateEnd: stateFunctionEnd
        }

    def stopCharging(self):
        # API function to stop the charging.
        self.isUserStopRequest = True


    def reInit(self):
        self.addToTrace("re-initializing fsmPev")
        self.Tcp.disconnect()
        self.hardwareInterface.setStateB()
        self.hardwareInterface.setPowerRelayOff()
        self.hardwareInterface.setRelay2Off()
        self.isBulbOn = False
        self.cyclesLightBulbDelay = 0
        self.state = stateConnecting
        self.cyclesInState = 0
        self.rxData = []

    def __init__(self, addressManager, connMgr, callbackAddToTrace, hardwareInterface, callbackShowStatus):
        self.callbackAddToTrace = callbackAddToTrace
        self.callbackShowStatus = callbackShowStatus
        self.addToTrace("initializing fsmPev")
        self.exiLogFile = open('PevExiLog.txt', 'a')
        self.exiLogFile.write("init\n")
        self.Tcp = pyPlcTcpSocket.pyPlcTcpClientSocket(self.callbackAddToTrace)
        self.addressManager = addressManager
        self.connMgr = connMgr
        self.hardwareInterface = hardwareInterface
        self.state = stateNotYetInitialized
        self.sessionId = "DEAD55AADEAD55AA"
        self.evccid = addressManager.getLocalMacAsTwelfCharString()
        self.cyclesInState = 0
        self.DelayCycles = 0
        self.rxData = []
        self.isLightBulbDemo = getConfigValueBool("light_bulb_demo")
        self.isBulbOn = False
        self.cyclesLightBulbDelay = 0
        self.isUserStopRequest = False
        # we do NOT call the reInit, because we want to wait with the connection until external trigger comes

    def __del__(self):
        self.exiLogFile.write("closing\n")
        self.exiLogFile.close()

    def mainfunction(self):
        #self.Tcp.mainfunction() # call the lower-level worker
        if (self.Tcp.isRxDataAvailable()):
                self.rxData = self.Tcp.getRxData()
                #self.addToTrace("received " + prettyHexMessage(self.rxData))
        # run the state machine:
        self.cyclesInState += 1 # for timeout handling, count how long we are in a state
        self.stateFunctions[self.state](self)

# end of class fsmCHdMO

if __name__ == "__main__":
    print("Testing the CHdeMO state machine")
    cdm = fsmCHdMO()
    print("Press Ctrl-Break for aborting")
    while (True):
        time.sleep(0.1)
        cdm.mainfunction()


