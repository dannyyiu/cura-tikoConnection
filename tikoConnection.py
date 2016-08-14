"""
@author Danny Yiu
@brief
Tiko printer connection. 
Detect printer based on /status API if 192.168.1.1 exists.
Calibrate (skip, auto, manual). Proof of concept set to skip.
Send Gcode to printer directly.
"""

#Standard libs
import threading
import json
import httplib
import urllib
import time

#Cura libs
#from Cura.util.printerConnection import printerConnectionBase
import printerConnectionBase

class tikoConnectionGroup(printerConnectionBase.printerConnectionGroup):
	"""
	Tiko connection group class. 
	As there is only one printer per connection, it is a single item list.
	
	IMPORTANT: Must be connected before Cura connects to Tiko. Otherwise
	untested.
	"""
	def __init__(self):
		super(tikoConnectionGroup, self).__init__("Tiko")
		self._list = [tikoConnection("Tiko 1")]

	def getAvailableConnections(self):
		return self._list

	def getIconID(self):
		return 5

	def getPriority(self):
		return 120

class tikoConnection(printerConnectionBase.printerConnectionBase):
	"""
	Tiko printer class.
	Connects Tiko printer, handles API, sends gcode.
	
	Note: Currently skips calibration for a quick print, proof of concept.
	For calibration: 
	Code:        self._sendGcode()
	Constants:   (see calibration constants below)
	Flag:        self._calibrationMode
	"""
	def __init__(self, name):
		super(tikoConnection, self).__init__(name)
		
		#Tiko: Calibration constants
		self.CALIBRATION_SKIP = 0 #Modes for calibration
		self.CALIBRATION_AUTO = 1
		self.CALIBRATION_MANUAL = 2
		self.CODE_AUTO= 'G29' #Auto cal prepended code
		self.CODE_MANUAL = { 
			#Manual cal, separate HTTP sent for each list item
			'INIT': ['G31', 'G28', 'G162 P1'],
			'POS_1_DONE': ['M666 P1', 'G162 P2'],
			'POS_2_DONE': ['M666 P2', 'G162 P3'],
			'POS_3_DONE': ['M666 P3', 'M104 Sundefined', 'G32\nG28']}
		#Tiko: Network constants
		self.HOST = '192.168.1.1' #Tiko Host IP
		self.API = {
			'STATUS': ['/status', 'GET'], #status, json
			'WIFI': ['/wifi', 'GET'], #wifi networks, json
			'SCAN': ['/data/wireless/scan', 'GET'], #wifi, json
			'LED': ['/leds', 'PUT'], #led brightness, "ok"
			'EXTRUDER': ['/extruder', 'GET'], #load filament, "ok"
			'UNLOADFIL': ['/unloadfil', 'PUT'], #unload filament, "ok"
			'CANCEL': ['/cancel', 'PUT'], #cancel, "ok"
			'GCODE_POST': ['/gcode', 'POST'], #gcode payload, "ok"
			'GCODE_PUT': ['/Gcode', 'PUT']} #manual gcode, "ok"
		self.CONTENT_TYPE = 'text/plain'
		
		#Tiko: Defaults
		
		# !!!!!!!! CHANGE CALIBRATION MODE HERE !!!!!!!!
		self._calibrationMode = self.CALIBRATION_AUTO
		#self._calibrationMode = self.CALIBRATION_SKIP
		#self._calibrationMode = self.CALIBRATION_MANUAL
		
		# !!!!! CHANGE MANUAL CALIBRATION VALUES HERE !!!!!
		self._manualCalibrationVals = [ 
			# 0.1 intervals per button press. down is -, up is +
			"G0 Z-1.90", #1st calibration position
			"G0 Z-1.90", #2nd calibration position
			"G0 Z-1.90"] #3rd calibration position
			
		self._gcode = "" #gcode string to send in POST
		self._statusString = "" #temporary way to prevent HTTP bombardment
		self._http = None #http connection
		self._printSent = False
		self._firstTimeCon = False #First time connect flag.
		
		
		#Standard Cura defaults
		self._isAvailable = False
		self._printing = False
		self._lineCount = 0
		self._progressLine = 0
		self._errorCount = 0
		self.printThread = threading.Thread(target=self._tikoThread)
		self.printThread.daemon = True
		self.printThread.start()
		
	#Load the data into memory for printing, returns True on success
	def loadGCodeData(self, dataStream):
		if self._printing:
			return False
		#Save as one big string for HTTP send
		self._lineCount = len(dataStream)
		self._gcode = "".join(dataStream)
		self._doCallback()
		return True
		
	def pretendLoad(self):
		self._lineCount = 100

	#Start printing flag
	def startPrint(self):
		if self._printing or self._gcode == "":
			return
		self._progressLine = 0
		self._printing = True

	#Abort the previously loaded print file
	def cancelPrint(self):
		if self._request('CANCEL'):
			self._printing = False
	
	#Tiko does not have printing state info for now.
	def isPrinting(self):
		return self._printing

	#Amount of progression of the current print file. 0.0 to 1.0
	def getPrintProgress(self):
		if self._lineCount < 1:
			return 0.0
		return float(self._progressLine) / float(self._lineCount)
		
	#Return connection availability
	def isAvailable(self):
		return self._isAvailable

	#Return status string from /status API, empty string if error.
	#Temporarily only returns the /status string on first load.
	def getStatusString(self):
		if not self._firstTimeCon:
			try:
				#response = self._request('STATUS')
				if response:
					return response
			except:
				return ""
		else:
			return self._statusString
		return ""
		
	def _request(self, input, method = "GET", postData = None):
		#Connect, or use old connection
		if self._http is None:
			self._http = httplib.HTTPConnection(self.HOST, timeout=30)
		
		#API vs non-API filter
		url = self.API[input][0] if self.API[input] else input
		method = self.API[input][1] if self.API[input] else method
		print self.HOST + url + "   " + method
		try: 
			if postData:
				#print postData
				self._http.request(
					method, 
					url, 
					postData)
			else:
				self._http.request(
					method, 
					url)
		except:
			self._http.close()
			return None
		try:
			response = self._http.getresponse()
			responseText = response.read()
		except:
			self._http.close()
			return None
		return responseText
		
	def _sendGcode(self):
		#Turn on "sent" flag
		self._printSent = True
		
		#Skip calibration
		if self._calibrationMode == self.CALIBRATION_SKIP:
			#self._request('EXTRUDER', postData=self._gcode)
			self._request('EXTRUDER')
			time.sleep(1) #sometime immediate send overloads it
			self._request('GCODE_POST', postData=self._gcode)
		
		#Auto calibration
		elif self._calibrationMode == self.CALIBRATION_AUTO:
			self._request('EXTRUDER')
			time.sleep(1)
			#Send G29\n + gcode
			self._request('GCODE_POST', 
			              postData=self.CODE_AUTO + "\n" +  self._gcode)
		
		#Manual calibration		
		elif self._calibrationMode == self.CALIBRATION_MANUAL:
			self._request('EXTRUDER')
			time.sleep(1)
			#Send init codes
			for code in self.CODE_MANUAL['INIT']:
				self._request('GCODE_PUT', postData=code)
			#Send 1st position Z codes
			time.sleep(18) #allow time for nozzle to move to next position
			self._request('GCODE_PUT', postData=self._manualCalibrationVals[0])
			time.sleep(2) # Z moving time
			#Send 1st position done, start 2nd position
			for code in self.CODE_MANUAL['POS_1_DONE']:
				self._request('GCODE_PUT', postData=code)
			time.sleep(5) #allow time for nozzle to move to next position
			#Send 2nd position Z codes
			self._request('GCODE_PUT', postData=self._manualCalibrationVals[1])
			time.sleep(2)
			#Send 2nd position done, start 3rd position
			for code in self.CODE_MANUAL['POS_2_DONE']:
				self._request('GCODE_PUT', postData=code)
			time.sleep(5)
			#Send 3rd position Z codes
			self._request('GCODE_PUT', postData=self._manualCalibrationVals[2])
			time.sleep(2)
			#Send 3rd position done, start print.
			for code in self.CODE_MANUAL['POS_3_DONE']:
				self._request('GCODE_PUT', postData=code)
			#Send model gcode
			self._request('GCODE_POST', postData=self._gcode)
			
	#Main thread
	def _tikoThread(self):
		while True:
			#Verify connected to Tiko
			if not self._firstTimeCon:
				stateReply = self._request('STATUS')
				if stateReply is None or not stateReply:
					self._errorCount += 1
					if self._errorCount > 10:
						print "cant connect >10"
						if self._isAvailable:
							self._printing = False
							self._isAvailable = False
							self._doCallback()
						time.sleep(15)
						self._group.remove(self._host)
						return
					else:
						print "Connection attempt %d/10, retrying..." % \
							  self._errorCount
						time.sleep(1)
					continue
			self._errorCount = 0
			self._firstTimeCon = True

			#We have a good connection from here.
			if not self._isAvailable:
				print "Good connection established."
				self._isAvailable = True
			
			if not self._printing:
				time.sleep(5)
			else:
				if not self._printSent:
					self._sendGcode()
				#Progress line is just fixed time based until Tiko adds status
				time.sleep(0.01)
				self._progressLine += 1
				if self._progressLine == self._lineCount:
					self._printing = False
					self._gcode = ""
			self._doCallback()
			
if __name__ == '__main__':
	d = tikoConnection("Tiko 1")
	print 'Searching for Tiko...'
	while not d.isAvailable():
		time.sleep(1)

	while d.isPrinting():
		print 'Tiko already printing! Requesting stop...'
		d.cancelPrint()
		time.sleep(5)

	print 'Tiko found, printing!'
	#d.loadFile("D:/documents/3D/tiko/s3d/square2cm-2mmwall-s3d.gcode")
	with open("D:/documents/3D/tiko/s3d/square2cm-2mmwall-s3d.gcode", 'r') as r:
		d._gcode = r.read()
	d.pretendLoad() #For standalone test
	d.startPrint()
	while d.isPrinting() and d.isAvailable():
		time.sleep(1)
	print 'Done'
