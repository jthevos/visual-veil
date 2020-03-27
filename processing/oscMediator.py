# run it with: java -jar processing/processing-py.jar processing/oscMediator.py

import random
from math import *

add_library('oscP5')
import netP5
import oscP5


osc = None
remote = None


def setup():
   global osc, remote

   size(700,700)
   osc = oscP5.OscP5(this, 57111)
   remote = netP5.NetAddress("127.0.0.1",13000)

def draw():
    global osc, remote
    background(0)
    fill(255)
    ellipse(mouseX, mouseY, 100, 100)
    fill(0)
    text("test processing pure", mouseX - 40, mouseY)

    message = oscP5.OscMessage("/test")
    message.add(mouseX)
    message.add(mouseY)
    print message
    print osc
    osc.send(message, remote)
