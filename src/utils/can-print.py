#!/usr/bin/python3
#
# This is simple CAN receive-then-transmit python program loop. 
# All messages received are printed out on screen.
# For use with Waveshare RS485/CAN boards on the Raspberry Pi
#
# Make sure Python-CAN is installed first - pip3 install python-can
# then 'import can'  as listed below

import can
import time
import os

count = 0
can_id = ""

print('\n\rCAN Rx...Tx test')
print('Bring up CAN0....')
os.system("sudo /sbin/ip link set can0 up type can bitrate 500000")
time.sleep(0.1)	

try:
	bus = can.interface.Bus(channel='can0', bustype='socketcan')
except OSError:
	print('Cannot find CAN board.')
	exit()
	
print('Ready')

try:
	while True:
		message = bus.recv()	# Wait until a message is received.
		
		c = '{0:f} {1:x} {2:x} '.format(message.timestamp, message.arbitration_id, message.dlc)
		
		can_id = message.arbitration_id
		count = message.dlc

		s=' ... '
		for i in range(message.dlc ):
			s +=  '{0:x} '.format(message.data[i])
			
		print(' {}'.format(c+s))
		
		# pause 10mS, then loop for next message or until Ctrl-C
		time.sleep(0.010) 
		count = 8
		msg = can.Message(can_id,data=[0x00,0x01,0x02, 0x03, 0x04, 0x05,0x06, count & 0xff])
		# bus.send(msg)
	
except KeyboardInterrupt:
	# Catch keyboard interrupt
	print('\n\rKeyboard interrupt')	


print('\n\rShutting bus and CAN0 down')	
bus.shutdown()
os.system("sudo /sbin/ip link set can0 down")
