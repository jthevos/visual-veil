# kuatroBegin.py
# 
# This file starts all the components of the Kuatro.  
# To start up the Kuatro:
#     1. Open a Terminal
#     2. cd to the Kuatro directory.  eg.  cd Dropbox/kuatro
#     3. Issue the following command:  sh jython.sh kuatroBegin.py


from kinectineServer import * 
from kinectine import *

#####  Start the Server
server = KuatroServer(verbose = 0)

##### Start the View
view = Kinectine()

