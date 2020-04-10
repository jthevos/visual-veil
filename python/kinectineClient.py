# kuatroKinectClient.py       Version 1.0     13-Aug-2014
#     David Johnson, Bill Manaris, and Seth Stoudenmier
#
# The Kuatro Client tracks the x, y, z coordinates of mulitple users
# within range of a configured depth sensor.  The coordinates are sent via OSC messages
# to the Kuatro Server for coordination within a Virtual World, as defined by the server.
#
#  Supported Controllers for the Kuatro Client are Microsoft Kinect, model 1414,
#  and the Asus Xtion Pro.
#
#  See README file for full instructions on using the Kuatro System


from pythonosc import udp_client
from pykinect2 import PyKinectV2
from pykinect2.PyKinectV2 import *
from pykinect2 import PyKinectRuntime
from jointConstants import *

from threading import *
from time import sleep

import sys
import pickle
import socket

# how often to get data from the Kinect (frames per second)
# (increase to get data more often, but this slows down the system)
FRAME_RATE = 30

# which body joints to pull position data for (including a hand will send that hand's state as well)
# choose from: SPINE_BASE, SPINE_MID, NECK, HEAD, SHOULDER_LEFT, ELBOW_LEFT, WRIST_LEFT, HAND_LEFT, SHOULDER_RIGHT, ELBOW_RIGHT, WRIST_RIGHT,
# HAND_RIGHT, HIP_LEFT, KNEE_LEFT, ANKLE_LEFT, FOOT_LEFT, HIP_RIGHT, KNEE_RIGHT, ANKLE_RIGHT, FOOT_RIGHT, SPINE_SHOULDER, HAND_TIP_LEFT,
# THUMB_LEFT, HAND_TIP_RIGHT, THUMB_RIGHT
JOINTS_LIST = [SPINE_BASE, SHOULDER_LEFT, ELBOW_LEFT, HAND_LEFT, SHOULDER_RIGHT, ELBOW_RIGHT, HAND_RIGHT]

#JOINTS_LIST = [HAND_LEFT]

SERVER_IP_ADDRESS = "localhost"
EXTERNAL_IP_ADDRESS = "10.5.170.229"
EXTERNAL_IP_ADDRESS = "10.5.194.25"
EXTERNAL_PORT = 57111

class KuatroKinectClient():

    ##### OSC Namespace #####
    NEW_USER_MESSAGE = "/kuatro/newUser"
    LOST_USER_MESSAGE = "/kuatro/lostUser"
    JOINT_COORDINATES_MESSAGE = "/kuatro/jointCoordinates"
    HAND_STATE_MESSAGE = "/kuatro/handState"
    REGISTER_DEVICE_MESSAGE = "/kuatro/registerDevice"
    CALIBRATE_DEVICE_MESSAGE = "/kuatro/calibrateDevice"
    PROCESSING_MESSAGE = "/kuatro/processing"

    def __init__(self, serverIpAddress=SERVER_IP_ADDRESS, serverPort=50505):
    #def __init__(self, serverIpAddress=EXTERNAL_IP_ADDRESS, serverPort=EXTERNAL_PORT):

        self.clientID = socket.gethostbyname(socket.getfqdn())  # find the computer's IP Address to use as unique ID of this device used by Kuatro Server
        self.users = None  # list of users being tracked by this device

        self.isRunning = True  # value is set to false to turn off the thread that is running the Kinect

        self.configureKinect()  # configure and start the Kinect


        # initiate Timer variable
        self.timer = None
        # once Kinect is started and display is setup, establish connection to server and register the client with the Kuatro Server
        self.oscServer =  udp_client.SimpleUDPClient(serverIpAddress, serverPort)  # setup the OSC Connection to the Kuatro Server
        self.oscServer.send_message(KuatroKinectClient.REGISTER_DEVICE_MESSAGE, self.clientID)  # and now send message to register client with server

        # send identical messages to another destination
        #self.twinOscServer =  udp_client.SimpleUDPClient(EXTERNAL_IP_ADDRESS, EXTERNAL_PORT)  # setup the OSC Connection to the Kuatro Server
        #self.twinOscServer.send_message(KuatroKinectClient.REGISTER_DEVICE_MESSAGE, self.clientID)  # and now send message to register client with server

        # now its registered, calibrate the device with server
        # sends defaults, only use if Calibrators not working
        ##self.calibrateWithServer()

    ##############################
    ###### Event Functions #######
    ##############################

    def addUser(self, userID, x, y, z):
        ''' Adds a new user to the Client when a new user is detected by the Kinect.
          Send the corresponding OSC Message to the Kuatro Server '''

        self.was_tracked[userID] = True # we now know this body has been tracked
        self.oscServer.send_message(KuatroKinectClient.NEW_USER_MESSAGE, [userID, x, y, z, self.clientID])  # tell the server we found a new user

    def removeUser(self, userID):
        ''' Removes a user from the Client when a lost user is detected by the Kinect.
          Send the corresponding OSC message to the Kuatro Server '''

        self.was_tracked[userID] = False  # we lost tracking on this user
        self.oscServer.send_message(KuatroKinectClient.LOST_USER_MESSAGE, [userID, self.clientID])  # tell the server we lost this user

    def sendAllUserCoords(self):
        ''' Sends all user coordinates via OSC Messages to the Kuatro Server.
          This happens for each Kuatro Frame '''

        for userID in range(0, self.kinect.max_body_count):  # for all users
            body = self.users.bodies[userID]  # get the body
            if body.is_tracked:  # if it is being tracked

                joints = body.joints  # get the body's joint set
                for jointID in JOINTS_LIST: # iterate through the JOINTS_LIST, defined at the top of this file
                    joint = joints[jointID]  # get the joint
                    # break it down into X, Y, Z coordinate values (originally measured in meters, we change to millimeters)
                    x, y, z = joint.Position.x * 1000, joint.Position.y * 1000, joint.Position.z * 1000
                    trackingState = joint.TrackingState # returns 0 if not tracked, 1 if inferred, 2 if tracked

                    # if the joint is a HAND joint, send that hand's current state (unknown = 0, not tracked = 1, open = 2, closed = 3, lasso = 4)
                    if jointID is HAND_LEFT:
                        leftHandState = body.hand_left_state
                        self.oscServer.send_message(KuatroKinectClient.HAND_STATE_MESSAGE, [userID, "left", leftHandState, self.clientID])
                        #self.oscServer.send_message(KuatroKinectClient.PROCESSING_MESSAGE, [userID, x, y, self.clientID])

                    if jointID is HAND_RIGHT:
                        rightHandState = body.hand_right_state
                        self.oscServer.send_message(KuatroKinectClient.HAND_STATE_MESSAGE, [userID, "right", rightHandState, self.clientID])

                    # this logic allows BasicView to work, but should probably be changed (should we include coordinate data with user lost/found?)
                    if jointID is SPINE_BASE:
                        if not self.was_tracked[userID]:  # and if the body wasn't already being tracked
                            self.addUser(userID, x, y, z)  # we found a new user
                            self.was_tracked[userID] = True # we now know this body has been tracked

                    # coordinates of 0, 0, 0 means user is temporarily lost
                    # reduce OSC messages by not sending if all 3 are 0
                    if x != 0 or y != 0 or z != 0:
                        self.oscServer.send_message(KuatroKinectClient.JOINT_COORDINATES_MESSAGE,
                                                    [userID, jointID, x, y, z, trackingState, self.clientID])  # and send it to the Server
                        ## print ("User:", userID, "location", x, y, z)

            else:
                if self.was_tracked[userID]:  # if the user is not being tracked but was before
                    self.removeUser(userID)  # we lost a user


    ####################################
    ###### Calibration Process #########
    ####################################

    def calibrateWithServer(self):
        ''' Calibrate the device with the Kuatro Server by finding the
          minimum and maximum coordinate values that the device outputs '''

        # hard-coded placeholder values for calibration, only use if the Calibrator isn't working
        self.oscServer.send_message(KuatroKinectClient.CALIBRATE_DEVICE_MESSAGE, [self.clientID, -3000, -3000, 0, 3000, 3000, 3000])

    ####################################
    ######### Client Setup #############
    ####################################

    def configureKinect(self):
        '''Configure the Motion Sensing device with the PyKinect2
          framework protocols'''

        try:
            # Configuration per PyKinect2 framework settings:
            # To pull other types of Frames from the Kinect through PyKinect2, use
            # PyKinectRuntime.PyKinectRuntime(PyKinectV2.FrameSourceTypes_Body | PyKinectV2.FrameSourceTypes_Color | PyKinectV2.FrameSourceTypes_Infrared)
            # formatting. The possible FrameSourceTypes are enumerated in PyKinectV2.py

            self.kinect = PyKinectRuntime.PyKinectRuntime(PyKinectV2.FrameSourceTypes_Body)

            # create list of booleans to say if a body WAS tracked, instantiate all to False
            self.was_tracked = []
            for i in range(0, self.kinect.max_body_count):
                self.was_tracked.append(False)

            # setup thread to run Device
            self.clientThread = Thread(target=self.run)

            self.start()
            print("Kuatro Device Configured and Started")

        except Exception as e:
            print("Something went wrong.  Device not started.")
            print(e)
            sys.exit(1)

    def run(self):
        '''Start the Client via a separate thread '''

        while self.isRunning:  # is the Kinect Running?

            try:
                if self.kinect.has_new_body_frame():  # then is there a new BodyFrame?
                    self.users = self.kinect.get_last_body_frame() # get the BodyFrame data

                if self.users is not None:  # if we have BodyFrame data (at least once)
                    self.sendAllUserCoords()  # and send all coordinate values
                # raise StatusException()
            except Exception as errorStack:
                print(errorStack)
                sys.exit(1)

            # let's sleep until it's time to grab the next frame of data
            sleep( 1.0/FRAME_RATE )

    def start(self):
        ''' Start the Kinect tracking '''

        self.isRunning = True
        self.clientThread.start()

    def stop(self):
        ''' Stop the Kinect tracking '''

        self.isRunning = False


if __name__ == '__main__':
    kinectClient = KuatroKinectClient()  # Create and start the Kinect Client
