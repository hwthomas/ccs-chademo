#  
# define classes to implement raw or non-blocking keyboard reads 
# see ref: https://ballingt.com/nonblocking-stdin-in-python-3/

import sys, os
import fcntl
import tty
import termios
import time

class raw(object):
    def __init__(self,stream):
        self.stream = stream
        self.fd = self.stream.fileno()
    def __enter__(self):
        self.original_stty = termios.tcgetattr(self.stream)
        tty.setcbreak(self.stream)
    def __exit__(self, type, value, traceback):
        termios.tcsetattr(self.stream, termios.TCSANOW, self.original_stty)

class nonblocking(object):
    def __init__(self, stream):
        self.stream = stream
        self.fd = self.stream.fileno()
    def __enter__(self):
        self.orig_fl = fcntl.fcntl(self.fd, fcntl.F_GETFL)
        fcntl.fcntl(self.fd, fcntl.F_SETFL, self.orig_fl | os.O_NONBLOCK)
    def __exit__(self, *args):
        fcntl.fcntl(self.fd, fcntl.F_SETFL, self.orig_fl)
        

if __name__ == "__main__":
    try:
        print("Testing non-blocking stdin for input...\n")
    
        print("Enter a command in set {s(how), n(ext), p(revious), 0(->0), 1(->1), q(uit)} \n>", sep='', end='')
        index = 0
        with raw(sys.stdin):        
            with nonblocking(sys.stdin):
                while True:                         # command input/GPIO output loop
                    c = sys.stdin.read(1)           # non-blocking check of input
                    if c:
                        print(c, flush=True)        # confirm command
                        match c:
                            case 's':               # show current selection
                                print("Command selected = ", c, "(how)", sep='' )
                            case 'n':               # next output selection
                                print("Command selected = ", c, "(ext)", sep='' )
                            case 'p':               # previous output selection
                                print("Command selected = ", c, "(revious)", sep='' )
                            case '0':
                                print("Command selected = ", c, "(->0)", sep='' )
                            case '1':
                                print("Command selected = ", c, "(->1)", sep='' )
                            case 'q':               # quit
                                print("Command selected = ", c, "(uit)", sep='' )
                                print("Ending test...")
                                raise KeyboardInterrupt
                            case _:
                                print("Unknown command")
                        print('>', end='', flush=True)    # and command prompt
                    else:
                        time.sleep(0.1)             # no input - sleep 100mS

    except KeyboardInterrupt:    # ctrl-C quits if all else fails!
        print( "Program terminated")

