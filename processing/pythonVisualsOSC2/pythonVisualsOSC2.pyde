# https://berinhard.github.io/pyp5js/


import random
from math import *

#add_library('oscP5')
#add_library('netP5')
import netP5
import oscP5


# config

MAX_PARTICLES = 170
#COLORS = [ '#31CFAD', '#ADDF8C', '#FF6500', '#FF0063', '#520042', '#DAF7A6' ];
COLORS = [ '#69D2E7', '#A7DBD8', '#E0E4CC', '#F38630', '#FA6900', '#FF4E50', '#F9D423' ]
#COLORS = [ '#581845', '#900C3F', '#C70039', '#C70039', '#FFC300', '#DAF7A6' ];
#COLORS = [ 'rgba(49,207,173,.7)', 'rgba(173,223,140,.7)', 'rgba(255,101,0,.7)', 'rgba(255,0,99,.7)', 'rgba(82,0,66,.7)' ];


particles = []
pool      = []

oscIn = None
listeningPort = None


wander1    = 0.5
wander2    = 2.0
drag1      = .9
drag2      = .99
force1     = 2
force2     = 8
theta1     = -0.5
theta2     = 0.5
size1      = 5
size2      = 180
sizeScalar = 0.97


class Particle():
   def __init__(self, x,y,size):
      import math   # for some reason I need to import math here...?
      self.alive = True
      self.size = size or 10
      self.wander = 0.15
      self.theta = random.uniform(0, 2 * math.pi)   # supply an angle between 0 and 2pi
      self.drag  = 0.92
      self.color = '#fff'
      self.location = PVector(x or 0.0, y or 0.0)   # create vector comes with p5
      self.velocity = PVector(0.0, 0.0)
      
   
   def move(self):
      import math
      self.location.add( self.velocity )
      self.velocity.mult( self.drag )
      self.theta  += random.uniform( theta1, theta2 ) * self. wander
      self.velocity.x += math.sin( self.theta ) * 0.1
      self.velocity.y += math.cos( self.theta ) * 0.1
      self.size *= sizeScalar
      self.alive = self.size > 0.5
   
   def show(self):
      fill( self.color )
      noStroke()
      ellipse( self.location.x, self.location.y, self.size, self.size )

def spawn(x,y):
   
   import math
   
   particle = None
   theta    = None
   force    = None
   
   # maintain list at max, and remove smallest (if at max)
   #if len(particles) >= MAX_PARTICLES:
   if len(particles) >= MAX_PARTICLES:
      #pool.append( particles.pop(0) )   # take first list element and add to end of array
      particles.pop(0)    # remove smallest list element
   
   particle = Particle( x, y, random.randint(size1, size2) )
   particle.wander = random.uniform( wander1, wander2 )
   particle.color  = random.choice( COLORS )
   particle.drag = random.uniform( drag1, drag2 )
   theta = random.uniform( 0.0, 2 * math.pi )
   force = random.randint( force1, force2 )
   particle.velocity.x = math.sin( theta ) * force
   particle.velocity.y = math.cos( theta ) * force
   
   # add new particle at end of list
   particles.append( particle )


def update():
   import traceback
   
   particle = None
   #for i in range(len(particles)-1, 0, -1):   # loop backwards from end
   for i in range(len(particles)-1, -1, -1):   # loop backwards from end
      particle = particles[i]
      if particle.alive:
         particle.move()
      else:
         # pool.push( particles.splice( i, 1 )[0] );
         # this is saying, take the element at position i in particles, removing it, and appending it to the end of pool array

        try:
            #pool.append( particles.pop(i) )
            particles.pop(i) 
        except:
            traceback.print_exc()
            #print sys.exc_info()[0]
            print "i out of bounds. i =", i, "len(particles) =", len(particles)

def moved(x,y):
   #print x,y
   particle = None
   maximum = random.randint(1,4)
   for i in range(maximum):
      #spawn( mouseX, mouseY )
      spawn(x,y)
   
def setup():
   global oscIn, listeningPort
   
   size(700,700)
   oscIn = oscP5.OscP5(this, 57111)
   listeningPort = netP5.NetAddress("10.5.194.25",57111)

def draw():
   update()
   #drawingContext.globalCompositeOperation = 'normal';
   background(0);
   #drawingContext.globalCompositeOperation = 'lighter';
   
   for i in range(len(particles) -1, 0, -1):
      try:
      #
         particles[i].show()
      except:
         print "len(particles) ==", len(particles), "i =", i

# def mouseMoved():
#    moved()

# def touchMoved():
#    moved()   

def oscEvent(message):
    
   ### Joint constants : LEFT_HAND = 7, HAND_RIGHT = 11
   ### how can I reliably get these? 
   print message.get(1).intValue(), message.get(2).intValue()
   # for i in range(len(message)):
   #     print "intValue = ", message.get(i).intValue()
   #     print "strValue = ", message.get(i).stringValue()
   moved(message.get(0).intValue(), message.get(1).intValue())
   
   
   
   
   
   
