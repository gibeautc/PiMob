#!/usr/bin/env python
import subprocess
import socket
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
#this only works if there is somthing, not if its empty
#while True:
#	try:
#		print("Clearing")
#		c=os.read(pipeIn,1)
#		print(c)
#	except:
#		break

tools=["UPDATE","CLOSE","OFF"]

def tbFunc(button):
	print("ToolBar Button "+str(button)+" was pressed")
	if button=="CLOSE":
		exit()
	if button=='GPS':
		app.showSubWindow("gpsWindow")
	if button=="OFF":
		shutdown=app.yesNoBox("Shutdown","Do you really want to shut down the system?",parent=None)
		if shutdown:
			#should probably shutdown other processes?
			#will need to include a way for them to know they should shutdown
			#so that MySQL connections and other stuff is closed?
			subprocess.call("shutdown -H now",shell=True)
		return 
	if button=="UPDATE":
		app.thread(gitPull)
		

def haveInternet(host="8.8.8.8", port=53, timeout=3):
	"""
	Host: 8.8.8.8 (google-public-dns-a.google.com)
	OpenPort: 53/tcp
	Service: domain (DNS/TCP)
	"""
	try:
		socket.setdefaulttimeout(timeout)
		socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
		return True
	except Exception as ex:
		print ex.message
		return False

def gitPull():
	#running in another thread, careful!
	if haveInternet():
		#do git pull, check for changed, restart processes as needed
		print("Going to update from git")
		git=subprocess.Popen(['git','pull','origin','master'],stdout=subprocess.PIPE)
		(output,err)=git.communicate()
		exit_code=git.wait()
		if "Already up-to-date" in output:
			app.queueFunction(app.okBox,"Update","Already Up To Date",parent=None)
			return
		if "wifiscan.py" in output:
			#need to restart wifiscan
			pass
		if "gui.py" in output:
			#need to restart gui
			os.exec*()
	else:
		app.queueFunction(app.errorBox,"Connection Required","No Internet Connection is available",parent=None)
	
	

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
if system=="pi":
	app.setGeometry("fullscreen")
else:
	app.setSize(800,480)
app.setTitle("Pi Mobile")
#Tool BAR setup
app.addToolbar(tools,tbFunc,findIcon=True)


#Status Bar Setup
app.addStatusbar(fields=4)
app.setStatusbarWidth(4,3)
app.setStatusbarBg("red",3)
app.setStatusbar("GPS",3)

#Main Tabbed Frame
app.startTabbedFrame("Main")

app.startTab("GPS")
app.stopTab()

app.startTab("WifiScan")
app.addLabel("totalWifi","Total Number of AP's:")
app.addLabel("dailyWifi","AP's Added today:")
app.stopTab()

app.stopTabbedFrame()

#Registered Events
app.registerEvent(checkUpdate)

#Launch Gui
app.go()

