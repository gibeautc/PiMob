#!/usr/bin/env python
from appJar import gui
import os
import sys
if os.path.isdir("/home/pi"):
	system="pi"
else:
	system="chadg"

toGuiPath="/home/"+system+"/pipeToGui"
fromGuiPath="/home/"+system+"/pipeFromGui"
#if not os.path.isfile(toGuiPath):
try:	
	os.mkfifo(toGuiPath)
except:
	pass
#if not os.path.isfile(fromGuiPath):
try:
	os.mkfifo(fromGuiPath)
except:
	pass
pipeIn=os.open(toGuiPath,os.O_RDONLY|os.O_NONBLOCK)
pipeOut=os.open(fromGuiPath,os.O_RDWR)

msgBuffer=[]

#need to clear buffer

#while True:
#	try:
#		print("Clearing")
#		c=os.read(pipeIn,1)
#		print(c)
#	except:
#		break

tools=["GPS","CLOSE","OFF"]

def tbFunc(button):
	print("ToolBar Button "+str(button)+" was pressed")

def checkUpdate():
	global msgBuffer
	msg=""
	#print("Checking for updates")
	try:
		line=os.read(pipeIn,10)
		#print(line)
		msgBuffer.append(line)
		#print(msgBuffer)
		total="".join(msgBuffer)
		lines=total.split("\n")
		if len(lines)<2:
			return
		for x in range(len(lines)-1):
			print("Message: "+lines[x])
			msg=lines[x]
		msgBuffer=[]
		msgBuffer.append(lines[len(lines)-1])
		#print("Here")	
		
	except:
		#print(sys.exc_info())
		#print("Error reading from pipe, maybe empty")
		return
	#print(line)
	if "GPS:" in msg:
		msg=msg.split(":")
		if msg[1]=="1":
			app.setStatusbarBg("green",3)
		if msg[1]=="0":
			app.setStatusbarBg("red",3)
	if "TOTAL:" in msg:
		msg=msg.split(":")
		app.setLabel("totalWifi","Total Number of AP's: "+msg[1])
		
	if "DAY:" in msg:
		msg=msg.split(":")
		app.setLabel("dailyWifi","AP's Added today: "+msg[1])

app=gui()

#Tool BAR setup
app.addToolbar(tools,tbFunc,findIcon=True)

#Status Bar Setup
app.addStatusbar(fields=4)
app.setStatusbarWidth(4,3)
app.setStatusbarBg("red",3)
app.setStatusbar("GPS",3)

#Lables
app.addLabel("title","PiMobile")
app.addLabel("totalWifi","Total Number of AP's:")
app.addLabel("dailyWifi","AP's Added today:")


#Registered Events
app.registerEvent(checkUpdate)
app.go()

