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
   #oscDev()
   pass


def mapValue(value, minValue, maxValue, minResultValue, maxResultValue):
   """
   Maps value from a given source range, i.e., (minValue, maxValue),
   to a new destination range, i.e., (minResultValue, maxResultValue).
   The result will be converted to the result data type (int, or float).
   """
   # check if value is within the specified range
   if value < minValue or value > maxValue:
      raise ValueError("value, " + str(value) + ", is outside the specified range, " \
                                 + str(minValue) + " to " + str(maxValue) + ".")

   # we are OK, so let's map
   value = float(value)  # ensure we are using float (for accuracy)
   normal = (value - minValue) / (maxValue - minValue)   # normalize source value

   # map to destination range
   result = normal * (maxResultValue - minResultValue) + minResultValue

   destinationType = type(minResultValue)  # find expected result data type
   result = destinationType(result)        # and apply it

   return result


def oscEvent(message):
   global osc, remote

   if(message.addrPattern() == "/kuatro/processing" and message.typetag() == "ff"):
      # checking both, the address pattern and the typetag,
      # guarantees safe value parsing and data transfer.
      # if the value at index 0 is not of type int, oscP5 will thrown
      # an error message of type java.lang.reflect.InvocationTargetException
      rawX = abs(int(message.get(0).floatValue()))
      rawY = abs(int(message.get(1).floatValue()))

      x = mapValue(x, 100, 700, 1900, 0 )
      y = mapValue(y, 100, 700, 0, 1000)

      msg = oscP5.OscMessage("/kuatro/processing/mediated")
      msg.add(x)
      msg.add(y)
      osc.send(msg, remote)

   elif message.typetag() == "si":
      print "in weird string int land again..."
      print "string part == ", message.get(0)
      print "int part ==", message.get(1)
   else:
      print "idk man, but something is wrong."
      print "addrPattern ==", message.addrPattern()
      print "typeTag ==", message.typetag()



def oscDev():
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
