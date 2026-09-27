#!/usr/bin/python3
#
# The non-GUI variant of the PEV side with CHAdeMO interface only
# Runs a main loop, reacting on (minimal) non-blocking user key inputs

import sys
import time
import pyPlcWorker
from pyPlcModes import *
import sys # for argv
from nonblockstdin import raw, nonblocking      # for non-blocking user input

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

print("Starting CHAdeMO sequence tester")
print("press Ctrl-C to exit in all cases")

# set worker function,linking to cbAddToTrace and cbShowStatus functions defined above
worker=pyPlcWorker.pyPlcWorker(cbAddToTrace, cbShowStatus, myMode, isSimulationMode)

nMainloops=0
lastKey = ''
try:
    with raw(sys.stdin):        
        with nonblocking(sys.stdin):    # using non-blocking keyboard input...

            while lastKey != 'q':               # worker.mainfunction loop until...
                lastKey = sys.stdin.read(1)     # non-blocking check of input
                if lastKey:
                    print(lastKey, flush=True)  # confirm command
                    match lastKey:
                        case 'q':               # quit program (next time)
                            pass                # no action this time 
                        case 'n':               # single-step mode: next (state)

                time.sleep(.03)     # Sleep for 30mS to set PLC average scan-time
                nMainloops+=1       # track number of calls of worker.mainfunction
                worker.mainfunction()

    pass    # end of 'with' sections
    
except KeyboardInterrupt:           # ctrl-C quits immediately
    print("setting outputs to 0" )
    del(worker)                     # remove worker function
    print( "Program terminated")

#---------------------------------------------------------------
