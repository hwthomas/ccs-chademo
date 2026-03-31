#
# simple test for all GPIO outputs used on CCS-to-CHAdeMO adapter
#  
# define classes to implement raw or non-blocking keyboard reads 
# see ref: https://ballingt.com/nonblocking-stdin-in-python-3/

import sys, os
import fcntl
import tty
import termios

import RPi.GPIO as GPIO
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

# define a class to hold all parameters for a single GPIO output
class output(object):
	def __init__(self, name, pinNo, state):
		self.name = name		# eg "d1/SS1"
		self.pinNo = pinNo		# pinNo in GPIO.BOARD format
		self.state = state		# 0/1 ie false/true 
	def show(self):
		# show output in form "d1/SS1 (29) {0/1}"	(on same line)
		print(self.name, "(", self.pinNo, ") {", self.state, "}", sep='',flush=True)
	def setGPIO(self, state):
		self.state = state
		print("GPIO ", self.pinNo, " set to ", self.state, sep='', flush=True)
		GPIO.output(self.pinNo, self.state)  #    set actual GPIO.output


GPIO.setmode(GPIO.BOARD)				# set GPIO for board (physical pin) numbering

# define a list of all GPIO outputs to be tested. Note:- GND & Output are opposite way round for 40/39
outputs = []
outputs.append(output("d1/SS1", 29, 0))	# pin 29 (GPIO 05); pin 30 GND:	# d1/SS1 - Charge sequence signal 1
outputs.append(output("d2/SS2", 13, 0))	# pin 13 (GPIO 27); pin 14 GND: # d2/SS2 - Charge sequence signal 2
outputs.append(output("CCS.CP", 40, 0))	# pin 40 (GPIO 21); pin 39 GND: # CP - CCS ControlPilot line
outputs.append(output("RPi.Wdog", 33, 0))	# pin 33 (GPIO 13); pin 34 GND: # RPi Watchdog charge pump (future)

for output in outputs:		# process all the outputs defined above
	GPIO.setup(output.pinNo, GPIO.OUT)	# set up each of the GPIO pins as outputs
	output.setGPIO(0)					# also output.setGPIO(0) in output class
#
# Test rig operates as follows:-
# A message is printed, followed by the outputs to be tested (name, pinNo, and current state {0/1}
# A command prompt ('>') is then printed on a new line (eg "d2/SS2, pin 13, {0}", "\n >"). 
# Single-character keyboard inputs can then be accepted :-
# 0		turn output off
# 1     turn output on
# n		next output selection
# p     previous output selection
# q		quit
# 
# If the output changes state, a new prompt (and new value) are printed.
# All outputs are set to zero when the program quits, but outputs may be left
# on (or off) when moving to the next or previous output. The keyboard input
# is non-blocking, so a <cr> is not required after each command.
#

try:
	print("GPIO tester")
	print("Outputs to be tested are:- ")
	for output in outputs:
		output.show()
		
	print("Enter a command in set {s, n, p, 0, 1, q} \n>", sep='', end='')
	index = 0
	output = outputs[index]					# select initial output
	last = len(outputs) - 1					# define last index
	with raw(sys.stdin):		
		with nonblocking(sys.stdin):
			while True:						# command input/GPIO output loop
				c = sys.stdin.read(1)		# non-blocking check of input
				if c:
					print(c, flush=True)	# confirm command
					match c:
						case 's':				# show current selection
							pass	#output.show()
						case 'n':				# next output selection
							if(index < last):
								index += 1
							else:
								index = 0		# loop back to start
						case 'p':				# previous output selection
							if(index > 0):
								index -= 1
							else:
								index = last	# loop back to last
						case '0':
							output.setGPIO(0)
						case '1':
							output.setGPIO(1)
						case 'q':			# quit
							print("Ending test...")
							raise KeyboardInterrupt
						case _:
							print("Unknown command")
					output = outputs[index]		# select output from list
					output.show()				# display current output
					print('>', end='', flush=True)	# and command prompt
				else:
					time.sleep(0.1)		# no input - sleep 100mS

except KeyboardInterrupt:	# ctrl-C quits if all else fails!
	print("setting outputs to 0" )
for output in outputs:
	output.setGPIO(0)
GPIO.cleanup()
print( "Program terminated")

