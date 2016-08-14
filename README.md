# cura-tikoConnection
Connection class for Cura to communicate with Tiko 3D printer. Supports:
- Cura 15.04.3
- Tiko firmware ```taf: 1.0.7-34b0d4a```
- Connecting, printing (all calibration modes), cancelling in Cura.

##Get Started
1. Place these files in ```/Cura/util/printerConnection``` *(ie. ```C:\Program Files\Cura_15.04.3\Cura\util\printerConnection```)*
2. Connect with Tiko, open Cura, open a model.
3. Change to Pronterface UI *(File > Preferences...)*
4. "*Print with Tiko*" button. Then press "*Print*".

##Changing Calibration Mode
In ```tikoConnection.py```, look for ```self._calibrationMode```, select calibration mode by commenting out the others.

###Example
```
# !!!!!!!! CHANGE CALIBRATION MODE HERE !!!!!!!!
#self._calibrationMode = self.CALIBRATION_AUTO
#self._calibrationMode = self.CALIBRATION_SKIP
self._calibrationMode = self.CALIBRATION_MANUAL # This one is selected
```
##Changing Manual Calibration Values
In ```tikoConnection.py```, look for ```self._manualCalibrationVals``` to change the three calibration points. Default position is ```G0 Z0.00```. Pressing down is -0.10 interval, up is +0.10 interval. 

###Example
```
self._manualCalibrationVals = [ 
	# 0.1 intervals per button press. down is -, up is +
	"G0 Z-1.90", #1st calibration position
	"G0 Z-1.90", #2nd calibration position
	"G0 Z-1.90"] #3rd calibration position
```
- Valid: `G0 Z-1.90`
- Valid: `G0 Z1.90`
- Not Valid: `G0 Z 1.90`

##Known Issues:
- May sometimes not work. Restarting the printer and/or Cura may do the trick.
- Tiko does not seem to have printing state info in the API yet. As such, things like temperature monitoring, pausing, printing state, printing time left etc. are all not implemented (at least not through actual communication with the printer). Only the print and cancel button work so far.
- Tested in 15.04.3 only. And briefly at that.
- Proof-of-concept only, not at all refined, use at your own risk.
