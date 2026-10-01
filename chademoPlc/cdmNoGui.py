#!/usr/bin/python3
#
# cdmNoGui.py - the non-GUI variant of the PEV side with CHAdeMO interface only.
# Runs a main 'worker' loop, reacting on (minimal) non-blocking user k/b inputs
#

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

# set worker function,linking to cbAddToTrace & cbShowStatus functions defined above
worker=pyPlcWorker.pyPlcWorker(cbAddToTrace, cbShowStatus, myMode, isSimulationMode)

# reset number of calls (scans) of worker.mainfunction for overall program run.
# used to check 'time' in each state, entry/exit call of each stateFunctions, etc
nMainloops=0    

lastKey = ''    # monitors non-blocking user input from k/b
try:
    with raw(sys.stdin):        
        with nonblocking(sys.stdin):    # using non-blocking keyboard input...
            print("Single-key immediate commands: 'q' (quit), 'y' (yes to confirm next state)")
            while lastKey != 'q':               # worker.mainfunction loop until 'quit' command
                lastKey = sys.stdin.read(1)     # non-blocking read of k/b input
                if lastKey:
                    print(lastKey, flush=True)  # confirm command
                    worker.handleUserAction(lastKey)    # safe shutdown, etc handled in here

                time.sleep(.03)     # Sleep for 30mS to set PLC average scan-time
                nMainloops+=1       # track number of calls of worker.mainfunction
                worker.mainfunction()
            pass    # 'quit' exits mainfunction loop here
            print("Main loop ended. Cleaning up...")
            print("Number of PLC scans:- ", nMainloops)
            del(worker)             # remove worker function

    pass    # end of 'with' sections (raw, nonblocking)
    
except KeyboardInterrupt:           # ctrl-C quits immediately, so clean up
    worker.handleUserAction('q')    # handle shutdown safely even if Ctrl-C typed
    del(worker)                     # remove worker function
    print("Number of PLC scans:- ", nMainloops)
print( "Program terminated")

#-------------------------------------------------------------------------------

