#!/usr/bin/python3
# The non-GUI variant of the PEV side with CHAdeMO interface only

import time
import pyPlcWorker
from pyPlcModes import *
import sys # for argv

startTime_ms = round(time.time()*1000)

def cbAddToTrace(s):
    currentTime_ms = round(time.time()*1000)
    dT_ms = currentTime_ms - startTime_ms
    print("[" + str(dT_ms) + "ms] " + s)

def cbShowStatus(s, selection=""):
    pass

myMode = C_PEV_MODE

isSimulationMode=0
if (len(sys.argv) > 1):
    if (sys.argv[1] == "S"):
        isSimulationMode=1

print("starting in PEV_MODE")
print("press Ctrl-C to exit")

# set worker function,linking to cbAddToTrace and cbShowStatus functions defined above
worker=pyPlcWorker.pyPlcWorker(cbAddToTrace, cbShowStatus, myMode, isSimulationMode)

nMainloops=0
while True:
    # time.sleep(.03)       # scan period is now set in pyPlcWorker main function
    nMainloops+=1           # track number of calls of worker.mainfunction
    worker.mainfunction()

#---------------------------------------------------------------
