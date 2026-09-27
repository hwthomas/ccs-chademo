# Worker for the pyPLC
#
# Tested on
#   - Raspbian with python 3.13     Sept 2026
#

import fsmCdM
from pyPlcModes import *
import time
import subprocess
import hardwareInterface



class pyPlcWorker():
    def __init__(self, callbackAddToTrace=None, callbackShowStatus=None, mode=C_PEV_MODE, isSimulationMode=0, callbackSoC=None):
        print("initializing pyPlcWorker")
        self.nMainFunctionCalls=0
        self.mode = mode
        self.strUserAction = ""
        self.callbackAddToTrace = callbackAddToTrace    # this logging function passed in from higher level
        self.callbackShowStatus = callbackShowStatus    # ditto for ShowStatus
        self.callbackSoC = callbackSoC
        self.oldAvlnStatus = 0
        self.isSimulationMode = isSimulationMode
        
        # set up the tasks which are to be called on every PLC scan
        self.hardwareInterface = hardwareInterface.hardwareInterface(self.workerAddToTrace, self.showStatus, None)
        self.cdm = fsmCdM.fsmCdM(None, None, self.workerAddToTrace, self.hardwareInterface, self.showStatus)

    def __del__(self):
        try:
            del(self.cdm)
        except:
            pass

    def workerAddToTrace(self, s):
        # The central logging function. 
        # All logging messages from the different parts of the project come through here.
        #print("workerAddToTrace " + s)
        self.callbackAddToTrace(s) # give the message to the upper level, eg for console log.

    def showStatus(self, s, selection = "", strAuxInfo1="", strAuxInfo2=""):
        self.callbackShowStatus(s, selection)

    def mainfunction(self):
        self.nMainFunctionCalls+=1              # increment PLC scan number
        # Timing on a Raspberry_Pi (4b) indicates 0.5mS to 1.5mS for this worker main loop
        self.hardwareInterface.setWdog_On()     # Set Watchdog output HIGH at start of main loop
        self.hardwareInterface.mainfunction()   # call hardwareInterface to read CAN inputs, etc
        self.cdm.mainfunction()                 # call the CHAdeMO state machine
        self.hardwareInterface.setWdog_Off()    # Set Watchdog output LOW at end of main loop

    def handleUserAction(self, strAction):      # UserAction determined by non-blocking stdin cmd
        self.strUserAction = strAction
        print("user action " + strAction)
        if (strAction == "space"):
            print("stopping the charge process")
            if (hasattr(self, 'pev')):
                self.cdm.stopCharging()
                
pass    # end of class pyPlcWorker
                

