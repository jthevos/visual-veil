# kuatroKinectClient.py       Version 1.0     13-Aug-2014
#     David Johnson, Bill Manaris, and Seth Stoudenmier
#
# The Kuatro Client tracks the x, y, z coordinates of mulitple users 
# within range of a configured depth sensor.  The coordinates are sent via OSC messages
# to the Kuatro Server for coordination within a Virtual World, as defined by the server.  
# 
#  Supported Controllers for the Kautro Client are Microsoft Kinect, model 1414, 
#  and the Asus Xtion Pro.
#
#  See README file for full instructions on using the Kuatro System


from osc import OscOut
from osc import OscIn
from threading import *
import sys
import pickle
import socket
from gui import *

# how often to get data from the Kinect (frames per second)
# (increase to get data more often, but this slows down the system)
# before use, verify that this FRAME_RATE value is the same as that of
# the corresponding kuatroKinectClient
FRAME_RATE = 30 

class Calibrator():

   ##### OSC Namespace #####
   NEW_USER_MESSAGE = "/kuatro/newUser"
   LOST_USER_MESSAGE = "/kuatro/lostUser"
   JOINT_COORDINATES_MESSAGE = "/kuatro/jointCoordinates"
   REGISTER_DEVICE_MESSAGE = "/kuatro/registerDevice"
   CALIBRATE_DEVICE_MESSAGE = "/kuatro/calibrateDevice"


   def __init__(self, clientID):

      # initializing variables
      self.clientID = clientID                                                # used to identify the tied client
      self.minX = None                                                        # used to store current calibration data
      self.minY = None
      self.minZ = None
      self.maxX = None
      self.maxY = None
      self.maxZ = None 


   ####################################
   ######## Helper Functions ##########
   ####################################

   def calibrate(self, x, y, z):
      '''Finds min and max of coordinate data'''

      # update min values (if needed)
      self.minX = min(x, self.minX)
      self.minY = min(y, self.minY)
      self.minZ = min(z, self.minZ)

      # update max values (if needed)
      self.maxX = max(x, self.maxX)
      self.maxY = max(y, self.maxY)
      self.maxZ = max(z, self.maxZ)
      

   def getCalibratedData():
      '''Returns the calibrated data as a set'''
         
      return [self.minX, self.minY, self.minZ, self.maxX, self.maxY, self.maxZ]
   

   ####################################
   ###### Calibration Process #########
   ####################################

   def setup(self):
      '''Check for existing calibration data on file, if there: return it, if not: return None'''

      # Try to load the file if it is there...
      try:
         # load serialized data

         # Uncomment out if too many files are being created by pickle.
         # Make sure to uncomment the same line in calibrationStop
         calibrationFile = open( self.clientID + ".calibrationData.p", "rb" )   # open the file to read calibration data (apend clientID to file for unique ID)
         calibrationData = pickle.load(calibrationFile)        # read calibration data
         calibrationFile.close()                               # close the file

         # min and max values loaded from the file
         self.minX = calibrationData["minX"]
         self.minY = calibrationData["minY"]
         self.minZ = calibrationData["minZ"]
         self.maxX = calibrationData["maxX"]
         self.maxY = calibrationData["maxY"]
         self.maxZ = calibrationData["maxZ"]

         return [self.minX, self.minY, self.minZ, self.maxX, self.maxY, self.maxZ, True]
         
         print "Kinect Calibrated:", self.clientID
         print "Min Values", self.minX, self.minY, self.minZ
         print "Max Values", self.maxX, self.maxY, self.maxZ
      
      # The file was not there, so let the user know there is no calibration data
      except:
         # should only reach here if server has never been calibrated.

         # There is no calibration data so let's send default values (default values are estimates of actual Kinect bounds)
         minX = -5000
         minY = -3000
         minZ = 0
         maxX = 5000
         maxY = 3000
         maxZ = 15000

         return [minX, minY, minZ, maxX, maxY, maxZ, False]

         print "No calibration data found for Kinect:", self.clientID
         print "Using default values. Please run calibration process."


   def  calibrationStart(self):
      ''' This is the Calibration Start Menu Item Callback function. It is 
          used to calibrate the Kinect Device with the installation space. '''
      
      # Recalibrating so resetting starting min and max values to arbitary high and low values
      self.minX = 1000000000  # set min values to an arbitrary high value so we know that min values will be smaller
      self.minY = 1000000000
      self.minZ = 1000000000
      self.maxX = -1000000000 # set max values to an arbitrary low value so we know that max values will be larger
      self.maxY = -1000000000
      self.maxZ = -1000000000


   def calibrationStop(self):
      ''' Callback function for the Menu Item, Stop.  Stops the Calbration process 
          and sends the updated information to the server '''

      # save data with pickle
      calibrationData = { "minX" : self.minX , "minY" : self.minY , "minZ" : self.minZ , "maxX" : self.maxX , "maxY" : self.maxY , "maxZ" : self.maxZ }

      # Uncomment out if too many files are being created by pickle.
      # Make sure to uncomment the same line in calibrateWithServer

      calibrationFile = open( self.clientID + ".calibrationData.p", "wb" )   # open file to write data (apend clientID to file for unique ID)
      pickle.dump( calibrationData,  calibrationFile)       # write calibration data
      calibrationFile.close()                               # close the file


      return [self.minX, self.minY, self.minZ, self.maxX, self.maxY, self.maxZ] # send final data to server
         

if __name__ == '__main__':
   cal = Calibrator() # Create and start the Calibrator
