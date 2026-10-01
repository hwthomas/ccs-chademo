#!/usr/bin/python3
#
# Worker for the pyPLC
#
# This is the 'worker' function called in a continuous loop as the PLC main
# task.  The calling function (see cdmNoGui.py) is the top-level program, and
# sets the approximate PLC scan time by a delay (time.sleep(30mS)) in the loop,
# checking on each scan for non-blocking user input for any specific commands.
# This allows for the user to stop the program, shutting down the charging safely,
# or, for debugging, single-step the finite state machine (fsmCdM) which 
# implements the CHAdeMO charging sequence, interfacing with the EV via module
# hardwareInterface which scans all CANbus signals and digital i/o. 
# Because of the continuous loop nature of the PLC, all code must be non-blocking,
# (python's 'asyncio' is not used at all), and each 'task' must complete in a
# time which is short compared to the overall scan time.  Tested on a RPi4b 
# indicates 0.5mS to 1.5mS for the worker main loop, which is 'short' compared to
# the average scan time set by the delay time (30mS)
#
# Tested on RPi4b using RPiOS with python 3.13     Sept 2026
#

import fsmCdM
from pyPlcModes import *
import time
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
        
        # set up the 'tasks' which are to be called on every PLC scan
        self.hardwareInterface = hardwareInterface.hardwareInterface(self.workerAddToTrace, self.showStatus, None)
        self.cdm = fsmCdM.fsmCdM(None, None, self.workerAddToTrace, self.hardwareInterface, self.showStatus)

    def __del__(self):
        try:
            del(self.cdm)
            del(self.hardwareInterface)
        except:
            pass

    def workerAddToTrace(self, s):
        # The central logging function. 
        # All logging messages from the different parts of the project come through here.
        #print("workerAddToTrace " + s)
        self.callbackAddToTrace(s) # give the message to the upper level, eg for console log.

    def showStatus(self, s, selection = "", strAuxInfo1="", strAuxInfo2=""):
        self.callbackShowStatus(s, selection)

    def mainfunction(self):                     # called by top-level loop on each PLC scan
        self.nMainFunctionCalls+=1              # increment PLC scan number
        self.hardwareInterface.setWdog_On()     # Set Watchdog output HIGH at start of main loop
        self.hardwareInterface.mainfunction()   # call hardwareInterface to read CAN inputs, etc
        self.cdm.mainfunction()                 # call the CHAdeMO state machine
        self.hardwareInterface.setWdog_Off()    # Set Watchdog output LOW at end of main loop

    def handleUserAction(self, strAction):      # strAction determined by non-blocking stdin
        self.strUserAction = strAction
        print("user action:  " + strAction)
        match (strAction):
            case 'q':                           # 'quit' by safe shutdown
                self.cdm.stopCharging()         # shut down safely via state machine
            case 'y':                           # confirm transition to next state
                self.cdm.stateNextConfirmed = True
            else:
                print("User input not recognised. Options are: 'q'(uit) or 'y'(es)")
                
pass    # end of class pyPlcWorker
                
