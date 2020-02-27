# kinectine8.py (was clementine.py)
#
# Demonstrates how to create a musical instrument using a Kinect and the Kuatro.
#
# NOTE:This implements Tim's recommendations:
#
# * User 0
#
#      Left hand  - timbre Vibraphone, scale diatonic, range C3-C4, rate 1 note / sec
#
#      Right hand - timbre Vibraphone, scale diatonic, range C3-C4, rate 1 note / sec 
#
# This instrument generates individual notes in succession based on
# a user's hand orientation in 3D space. Each note is visually accompanied by
# a color circle drawn on a display.
#
# * Pitch - height of user's hand relative to the shoulder.
#   The higher the hand, the higher the pitch.
#
# * Play notes - distance of hand from center (spine).
#
# Visually, you get one circle per note. The circle size (radius)
# corresponds to note volume (the louder the note, the larger the
# circle). Circle color corresponds to note pitch (the lower the
# pitch, the darker the color, the higher the pitch the brighter the color).
#
 
from gui import *
from random import *
from music import *
from osc import *
from time import time

import math

# Kinect parameters
FRAMES_PER_SEC = 30     # Kinect's frame rate (used in speed calculation)
MAX_HAND_SPEED = 3000   # we filter anything higher

SPINE_BASE  = 0         # Kinect joint ID constants
SHOULDER_LEFT = 4
ELBOW_LEFT  = 5
HAND_LEFT   = 7
SHOULDER_RIGHT = 8
ELBOW_RIGHT = 9
HAND_RIGHT  = 11

NOTE_DISTANCE_TRIGGER = 20  # how far to move hand away from body to start notes (20 cm)

# music parameters
Play.setInstrument(VIBRAPHONE)   # set instrument

SCALE       = MAJOR_SCALE        # scale used by instrument
MIN_RANGE   = C2                 # lowest note 
MAX_RANGE   = C4                 # highest note
DELAY_LEFT  = 1.0                # play one note per this many secs
DELAY_RIGHT = 0.5                # play one note per this many secs

MIN_VOLUME = 50           # loudness range
MAX_VOLUME = 127
MAX_NOTE_DURATION = 3000  # length of notes (in milliseconds, i.e., 3 secs)

# color and graphics parameters
MIN_CIRCLE = 5            # smallest circle radius
MAX_CIRCLE = 80           # largest circle radius

BLACK      = [0, 0, 0]
CLEMENTINE = [255, 146, 40]
WHITE      = [255, 255, 255]

CLEMENTINE_GRADIENT = colorGradient(BLACK, CLEMENTINE, 126/2) + colorGradient(CLEMENTINE, WHITE, 126/2) + [WHITE]




#################################################
# Instrument class
#################################################

class Kinectine():

   ##### OSC Namespace ######
   NEW_USER_MESSAGE = "/kuatro/newUser"
   LOST_USER_MESSAGE = "/kuatro/lostUser"
   JOINT_COORDINATES_MESSAGE = "/kuatro/jointCoordinates"
   HAND_STATE_MESSAGE = "/kuatro/handState"
   REGISTER_VIEW_MESSAGE = "/kuatro/registerView"
   PROCESSING_MESSAGE = "/kuatro/processing"

   def __init__(self, incomingPort = 60606, kuatroServerIP = "localhost", kuatroServerOscPort = 50505, processingOscPort = 57111):
   
      # parameters
      self.leftSpeed = 0     # speed of left hand
      self.rightSpeed = 0    # speed of right hand
      self.leftPitch = 0     # left hand pitch
      self.rightPitch = 0    # right hand pitch
      
      ##### create main display #####
      self.display = Display("Clementine Circles", 1000, 800)
      #self.display.hide()

      # dictionary of Kinectine users 
      # (key is a userID (as returned by Kinect), value is a KinectineUser object)
      self.kinectineUsers = {}


      ######### Server-to-View API ############
      try:
         print "Trying on port:", incomingPort
         oscIn = OscIn(incomingPort)
         oscIn.hideMessages()   #***

         #oscIn.onInput("/.*", self.echoMessage)
         oscIn.onInput(Kinectine.NEW_USER_MESSAGE, self.addUser)
         oscIn.onInput(Kinectine.LOST_USER_MESSAGE, self.removeUser)
         oscIn.onInput(Kinectine.HAND_STATE_MESSAGE, self.makeMusic)
         oscIn.onInput(Kinectine.PROCESSING_MESSAGE, self.visualizeWithProcessing)
         oscIn.onInput(Kinectine.JOINT_COORDINATES_MESSAGE, self.updateJoints)

      except:
         print "Error:  Unable to setup OSC In port. Port may already be in use."


      ####### Register View with Server ######

      # ipAddress = socket.gethostbyname(socket.getfqdn())   # find the computer's IP Address
      ipAddress = "localhost"

      # Setup OSC Out and send the message
      try:
         oscOut = OscOut(kuatroServerIP, kuatroServerOscPort)           # configure OSC Out port and add to list of ports
         print "OSC Out Configured.  Sending messages to", kuatroServerIP, "on", kuatroServerOscPort

         oscOut.sendMessage(Kinectine.REGISTER_VIEW_MESSAGE, ipAddress, incomingPort)         # send osc message through osc port
         print "\nSent message to:", kuatroServerIP
         print "  Data:", ipAddress, incomingPort

      except Exception, e:
         print e
         sys.exit(1)

      # Setup OSC Out and send the message to PROCESSING
      try:
         self.oscOutProcessing = OscOut(kuatroServerIP, processingOscPort)           # configure OSC Out port and add to list of ports
         print "OSC Out Configured.  Sending messages to", kuatroServerIP, "on", kuatroServerOscPort

         #self.oscOutProcessing.sendMessage(Kinectine.PROCESSING_MESSAGE, ipAddress, incomingPort)         # send osc message through osc port
         print "\nSent message to:", kuatroServerIP
         print "  Data:", ipAddress, incomingPort

      except Exception, e:
         print e
         sys.exit(1)
      
      print "Kinectine set up!"

   #####################################
   ###### Kuatro View Callbacks ######
   #####################################

   # These methods coordinate user data input from the view into
   # coordinates consistent with the virutal world
   
   def echoMessage(self, message):
      '''Simply prints OSC address and arguments'''

      address = message.getAddress()
      args = message.getArguments()

      print "\nKuatro View - OSC Event:"
      print "OSC In - Address:", address,
      for i in range(len(args)):
         print ",Argument " + str(i) + ": " + str(args[i]),
      print
 
   def addUser(self, message):
      ''' Callback function for NEW USER messages.  Adds a new user to the view '''

      # parse arguments from OSC Message
      args = message.getArguments()
      userID = args[0]              # user ID
      x = args[1]                   # x coordinate of user's initial location (*** which point is this?)
      y = args[2]                   # y coordinate of user's initial location
      z = args[3]                   # z coordinate of user's initial location

      # add user to known users
      if userID not in self.kinectineUsers.keys():  # is this a new user? (avoid duplicates)

         # yes, so add a new entry
         self.kinectineUsers[ userID ] = KinectineUser( x, y, z, self.display )

         print "Added User:", userID, "Location:", x, y, z

         
   def removeUser(self, message):
      ''' Callback function for LOST USER messages.  Removes the specified user from the view '''

      # parse arguments from OSC Message
      args = message.getArguments()
      userID = args[0]

      # remove user from known users
      if userID in self.kinectineUsers.keys():  # is this an existing user? 

         # yes, so remove them
         del self.kinectineUsers[ userID ]

         print "Removed User:", userID


   # callback function for HAND_STATE_MESSAGE
   def makeMusic(self, message):
      """Allows a particular user to generate music."""

      # parse arguments from the OSC message.
      args = message.getArguments()
      userID = args[0]        # which user (should be a known user)
      hand = args[1]          # hand ("left" or "right")
      handState = args[2]     # hand state (0 for unknown, 1 for not tracked, 2 for open, 3 for closed, 4 for lasso)

      
      if userID in self.kinectineUsers.keys():  # is this an existing user? 

         # pass hand and handState to corresponding KinectineUser object 
         # so that it can interpret what these may mean
         # (i.e., implement semantics of gestural language there, not here!)
         self.kinectineUsers[ userID ].makeMusic( hand, handState )

   #################################################################################

   def visualizeWithProcessing(self, message):
      args = message.getArguments()
      #print args
      userID = args[0]        # which user (should be a known user)
      x = args[1]
      y = args[2]

      
      if userID in self.kinectineUsers.keys():  # is this an existing user? 

         # let corresponding KinectineUser object handle things
         #self.kinectineUsers[ userID ].updateJoints( jointID, x, y, z )
         
         self.oscOutProcessing.sendMessage(Kinectine.PROCESSING_MESSAGE, x,y)
   #################################################################################

         
   # callback function for JOINT_COORDINATES_MESSAGE
   def updateJoints(self, message):
      """Updates a particular user's joint data."""

      # parse arguments from the OSC message.
      args = message.getArguments()
      userID = args[0]       
      jointID = args[1] 
      trackingState = args[2]
      x = args[3]
      y = args[4]
      z = args[5]

      if userID in self.kinectineUsers.keys():  # is this an existing user? 

         # let corresponding KinectineUser object handle things
         self.kinectineUsers[ userID ].updateJoints( jointID, x, y, z )
         


#################################################
# User class - instrument supports multiple users
#################################################

class KinectineUser():
   """Encapsulates data and actions for a single, unique Kinectine user."""

   def __init__(self, initialX, initialY, initialZ, display):

      # holds user joint data
      self.jointData = {}    


# ***
# * Pitch - height of user's hand relative to the shoulder.
#   The higher the hand, the higher the pitch.
#
# * Play notes - distance of hand from center (spine).

      # initialize joint data to user's initial x, y, z, location (will be updated when joint data arrive)
      self.jointData[SPINE_BASE]     = [initialX, initialY, initialZ]
      self.jointData[SHOULDER_LEFT]  = [initialX, initialY, initialZ]
      self.jointData[ELBOW_LEFT]     = [initialX, initialY, initialZ]
      self.jointData[HAND_LEFT]      = [initialX, initialY, initialZ]
      self.jointData[SHOULDER_RIGHT] = [initialX, initialY, initialZ]
      self.jointData[ELBOW_RIGHT]    = [initialX, initialY, initialZ]
      self.jointData[HAND_RIGHT]     = [initialX, initialY, initialZ]      

      # hold speed and pitch (low to high) of left and right hands
      self.leftSpeed  = 1   # a small speed
      self.rightSpeed = 1
      self.leftPitch  = 3   # a small pitch
      self.rightPitch = 3

      # holds list of last few points (to be used in calculating speed)
      #self.lastFewPointsLeft  = []
      #self.lastFewPointsRight = []
      #self.windowSize         = 6   # how many points to remember

      # remember display to draw circles on
      self.display = display

      # helper variables for implementing note rate
      self.leftHandNoteStartTime  = 0  # holds timestamp when last note was played for left hand
      self.rightHandNoteStartTime = 0  # holds timestamp when last note was played for right hand
      

      # implement rate - here 1 note per second.
      # (the idea is to set a flag when a note is played, and wait until the proper time has passed
      # before we play another note)
      #self.soundOn = False   # do not play more notes just yet...

      # callback function for timer - essentially, when called, it allows playing of notes again
      #def resetSoundOnFlag():
      #   self.soundOn = True   # time to play more notes...

      # define timer and start it (it allows playing a note once per delay millisecs
      #delay = 1000   # millisecs
      #self.soundRateTimer = Timer(delay, resetSoundOnFlag, [], True)
      #self.soundRateTimer.start()  


   def updateJoints(self, jointID, x, y, z):
      """Updates user's joint positions."""

      # NOTE: First time around, calculation of speed and pitch of hands will produce
      # non-sensical values, but we ignore that (for simplicity of code below)...
      
      # update the corresponding joint's position 
      self.jointData[ jointID ] = [x, y, z]

      # calculate left hand speed (if needed)
      if jointID == HAND_LEFT:

         # update last few points
         #if len(self.lastFewPointsLeft) >= self.windowSize:  # is list full?
         #   self.lastFewPointsLeft.pop(0)                    # remove oldest point

         # add latest point
         #self.lastFewPointsLeft.append( [x, y, z] )                
            
         # calculate speed (uses last few points)
         ##self.leftSpeed = self.setSpeed( self.lastFewPointsLeft )
         ##self.leftSpeed = min(self.leftSpeed, MAX_HAND_SPEED)   # filter out large speeds

         # calculate hand pitch
         self.leftPitch = self.setHandPitch( HAND_LEFT, SHOULDER_LEFT )

      elif jointID == HAND_RIGHT:
            
         # update last few points
         #if len(self.lastFewPointsRight) >= self.windowSize:  # is list full?
         #   self.lastFewPointsRight.pop(0)                    # remove oldest point

         # add latest point
         #self.lastFewPointsRight.append( [x, y, z] )                

         # calculate speed (uses last few points)
         ##self.rightSpeed = self.setSpeed( self.lastFewPointsRight )
         ##self.rightSpeed = min(self.rightSpeed, MAX_HAND_SPEED)   # filter out large speeds

         # calculate hand pitch
         self.rightPitch = self.setHandPitch( HAND_RIGHT, SHOULDER_RIGHT )


   def setSpeed(self, lastFewPoints):
      """ Calculates how fast the hand is moving, i.e., speed. """
      
      # calculate elapsed time between two Kinect frames (data captures)
      elaspedTime = 1.0 / FRAMES_PER_SEC      
   
      # calculate average distance travelled between last few points
      totalDiffX, totalDiffY, totalDiffZ = 0               # initialize difference accumulators
      previousX, previousY, previousZ = lastFewPoints[0]   # priming read     
      for currentX, currentY, currentZ in lastFewPoints[1:] :

         # calculate difference between two adjacent points
         diffX = currentX - previousX
         diffY = currentY - previousY
         diffZ = currentZ - previousZ

         # accumulate this difference
         totalDiffX = totalDiffX + diffX   
         totalDiffY = totalDiffY + diffY
         totalDiffZ = totalDiffZ + diffZ

         # grab next point
         previousX, previousY, previousZ = currentX, currentY, currentZ
         
      # now, all points have been accumulated
      # let's average them
      avgDiffX = totalDiffX / len(lastFewPoints)
      avgDiffY = totalDiffY / len(lastFewPoints)
      avgDiffZ = totalDiffZ / len(lastFewPoints)
         
      # calculate Euclidean distance between the two points
      distanceTraveled = math.sqrt( avgDiffX**2 + avgDiffY**2 + avgDiffZ**2 )

      # calculate speed
      speed = distanceTraveled / elaspedTime
         
      return speed
   

   def setHandPitch(self, hand, joint):
      """Calculates the pitch (low to high) of user's hand, based on two points"""
      
      handX, handY, handZ    = self.jointData[hand]
      jointX, jointY, jointZ = self.jointData[joint]

      #***
      #print "setHandPitch():"
      #print "   handX, handY, handZ =", handX, handY, handZ
      #print "   jointX, jointY, jointZ =", jointX, jointY, jointZ
         
      dX = handX - jointX
      dY = handY - jointY
      dZ = handZ - jointZ
         
      # find the angle of the user's arm (elbow to hand)
      pitch = math.atan2(math.sqrt(dZ * dZ + dX * dX), dY) + math.pi   

      return pitch
 
   
   def makeMusic(self, hand, handState ):
      """Plays notes / draws circles whenever a hand is extended beyond a certain distance."""

      # we make music only if hand is open
      #if handState == 2:           # is hand open?

      # yes, so decide which hand we are using
      if hand == "left":        # is this the left hand?

        # yes, so use corresponding pitch and depth
        pitch = self.leftPitch
        #depth = self.jointData[ HAND_LEFT ][2] # the Z value
        handZ = self.jointData[HAND_LEFT][2]
        spineZ = self.jointData[SPINE_BASE][2]
        depth = abs(handZ - spineZ)

        # ***
        #print depth 

        # ensure depth is under 1000 (1 meter)
        #depth = min(depth, 1000)

        # if hand has moved far enough (penetrated into the "veil" that separates), play a note
        if depth > NOTE_DISTANCE_TRIGGER:
           # implement note-playing rate for left hand
           now = time()
           if now - self.leftHandNoteStartTime > DELAY_LEFT:   # time to play?
              self.leftHandNoteStartTime = now   # reset elapsed time

              # now generate corresponding notes and circles
              self.drawCircle( pitch, depth )

      # or, is it the right
      elif hand == "right":     # is this the right hand?

        # yes, so use corresponding pitch and depth
        pitch = self.rightPitch
        #depth = self.jointData[ HAND_RIGHT ][2] # the Z value
        handZ = self.jointData[HAND_RIGHT][2]
        spineZ = self.jointData[SPINE_BASE][2]
        depth = abs(handZ - spineZ)

        # if hand has moved far enough (penetrated into the "veil" that separates), play a note
        if depth > NOTE_DISTANCE_TRIGGER:
           # implement note-playing rate for right hand
           now = time()
           if now - self.rightHandNoteStartTime > DELAY_RIGHT:   # time to play?
              self.rightHandNoteStartTime = now   # reset elapsed time

              # now generate corresponding notes and circles
              self.drawCircle( pitch, depth )

 
   def drawCircle(self, handPitch, handDepth):
      """Draws one circle and plays the corresponding note."""
 
      # map hand pitch to note pitch
      #pitch = mapScale(handPitch*-100, -750, -250, 0, 127, SCALE)  # use scale
      pitch = mapScale(handPitch*-100, -750, -250, MIN_RANGE, MAX_RANGE, SCALE)  # use scale

      # *** Kyle, wouldn't this achieve the same thing?
      #pitch = mapScale(handPitch, 75, 25, 0, 127, SCALE)  # use scale

      # map hand speed to volume
      volume = mapValue(handDepth*-1, -1000, 0, MIN_VOLUME, MAX_VOLUME)
 
      # now create a circle in a random location
      x = randint(0, self.display.getWidth())               # random circle x position
      y = randint(0, self.display.getHeight())              # random circle y position
      radius = mapValue(volume, MIN_VOLUME, MAX_VOLUME, MIN_CIRCLE, MAX_CIRCLE)  # map volume to radius
 
      # create color based on provided gradient
      red, green, blue = CLEMENTINE_GRADIENT[pitch]
      color = Color(red, green, blue)
      c = Circle(x, y, radius, color, True)   # create filled circle
      self.display.add(c)                     # add it to display
      #self.display.removeAll()

      # yes, so play it
      Play.note(pitch, 0, MAX_NOTE_DURATION, volume)


