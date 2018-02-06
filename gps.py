#!/usr/bin/env python

# Udev Rule for /etc/udev/rules.d/99 Com.....
# ACTION=="add", ATTRS{idVendor}=="067b", ATTRS{idProduct}=="2303", SYMLINK+="GPSUSB"


#Notes/Todo
# Averaging will continue to fill up, unrestriced
# dont think I am catching the loss of signal and updating posfix to false
# launch own thread to run GPS,
# add status flag that can be checked maybe
# add logging

import math
import serial
import sys
import time
from collections import deque
import json
from threading import Thread
import logging as log
import subprocess
import datetime
#log.basicConfig(filename='GPS.log',level=log.DEBUG,format=    '%(asctime)s %(levelname)s : %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

#ser=serial.Serial('/dev/ttyUSB0',4800,timeout=1)
#not_tracking=[]
class Pos():
	def __init__(self):
		self.latDeg=None	#int
		self.lonDeg=None	#int
		self.latMin=None	#dec min
		self.lonMin=None	#dec min
		self.lat=None	#dec deg
		self.lon=None	#dec deg
		self.hour=None
		self.min=None
		self.sec=None
		self.timeset=False
		self.posfix=False
		self.altfix=False
		self.alt=None		#ft
		self.satcnt=None
		self.speed=None	#mph
		self.course=None	#deg
		self.checkT=0
		self.checkF=0
		self.timezone=-7
		self.month=None
		self.day=None
		self.year=None
class GPS():
	gpsStatNoConn=0
	gpsStatConn=1
	gpsStatLock=2
	def __init__(self):
		#add serial here
		self.controlClock=False
		self.cur_pos=Pos()
		self.checkT=0
		self.checkF=0
		self.ave_list=deque()
		self.status=self.gpsStatNoConn
		#0-Not Connected, no data
		#1-Connected, no lock
		#2-Connected and lock
		self.ser=None
	def connect(self):
		try:
			self.ser=serial.Serial('/dev/GPSUSB',4800,timeout=1)
			self.status=self.gpsStatConn
		except:
			log.error(sys.exc_info())
			self.status=self.gpsStatNoConn
	def get_pos(self):
		j=json.loads("{}")	
		if self.cur_pos==None:
			return j
		if not self.cur_pos.posfix:
			return j
		j["lat"]=self.cur_pos.lat
		j["lon"]=self.cur_pos.lon
		j["speed"]=self.cur_pos.speed
		j["course"]=self.cur_pos.course
		if self.cur_pos.altfix:
			j["alt"]=self.cur_pos.alt

		return j 
	def checkSystemTime(self):
		#check system time and update it if needed and flag is set
		try:
			sysTime=datetime.datetime.now()
			gpsTime=datetime.datetime(self.year,self.month,self.day,self.hour,self.min,self.sec)
			delta=sysTime-gpsTime
		except:
			log.error("Getting Time")
			log.error(sys.exc_info())
			return
		if delta<0:
			delta=delta*-1
		if delta>30:
			log.warning("Time Drift of : "+str(delta)+" seconds")
			if self.controlClock:
				#using 30 seconds now, but could probably make it less (2?)
				try:
					dateString=str(self.year)+str(self.month)+str(self.day)
					subprocess.check_output(['date','+%Y%m%d','-s',dateString])
					timeString=str(self.hour)+":"+str(self.min)+":"+str(self.sec)
					subprocess.check_output(['date','+%T','-s',timeString])
					log.info("Time Shift Complete")
				except:
					log.error("Setting Time Failed")
					log.error(sys.exc_info())
			else:
				log.warning("GPS and System time out of sync")
				log.warning("GPS Does not have Control over system clock")
	def check_sum_percent(self):
		if self.checkT>0:
			return float(self.checkT)/float(self.checkT+self.checkF)
		return 0
	def check_sum(self,line):
		try:
			e=line.split("*")
		except:
			log.debug("No CheckSum")
			self.checkF=self.checkF+1
			return False
		msg=list(e[0])
		msg=msg[1:] # remove the $
		res=0

		for c in msg:
			res=res^ ord(c)
		res=hex(res).upper()
		check=""
		try:
			check=e[1]
			check=check[:2]
			check=str(check).upper()
			check="0X"+check	
			if res==check:
				self.checkT=self.checkT+1
				return True
		except:
			self.checkF=self.checkF+1
			return False
		return False
	def feed(self, line):
		if self.check_sum(line)==False:
			log.debug("CheckSum Failed")
			return 
			
		#send new line of data to GPS Class
		if "GPGGA" in line:
			self.processGPGGA(line)
			return
		if "GPRMC" in line:
			self.processGPRMC(line)
			return
		#['$GPGLL', '$GPGSA', '$GPRMC', '$GPGSV']
		#not processing it at this time
		#print("Not Processing this type:")
		#print(line)
		#e=line.split(',')
		#if e[0] not in not_tracking:
		#	not_tracking.append(e[0])
	def processGPRMC(self,line):
		try:
			e=line.split(',')
			#2-data status V-warning
			#7-speed over ground in knots
			#8- track made good in degrees true
			#9 UT date  ddmmyy
			#10 magnetic variation degrees
			#11 E or west     East subtracks from true course
			log.debug("Processing GPRMC message")
			if e[2]=='V':
				return
			self.cur_pos.speed=float(e[7])*1.15
			self.cur_pos.course=float(e[8])
		except:
			self.cur_pos.speed=None
	def processGPGGA(self,line):
		log.debug(line)
		#$GPGGA,070538.000,4436.9643,N,12304.3958,W,2,08,1.0,89.9,M,-20.7,M,3.8,0000*76
		#         time           lat         lon    fix
		log.debug("Processing GPGGA message")
		
		try:
			e=line.split(",")
			self.cur_pos.posfix=int(e[6])
			if self.cur_pos.posfix==0:
				log.warning("GPS Signal Lost")
				return
			#if N= neg?
			lat=float(e[2])
			if e[3]=='S':
				lat=lat*-1
			lon=float(e[4])
			if e[5]=='W':
				lon=lon*-1
			self.cur_pos.latDeg=int(lat/100)
			self.cur_pos.latMin=lat-(self.cur_pos.latDeg*100)
			self.cur_pos.lonDeg=int(lon/100)
			self.cur_pos.lonMin=lon-(self.cur_pos.lonDeg*100)
			self.cur_pos.latMin=abs(self.cur_pos.latMin)
			self.cur_pos.lonMin=abs(self.cur_pos.lonMin)
			self.cur_pos.lat=self.cur_pos.latDeg+self.cur_pos.latMin/60
			self.cur_pos.lon=self.cur_pos.lonDeg+self.cur_pos.lonMin/60
			self.cur_pos.alt=float(e[9])
			self.cur_pos.alt=self.cur_pos.alt*3.28084 #convert to feet
			t=float(e[1])
			t=int(t)
	
			self.cur_pos.hour=t/10000
			self.cur_pos.min=(t-self.cur_pos.hour*10000)/100
			self.cur_pos.sec=t-self.cur_pos.hour*10000-self.cur_pos.min*100
		except:
			self.cur_pos=None
	def printpos(self):
		if self.cur_pos.timezone is not None and self.cur_pos.hour is not None:
			hour=self.cur_pos.hour+self.cur_pos.timezone
			if hour>23:
				hour=hour-24
			if hour<0:
				hour=hour+24
		else:
			hour=self.cur_pos.hour
		if self.cur_pos.posfix==0:
			status="FAIL"
		else:
			status="GOOD"
		log.debug("*********************")
		log.debug(str(hour)+":"+str(self.cur_pos.min)+":"+str(self.cur_pos.sec))
		log.debug("Status: "+status)
		log.debug("Lat   : "+str(self.cur_pos.latDeg)+" "+str(self.cur_pos.latMin))
		log.debug("Lon   : "+str(self.cur_pos.lonDeg)+" "+str(self.cur_pos.lonMin))
		log.debug("Speed : "+str(self.cur_pos.speed))
		log.debug("Alt   : "+str(self.cur_pos.alt))
		if self.checkT>0:
			log.debug("Sum   : "+str(float(self.checkT)/float(self.checkT+self.checkF)))
		else:
			log.debug("No Check Sum Yet")
		log.debug("Len ave: "+str(len(self.ave_list)))
		log.debug("*********************")
		log.debug("\n")
		
def dist(s,e):
	try:
		sLat=math.radians(s.lat)
		sLon=math.radians(s.lon)
		eLat=math.radians(e.lat)
		eLon=math.radians(e.lon)
	except:
		log.error("invalid position variables")
		return
	latD=math.radians(e.lat-s.lat)
	lonD=math.radians(e.lon-s.lon)
	R=6371000
	a=math.sin(latD/2)*math.sin(latD/2)+math.cos(sLat)*math.cos(eLat)*math.sin(lonD/2)*math.sin(lonD/2)
	c=2*math.atan2(math.sqrt(a),math.sqrt(1-a))
	d=R*c
	ft= d*3.28084  #in feet
	return ft

def bearing(s,e):
	try:
		sLat=math.radians(s.lat)
		sLon=math.radians(s.lon)
		eLat=math.radians(e.lat)
		eLon=math.radians(e.lon)
	except:
		log.error("invalid position variables")
		return
	y=math.sin(eLon-sLon)*math.cos(eLat)
	x=math.cos(sLat)*math.sin(eLat)-math.sin(sLat)*math.cos(eLat)*math.cos(eLon-sLon)
	brg=math.atan2(y,x)
	brg=math.degrees(brg)
	return brg


def run(g):
	gps=g
	i=0
	while gps.status!=gps.gpsStatConn:
		gps.connect()
		log.warning("Trying to connect to GPS")
		time.sleep(5)
	log.info("Connected")
	while True:
		line=gps.ser.readline()
		if i%100==0:
			log.info("Checking time")
			gps.checkSystemTime()	
		if len(line)>0:
			gps.feed(line)
		#gps.printpos()
	
def start():
	gps=GPS()
	t=Thread(target=run,args=[gps,])
	t.daemon=True
	t.name="GPS"
	t.start()
	log.info("Tread Running, returning gps object to parent")
	return gps

if __name__=="__main__":
	g=start()
	while True:
		time.sleep(5)
		print("Still Here")


