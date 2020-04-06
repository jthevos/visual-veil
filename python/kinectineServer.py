# kuatroServer.py       Version  1.3     30-Oct-2017
#     Kyle Stewart, David Johnson, Bill Manaris, and Seth Stoudenmier
#
# The Kuatro Server receives x, y, z coordinates, via OSC, of users in a being
# tracked in a space by one or more depth sensors, such as the Kinect.
# The data is received by one more more Kuatro Clients.
# These data is placed in a normalized coordinate space (virtual world).
# The normalized data is also sent, via OSC, to one or more Kuatro Views,
# as specified by the project's interaction design.
#
# See README file for full instructions on using the Kuatro System
#
#
#  LOG:
#     03-Nov-17:  Updated to include a GUI to track client input and facilitate calibration
#     30-Oct-17:  Updated with the ability to track multiple joints as well as hand states
#     26-Oct-17:  Updated to include server-side calibration for clients
#     28-Oct-14:  Updated to only allow one connection per view (i.e. only one entry into the viewPort list)
#     14-Aug-14:  Updated OSC Addresses to be constants
#     13-Aug-14:  Updated Server so messages now require a unique client ID.  This allows
#              the server to track coordinates from multiple devices.
#
#  TO DO:
#


from osc import OscIn, OscOut
from gui import *
from music import *
from calibrator import Calibrator
import sys

class KuatroServer():

   ##### OSC Namespace #####
   NEW_USER_MESSAGE = "/kuatro/newUser"
   LOST_USER_MESSAGE = "/kuatro/lostUser"
   JOINT_COORDINATES_MESSAGE = "/kuatro/jointCoordinates"
   HAND_STATE_MESSAGE = "/kuatro/handState"
   REGISTER_DEVICE_MESSAGE = "/kuatro/registerDevice"
   CALIBRATE_DEVICE_MESSAGE = "/kuatro/calibrateDevice"
   REGISTER_VIEW_MESSAGE = "/kuatro/registerView"
   PROCESSING_MESSAGE = "/kuatro/processing"

   def __init__(self, port = 50505, verbose = 0):

      # *** add comments below
      self.nextUserID = 0              # used to find the next available user ID (this is never decremented so IDs are not reused)
      self.deviceUsers = {}            # maps a device user ID (combination of user ID and client ID) to a corresponding Virtual World user ID (This is needed so we can send views an integer value for the User ID)
      self.virtualUsers = {}           # stores Virtual World User IDs and each user's coordinates within the Virtual World

      self.devices = []                # stores a list of clients/devices which have connected to the server
      self.calibrators = []            # stores a list of the calibrators the server has created in the form [calibrator, isActiveCheckbox]
      self.deviceLights = []           # stores circle "lights" for each registered device that show data flow

      self.viewInfo = []               # stores a tuple including the IP Address and Port of all registered view.  Used to ensure that that same view does not register multiple times.
      self.viewPorts = []              # stores the OSC Port to all registered views
      self.deviceCalibrationData = {}  # stores calibration data from calibrators
      self.calibrating = False         # whether the server is currently calibrating or not
      self.lightDelay = 500            # delay between resetting device lights

      # the max coordinates of the Virtual World
      self.virtualMaxX = 1000
      self.virtualMaxY = 1000
      self.virtualMaxZ = 750    # Virtual World is 2D using X and Z values

      self.verbose = verbose  # turn on logging of user tracking. 0 = Off, 1 = User Tracking Data, 2 = User Tracking plus Echo OSC Messages


      # configure OSC protocol communication
      try:

         oscIn = OscIn(port)
         oscIn.hideMessages()  #***

         # if verbose logging is set to 2 turn on echo message
         if verbose == 2:
            oscIn.onInput("/.*", self.echoMessage)

         # the Client-to-Server API
         oscIn.onInput(KuatroServer.NEW_USER_MESSAGE, self.addUser)
         oscIn.onInput(KuatroServer.LOST_USER_MESSAGE, self.removeUser)
         oscIn.onInput(KuatroServer.JOINT_COORDINATES_MESSAGE, self.handleUserData)
         oscIn.onInput(KuatroServer.HAND_STATE_MESSAGE, self.echoHandState)
         oscIn.onInput(KuatroServer.REGISTER_DEVICE_MESSAGE, self.registerDevice)
         oscIn.onInput(KuatroServer.PROCESSING_MESSAGE, self.visualize)

         # the View-to-Server API
         oscIn.onInput(KuatroServer.REGISTER_VIEW_MESSAGE, self.registerView)

      except:
         print "Error:  Unable to setup OSC In port. Port " + port + " may already be in use."

      # create calibration GUI
      self.display = Display("Kuatro Server", 600, 600, 0, 0, Color.BLACK)

      # create Menu for calibration
      calibrateMenu = Menu("Calibrate")
      calibrateMenu.addItemList(["Start", "Stop"], [self.calibrationStart, self.calibrationStop])
      self.display.addMenu(calibrateMenu)

      # add label for instructions
      self.instructions = self.display.drawLabel("Select Calibrate > Start to start the calibration process.", 20, 75, Color.WHITE)




   #####################################
   ###### Kuatro Server Callbacks ######
   #####################################

   # These methods coordinate user data input from the view into
   # coordinates consistent with the virutal world.  And then send
   # the new data to all registered views.

   def echoMessage(self, message):
      '''Simply prints OSC address and arguments'''

      address = message.getAddress()
      args = message.getArguments()

      print "\nOSC Event:"
      print "OSC In - Address:", address,
      for i in range(len(args)):
         print ",Argument " + str(i) + ": " + str(args[i]),
      print


   def addUser(self, message):
      ''' Adds a user to the virtual world.  The OSC Message should contain
          the values:
               userID, x, y, z
      '''

      # parse arguments from OSC Message
      args = message.getArguments()
      userID = args[0]
      x = args[1]
      y = args[2]
      z = args[3]
      clientID = args[4]

      user = (userID, clientID)  # make user from each device unique by creating tuple with userID and client id
      #### Update Virutal World with new User
      if user not in self.deviceUsers:     # make sure user does not already exist


         virtualWorldUserID = self.nextUserID   # then get a new user ID for the virtual World
         self.nextUserID = self.nextUserID + 1  # increment user ID

         self.deviceUsers[user] = virtualWorldUserID  # map user to virtual world ID

         newX, newY, newZ = self.calibrateUserCoordinates(x, y, z, clientID)   # get new set of user coordinates calibrated to the Virtual World
         self.virtualUsers[virtualWorldUserID] = (newX, newY, newZ)            # update User dictionary with new user and tuple of user coordinates

         if self.verbose !=0:
            print "Added User:", virtualWorldUserID, "Coords:", newX, newY, newZ

         self.sendMessage(KuatroServer.NEW_USER_MESSAGE, virtualWorldUserID, newX, newY, newZ)  # send message with calibrated user coordinates to registered views


   def removeUser(self, message):
      ''' Removes a user from the Virtual World and updates the registered views.
          The OSC Message should contain the value:
               userID
      '''

      # parse arguments from OSC Message
      args = message.getArguments()
      userID = args[0]
      clientID = args[1]

      user = (userID, clientID)

      ##### Remove user from Virtual World
      if user in self.deviceUsers:                     # verify that user exists in virtual world
         virtualWorldUserID = self.deviceUsers[user]      # then get the virtual world user ID
         del self.virtualUsers[virtualWorldUserID]        # and remove user from user dictionaries
         del self.deviceUsers[user]

         self.sendMessage(KuatroServer.LOST_USER_MESSAGE, virtualWorldUserID)  # send lost user message to registered views

         # if there are no users during calibration, set display to RED
         if self.calibrating and not self.deviceUsers:
            self.display.setColor(Color.RED)

         if self.verbose !=0:
            print "Removed User:", virtualWorldUserID


   def handleUserData(self, message):
      ''' Moves a user to a new location in the virtual world. The OSC Message
          should contain the values:
               userID, jointID, x, y, z, trackingState, clientID
       '''

      # parse arguments from OSC Message
      args = message.getArguments()
      userID = args[0]
      jointID = args[1]
      x = args[2]
      y = args[3]
      z = args[4]
      trackingState = args[5]
      clientID = args[6]

      user = (userID, clientID)

      # this device is transmitting data, turn its dataLight green
      lightSet = self.deviceLights[self.devices.index(clientID)]
      light = lightSet[0]
      light.setColor(Color.GREEN)

      ##### Calibration
      if self.calibrating: # if we're calibrating, forward the coordinate data to the right calibrator
         calSet = self.calibrators[self.devices.index(clientID)]
         calibrator = calSet[0]
         isActiveCheckbox = calSet[1]

         if isActiveCheckbox.isChecked(): # if the calibrator is supposed to be calibrated, send it data
            calibrator.calibrate(x, y, z)

         # we are calibrating and a user is in the space (we're receiving data)
         # set display background to GREEN
         self.display.setColor(Color.GREEN)

      ##### Update User Coordinates
      if user in self.deviceUsers:                           # verify that user exists in device users

         virtualWorldUserID = self.deviceUsers[user]                           # then get the virtual world user ID
         newX, newY, newZ = self.calibrateUserCoordinates(x, y, z, clientID)   # get calibrated coordinates for user
         self.virtualUsers[virtualWorldUserID] = (newX, newY, newZ)            # add new coordinates user dictionary

         # send message with calibrated user coordinates
         self.sendMessage(KuatroServer.JOINT_COORDINATES_MESSAGE, virtualWorldUserID, jointID, trackingState, newX, newY, newZ)

         if self.verbose !=0:
            print "User:", virtualWorldUserID, "Joint:", jointID, "Coords:", newX, newY, newZ


   def echoHandState(self, message):
      ''' Sends the state of existing user's hand to View. The OSC Message
          should contain the values:
             userID, hand, handState, clientID
      '''

      args = message.getArguments()
      userID = args[0]
      hand = args[1]
      handState = args[2]
      clientID = args[3]

      user = (userID, clientID)

      ##### Update User Hand State
      if user in self.deviceUsers:
         virtualWorldUserID = self.deviceUsers[user]
         self.sendMessage(KuatroServer.HAND_STATE_MESSAGE, virtualWorldUserID, hand, handState)

   def registerDevice(self, message):
      ''' Registers a device with the Kuatro Server.  The OSC Message should
          contain the values:
             clientID, sensorType
      '''

      # parse the arguments from the OSC Message
      args = message.getArguments()
      clientID = args[0]

      # have we already registered this client?
      try:
         self.devices.index(clientID) # if we haven't registered, throw an exception
         print "Client Reconnected:", clientID # if we have already registered, client must have reconnected

      except ValueError: # we haven't registered, do so now
         self.devices.append(clientID)

         # create a Calibrator and add the device to devices list
         calibrator = Calibrator(clientID)
         startingValues = calibrator.setup() # returns an array of 6 starting calibration values followed by a boolean of if a data file existed

         minX = startingValues[0]
         minY = startingValues[1]
         minZ = startingValues[2]
         maxX = startingValues[3]
         maxY = startingValues[4]
         maxZ = startingValues[5]
         dataFound = startingValues[6]

         self.calibrateDevice([minX, minY, minZ, maxX, maxY, maxZ], clientID) # update calibration data

         if not dataFound: # if there was no calibration data found, inform the user they need to run the calibration process
            self.display.drawLabel("No calibration data found.  Please run calibration process.", 20, 20, Color.WHITE)

         isActiveCheckbox = Checkbox("") # create a checkbox representing whether or not to include this device during calibration
         self.calibrators.append([calibrator, isActiveCheckbox])

         # add device to the display
         radius = 7
         horizontal = self.devices.index(clientID)*20 + 20

         dataLight = Circle(horizontal+10, 525, radius, Color.GREEN, True) # a "light" which is green when this client receives data, grey otherwise
         timer = Timer(self.lightDelay, self.resetLight, [dataLight], True)  # continually turn light grey if no data coming in
         timer.start()
         self.deviceLights.append([dataLight, timer])
         self.display.add(dataLight)
         deviceLabel = self.display.drawLabel(str(self.devices.index(clientID)), horizontal+radius, 500, Color.WHITE) # create a label for the device
         self.display.add(isActiveCheckbox, horizontal, 540)

         print "Client Registered:", clientID



   # *** describe how this works - it's the heart of the View-to-Server API
   def registerView(self, message):
      ''' Callback function for Kuatro View Registration. To register with this server,
          views send an OSC message containing the IP address and OSC Port of the view
          to the server.  The server then creates list of OSC connections to all registered
          views. '''

      # parse arguments from OSC Message
      args = message.getArguments()
      ipAddress = args[0]
      port = args[1]

      # When a view registers with the server an OSC Out port is created and added to the
      # list of ports.  When sending OSC messages, the server will send the same message
      # to all OSC Ports.

      if (ipAddress, port) not in self.viewInfo:  # only add view if it is not already registered
         try:
            self.viewInfo.append((ipAddress, port))          # add view details to
            self.viewPorts.append(OscOut(ipAddress, port))   # configure OSC Out port and add to list of ports
            print "OSC Configured.  Sending messages to", ipAddress, "on", port
         except Exception, e:
            print e
            sys.exit(1)


   ####################################
   ###### Calibration Process #########
   ####################################


   def calibrationStart(self):

      # start calibrating
      self.calibrating = True

      # remove initial instructions
      self.display.remove(self.instructions)

      # add label for instructions
      self.instructionsLine1 = self.display.drawLabel("Zig-Zag through the room for the system to find", 20, 175, Color.WHITE)
      self.instructionsLine2 = self.display.drawLabel("the space that it can sense (the light will be green).", 20, 200, Color.WHITE)
      self.instructionsLine3 = self.display.drawLabel("Select Calibrate > Stop when done.", 20, 225, Color.WHITE)

      # Get calibrators ready (calibration data will be relayed through the handleUserData method)
      for calSet in self.calibrators:
         calibrator = calSet[0]
         isActiveCheckbox = calSet[1]
         if isActiveCheckbox.isChecked():
            calibrator.calibrationStart()


   def calibrationStop(self):
      ''' Callback function for the Menu Item, Stop.  Stops the Calbration process
          and sends the updated information to the server '''

      # stop calibrating
      self.calibrating = False

      # now that we are done remove labels
      self.display.remove(self.instructionsLine1)
      self.display.remove(self.instructionsLine2)
      self.display.remove(self.instructionsLine3)

      self.display.setColor(Color.BLACK)  # set background to black since we are no longer calibrating

      # stop calibrators
      for calSet in self.calibrators:
         calibrator = calSet[0]
         isActiveCheckbox = calSet[1]
         if isActiveCheckbox.isChecked():
            data = calibrator.calibrationStop()                     # stop calibrator (returns final calibration data)
            clientID = self.devices[self.calibrators.index(calSet)] # get clientID
            self.calibrateDevice(data, clientID)                    # store calibration data to server

         self.instructions = self.display.drawLabel("Calibration complete and data saved", 20, 200, Color.WHITE)


   def calibrateDevice(self, data, clientID):
      '''Updates calibration data from calibrators so the Kuatro Server can
         normalize client data to Virtual World Coordinates.
         'data' should contain the following values:
               minX, minY, minZ, maxX, maxY, maxZ
      '''

      # parse arguments from data array
      minX = data[0]
      minY = data[1]
      minZ = data[2]
      maxX = data[3]
      maxY = data[4]
      maxZ = data[5]

      self.deviceCalibrationData[clientID] = (minX, minY, minZ, maxX, maxY, maxZ)


      if self.verbose !=0:
         print "Device", clientID, "calibrated"
         print minX, minY, minZ, maxX, maxY, maxZ
         print "-----------------------------------"



   #####################################
   ###### Kuatro Helper Functions ######
   #####################################


   def calibrateUserCoordinates(self, x, y, z, clientID):
      '''Takes User Coordinate data from a device and translates it to Virtual World
         coordinates'''

      ### Get Coordination Data ###
      minX = self.deviceCalibrationData[clientID][0]
      minY = self.deviceCalibrationData[clientID][1]
      minZ = self.deviceCalibrationData[clientID][2]
      maxX = self.deviceCalibrationData[clientID][3]
      maxY = self.deviceCalibrationData[clientID][4]
      maxZ = self.deviceCalibrationData[clientID][5]


      # Now calibrate the input values

      x = max(x, minX)   # keep x in range
      x = min(x, maxX)
      #print x,y,minX,maxX
      newX = mapValue(x, minX, maxX, 0, self.virtualMaxX)  # find the normalized value of X

      y = max(y, minY)   # keep y in range
      y = min(y, maxY)
      newY = mapValue(y, minY, maxY, 0, self.virtualMaxY)  # find the normalized value of Y

      z = max(z, minZ)   # keep z in range
      z = min(z, maxZ)
      newZ = mapValue(z, minZ, maxZ, 0, self.virtualMaxZ)  # find the normalized value of Z

      return newX, newY, newZ

#####################################

   def visualize(self, message):
      args = message.getArguments()
      print args
      userID = args[0]        # which user (should be a known user)
      x = args[1]
      y = args[2]
      self.sendMessage(KuatroServer.PROCESSING_MESSAGE, userID, x,y)


#####################################

   def resetLight(self, light):
      '''Resets a client's light to GRAY'''
      light.setColor(Color.GRAY)


   def sendMessage(self, address, *args):
      '''Helper method to send OSC messages using OSC Out port.
         *args allows calling method to send any number of parameters'''


      if len(self.viewPorts) > 0:      # make sure at least one oscOut port is setup

         for oscOut in self.viewPorts:  # loop through all osc ports
            oscOut.sendMessage(address, *args)  # send osc message through osc port
            if self.verbose !=0:
               print "Sending message to:", address
               print "Data:", args

      else:
         print "No OSC out ports are setup"


##### Instantiate a Server
if __name__ == '__main__':
   kuatroServer = KuatroServer(verbose=1)
