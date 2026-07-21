# Worker for the pyPLC
#
# Tested on
#   - Windows10 with python 3.9 and
#   - Raspbian with python 3.9
#

#------------------------------------------------------------
#import pyPlcHomeplug
#import fsmEvse
#import fsmPev
from pyPlcModes import *
#import addressManager
import time
import subprocess
import hardwareInterface
#import connMgr


class pyPlcWorker():
    def __init__(self, callbackAddToTrace=None, callbackShowStatus=None, mode=C_EVSE_MODE, isSimulationMode=0, callbackSoC=None):
        print("initializing pyPlcWorker")
        self.nMainFunctionCalls=0
        self.mode = mode
        self.strUserAction = ""
        #self.addressManager = addressManager.addressManager()
        self.callbackAddToTrace = callbackAddToTrace
        self.callbackShowStatus = callbackShowStatus
        self.callbackSoC = callbackSoC
        self.oldAvlnStatus = 0
        self.isSimulationMode = isSimulationMode
        #self.connMgr = connMgr.connMgr(self.workerAddToTrace, self.showStatus)
        #self.hp = pyPlcHomeplug.pyPlcHomeplug(self.workerAddToTrace, self.showStatus, self.mode, self.addressManager, self.connMgr, self.isSimulationMode)
        self.hardwareInterface = hardwareInterface.hardwareInterface(self.workerAddToTrace, self.showStatus, self.hp)
        #self.hp.printToUdp("pyPlcWorker init")
        # Find out the version number, using git.
        # see https://stackoverflow.com/questions/14989858/get-the-current-git-hash-in-a-python-script
        try:
            strLabel = str(subprocess.check_output(["git", "describe", "--tags"], text=True).strip())
        except:
            strLabel = "(unknown version. 'git describe --tags' failed.)"
        self.workerAddToTrace("[pyPlcWorker] Software version " + strLabel)
        if (self.mode == C_PEV_MODE):
            self.pev = fsmPev.fsmPev(self.addressManager, self.connMgr, self.workerAddToTrace, self.hardwareInterface, self.showStatus)
    def __del__(self):
        if (self.mode == C_PEV_MODE):
            try:
                del(self.pev)
            except:
                pass

    def workerAddToTrace(self, s):
        # The central logging function. All logging messages from the different parts of the project
        # shall come here.
        #print("workerAddToTrace " + s)
        self.callbackAddToTrace(s) # give the message to the upper level, eg for console log.
        #self.hp.printToUdp(s) # give the message to the udp for remote logging.

    def showStatus(self, s, selection = "", strAuxInfo1="", strAuxInfo2=""):
        self.callbackShowStatus(s, selection)
        if (selection == "pevState"):
            self.hardwareInterface.showOnDisplay(s, strAuxInfo1, strAuxInfo2)
        try:
            self.hardwareInterface.visualizeStatus(s, selection, strAuxInfo1, strAuxInfo2)
        except:
            pass


    def mainfunction(self):
        self.nMainFunctionCalls+=1

        #  Set Watchdog output HIGH at start of main loop
        self.hardwareInterface.setWdog_On()

        if (self.mode == C_PEV_MODE):
            pass    # self.connMgr.mainfunction()

        self.hardwareInterface.mainfunction()   # call hardwareInterface to read CAN inputs, etc
 
        if (self.mode == C_PEV_MODE):
            self.pev.mainfunction()             # call the pev state machine

        # Set Watchdog output LOW at end of main loop
        self.hardwareInterface.setWdog_Off()

        # Timing on a Raspberry_Pi (4b) indicates 0.5mS to 1.5mS for this main loop
        # Sleep for 30mS to set PLC average scan-time. A Watchdog will be fired here sometime
        sleep(0.03)

    def handleUserAction(self, strAction):
        self.strUserAction = strAction
        print("user action " + strAction)
        if (strAction == "space"):
            print("stopping the charge process")
            if (hasattr(self, 'pev')):
                self.pev.stopCharging()

