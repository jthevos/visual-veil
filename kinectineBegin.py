# kuatroBegin.py
# 
# This file starts all the components of the Kuatro.  
# To start up the Kuatro:
#     1. Open a Terminal
#     2. cd to the Kuatro directory.  eg.  cd Dropbox/kuatro
#     3. Issue the following command:  sh jython.sh kuatroBegin.py


from kinectineServer import * 
from kinectine9 import *

#####  Start the Server
server = KuatroServer(verbose = 0)

##### Start the Client
#import kuatroMouseClient
# kinectClient = KuatroKinectClient() # Requires that a Kinect is connected to the computer.

##### Start the View
view = Kinectine()

# wait 5 seconds for server to start properly before starting client
#from time import sleep
#sleep(5)

##### Now, also start the CPython client
#from subprocess import call
#call(["python", "kuatroKinectClientv2PYTHON.py"])

import os
# os.system("python kuatroKinectClientv2PYTHON.py")
