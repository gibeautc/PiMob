#!/usr/bin/env python

import os
import time



inPipe=os.open("/home/chadg/pipeFromGui",os.O_RDWR)
outPipe=os.open("/home/chadg/pipeToGui",os.O_RDWR)

cnt=0

while True:
	os.write(outPipe,"GPS:1\n")
	time.sleep(5)	
	os.write(outPipe,"GPS:0\n")
	time.sleep(5)
