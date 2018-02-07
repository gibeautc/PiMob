#!/usr/bin/env python


import logging as log
import MySQLdb
import subprocess
import sys
import time
import Queue
import gps
import sys
import os
from threading import Thread
db=MySQLdb.connect('localhost','root','aq12ws','wifi')
curs=db.cursor()
que=Queue.Queue()
#sudo iwlist wlan0 scan
adds=0
if os.path.isdir("/home/pi"):
	system="pi"
else:
	system="chadg"

toGuiPath="/home/"+system+"/pipeToGui"
fromGuiPath="/home/"+system+"/pipeFromGui"

try:
	os.mkfifo(toGuiPath)
except:
	pass
try:
	os.mkfifo(fromGuiPath)
except:
	pass
toGui=os.open(toGuiPath,os.O_RDWR)
fromGui=os.open(fromGuiPath,os.O_RDONLY|os.O_NONBLOCK)
log.basicConfig(filename='scan.log',level=log.INFO,format=    '%(threadName)s %(asctime)s %(levelname)s : %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')


class entry:
	def __init__(self,name,level,security,lat,lon,address):
		self.name=name
		self.level=level
		self.security=security
		self.lat=lat
		self.lon=lon
		self.address=address
	def addDB(self):
		global adds
		q="select 1 from devices where address=%s"
		curs.execute(q,[self.address,])
		d=curs.fetchall()
		if len(d)==0:
			adds=adds+1
			log.debug("Not in devices yet")
			q="insert into devices(address,name,sec) values(%s,%s,%s)"
			out=[str(self.address),str(self.name),str(self.security)]
			log.debug("adding New Device")
			log.debug(out)
			try:
				curs.execute(q,out)
				db.commit()
			except:
				db.rollback()
				log.error("Error Adding Device")
				log.error(sys.exc_info())
    
		q="insert into records(tor,sig,lat,lon,address) values(Now(),%s,%s,%s,%s)"
		out=[str(self.level),self.lat,self.lon,self.address]
		log.debug("adding")
		log.debug(out)
		try:
			curs.execute(q,out)
			db.commit()
		except:
			db.rollback()
			log.error("Error Adding Entry")
			log.error(sys.exc_info())
    
def scan(lat,lon):
	try:
		out=subprocess.check_output(['sudo','iwlist','wlan0','scan'])
	except:
		log.error("Scan Failed")
		log.error(sys.exc_info())
		return
	cells=out.split("Cell")
	for c in cells:
		e=None
		q=None
		a=None
		s=None
		lines=c.split("\n")
		for line in lines:
			if "Address" in line:
				a=line.split("Address:")
				a=a[1]
                                a=a.replace(" ","")
			if "ESSID" in line:
				e=line.split(":")
				e=e[1]
				e=e.replace('"',"")
			if "Encryption key" in line:
				if ":on" in line:
					s=0
				else:
					s=1
			if "Quality" in line:
				q=line.split("level=")
				q=q[1]
				q=int(q.replace("dBm",""))
		if a is None or e is None:
			continue
		if e is None:
			e=""
		if q is None:
			q=0
		if s is None:
			s=0
		if a is None:
			a="Unknown"
                if e.replace(" ","")=="":
                    continue
		if len(e)>30:
			log.warning("Truncating Name")
			e=e[:29]
		tmp=entry(e,q,s,lat,lon,a)
		que.put(tmp)

def dbWorker():
	log.info("dbWorker Starting")
	while True:
		try:
			i=que.get(False)
		except:
			log.info("Queue Currently Empty")
			time.sleep(5)
			continue
		i.addDB()
		que.task_done()

def startDBWorker():
	t=Thread(target=dbWorker)
	t.name="dbWorker"
	t.daemon=True
	t.start()
	return t
def sendStats():
	q="SELECT 1 from devices"
	curs.execute(q)
	d=curs.fetchall()
	tot=len(d)
	q="SELECT address from records where tor=CURDATE()"
	curs.execute(q)
	d=curs.fetchall()
	lst=[]
	for dev in d:
		if dev not in lst:
			lst.append(dev)
	day=len(lst)
	os.write(toGui,"TOTAL:"+str(tot)+"\n")
	os.write(toGui,"DAY:"+str(day)+"\n")


if __name__=="__main__":
    #check time?
	#global adds
	#get gps object, and gps thread so we can ensure it is alive
	g,gt=gps.start()
	t=startDBWorker()
	while True:
		if not t.isAlive():
			log.error("DBWorker thread died...restarting")
			t=startDBWorker()
		if not gt.isAlive():
			log.error("GPS thread is Dead")
			log.info("Restarting GPS")
			g,gt=gps.start()
		if g.status==g.gpsStatNoConn:
			log.warning("No GPS yet....waiting")
			os.write(toGui,"GPS:0\n")
			time.sleep(10)
			continue
		if g.cur_pos.posfix:
			os.write(toGui,"GPS:1\n")
			scan(str(g.cur_pos.lat),str(g.cur_pos.lon))
		else:
			os.write(toGui,"GPS:0\n")
			log.warning("No Position Fix from GPS....")
			time.sleep(10)
		log.info("Current Queue Size: "+str(que.qsize()))
		log.info("NUMBER OF DEVICES ADDED: "+str(adds))
		sendStats()
		time.sleep(5)
    
