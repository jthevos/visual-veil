/*
This file takes from:
1. VISUAL SHADER JS LIB HERE
2. p5 processing OSC here

*/


const MAX_PARTICLE_COUNT = 70;
const MAX_TRAIL_COUNT = 30;

// we need a handle to the socket to send our osc values
let socket;
let isConnected;

// globals
let shaded = true;
let theShader;
let shaderTexture;

// empty list to hold each user's particle systems
let particleSystems = [];

class Particle {
	constructor(x, y, vx, vy) {
		this.pos = new p5.Vector(x, y);
		this.vel = new p5.Vector(vx, vy);
		this.vel.mult(random(10));
		this.vel.rotate(radians(random(-25, 25)));
		this.mass = random(1, 20);
		this.airDrag = random(0.92, 0.98);
		this.colorIndex = int(random(colorScheme.length));

		this.move = function() {
			this.vel.mult(this.airDrag);
			this.pos.add(this.vel);
		}
	}
}

class ParticleSystem {
	/*
	This class encapsulates a system of particles. We need this because
	we want this code to accomodate multiple concurrent users. Each user
	will control one instance of several particle systems.
	*/
	constructor(colorScheme) {
		this.colorScheme = colorScheme;
		this.trail = [];
		this.particles = [];

		//["#E69F66", "#DF843A", "#D8690F", "#B1560D", "#8A430A"];
	}

	serializeParticles() {
		/*
		We serialize a system's particles into a JSON object because
		each call of the draw() function must have all of this information
		in order to properly render. Using JSON here is appropriate because
		otherwise we would need three separate functions each returning
		one dimension of this three dimensional object.
		This function is called 30 times per second.
		*/
		let data = { "trails": [], "particles": [], "colors": [] };


		for (let i = 0; i < this.trail.length; i++) {
			data.trails.push(
				map(this.trail[i][0], 0, width, 0.0, 1.0),
				map(this.trail[i][1], 0, height, 1.0, 0.0));
		}

		for (let i = 0; i < this.particles.length; i++) {
			data.particles.push(
				map(this.particles[i].pos.x, 0, width, 0.0, 1.0),
				map(this.particles[i].pos.y, 0, height, 1.0, 0.0),
				this.particles[i].mass * this.particles[i].vel.mag() / 100)

			let itsColor = this.colorScheme[this.particles[i].colorIndex];
			data.colors.push(red(itsColor), green(itsColor), blue(itsColor));
		}

		return data;
	}

}


// java processing - need to look up why this is.
let vertShader = `
	precision highp float;

	attribute vec3 aPosition;

	void main() {
		vec4 positionVec4 = vec4(aPosition, 1.0);
		positionVec4.xy = positionVec4.xy * 2.0 - 1.0;
		gl_Position = positionVec4;
	}
`;

let fragShader = `
	precision highp float;

	uniform vec2 resolution;
	uniform int trailCount;
	uniform vec2 trail[${MAX_TRAIL_COUNT}];
	uniform int particleCount;
	uniform vec3 particles[${MAX_PARTICLE_COUNT}];
	uniform vec3 colors[${MAX_PARTICLE_COUNT}];

	void main() {
			vec2 st = gl_FragCoord.xy / resolution.xy;  // Warning! This is causing non-uniform scaling.

			float r = 0.0;
			float g = 0.0;
			float b = 0.0;

			for (int i = 0; i < ${MAX_TRAIL_COUNT}; i++) {
				if (i < trailCount) {
					vec2 trailPos = trail[i];
					float value = float(i) / distance(st, trailPos.xy) * 0.00015;  // Multiplier may need to be adjusted if max trail count is tweaked.
					g += value * 0.5;
					b += value;
				}
			}

			float mult = 0.00005;

			for (int i = 0; i < ${MAX_PARTICLE_COUNT}; i++) {
				if (i < particleCount) {
					vec3 particle = particles[i];
					vec2 pos = particle.xy;
					float mass = particle.z;
					vec3 color = colors[i];

					r += color.r / distance(st, pos) * mult * mass;
					g += color.g / distance(st, pos) * mult * mass;
					b += color.b / distance(st, pos) * mult * mass;
				}
			}

			gl_FragColor = vec4(r, g, b, 1.0);
	}
`;


var colorScheme = ["#E69F66", "#DF843A", "#D8690F", "#B1560D", "#8A430A"];
var trail = [];
var particles = [];

function preload() {
	theShader = new p5.Shader(this.renderer, vertShader, fragShader);
}

function setup() {
	pixelDensity(1);
	setupOsc(57111, 13000);

	colors = ["#E69F66", "#DF843A", "#D8690F", "#B1560D", "#8A430A"];

	p = new ParticleSystem(colors);
	particleSystems.push(p);

	// let canvas = createCanvas(
  	// 	min(windowWidth, windowHeight),
  	// 	min(windowWidth, windowHeight),
  	// 	WEBGL);

  let canvas = createCanvas(
		windowWidth,
		windowHeight,
		WEBGL);

	canvas.canvas.oncontextmenu = () => false;  // Removes right-click menu.

	shaderTexture = createGraphics(width, height, WEBGL);
	shaderTexture.noStroke();
}

function draw() {
	background(0);
	noStroke();

	translate(-width / 2, -height / 2);   // adjust for WEBGL's coordinate system

	generate();

}

function generate() {
	for (let i = 0; i < particleSystems.length; i++) {
		// Trim end of trail.
		particleSystems[i].trail.push([mouseX, mouseY]);

		let removeCount = 1;
		if (mouseIsPressed && mouseButton == CENTER) {
			removeCount++;
		}

		for (let j = 0; j < removeCount; j++) {
			if (particleSystems[i].trail.length == 0) {
				break;
			}

			if (mouseIsPressed || particleSystems[i].trail.length > MAX_TRAIL_COUNT) {
				particleSystems[i].trail.splice(0, 1);
			}
		}

		// Spawn particles.
		if (particleSystems[i].trail.length > 1 && particleSystems[i].particles.length < MAX_PARTICLE_COUNT) {
			let mouse = new p5.Vector(mouseX, mouseY);
			mouse.sub(pmouseX, pmouseY);
			if (mouse.mag() > 10) {
				mouse.normalize();
				particleSystems[i].particles.push(new Particle(pmouseX, pmouseY, mouse.x, mouse.y));
			}
		}

		// Move and kill particles.
		for (let j = particleSystems[i].particles.length - 1; j > -1; j--) {
			particleSystems[i].particles[j].move();
			if (particleSystems[i].particles[j].vel.mag() < 0.1) {
				particleSystems[i].particles.splice(j, 1);
			}
		}

		if (shaded) {
			// Display shader.
			shaderTexture.shader(theShader);

			let data = particleSystems[i].serializeParticles();

			theShader.setUniform("resolution", [width, height]);
			theShader.setUniform("trailCount", particleSystems[i].trail.length);
			theShader.setUniform("trail", data.trails);
			theShader.setUniform("particleCount", particleSystems[i].particles.length);
			theShader.setUniform("particles", data.particles);
			theShader.setUniform("colors", data.colors);

			shaderTexture.rect(0, 0, windowWidth, windowHeight);
			texture(shaderTexture);

			rect(0, 0,windowWidth, windowHeight);

		} else {
			// Display only points.
			stroke(255, 200, 0);
			for (let j = 0; j < particleSystems[i].particles.length; j++) {
				point(particleSystems[i].particles[j].pos.x, particleSystems[i].particles[j].pos.y);
			}

			stroke(0, 255, 255);
			for (let j = 0; j < particleSystems[i].trail.length; j++) {
				point(particleSystems[i].trail[j][0], particleSystems[i].trail[j][1]);
			}
		}
	}
}

function mousePressed() {
	if (mouseButton == RIGHT) {
		shaded = !shaded;
	}
}

function mapValue(value, min, max, minTarget, maxTarget) {
	if (value < min || value > max) {
		console.log('invalid range');
	} else {
		let normalizedValue = (value - min) / (max - min);
		let result = normalizedValue * (maxTarget - minTarget) + minTarget;
		return Math.trunc(result);
	}
}

// OSC

function receiveOsc(address, message) {
	/*
	This function handles the receipt of all OSC messages.
	It performs two important operations. First, it retreives
	the raw x and y coordinates from the Kinect. Second, it
	sanitizes these coordinates. Once sanitized, the x/y
	coordinates are sent to the view for display.
	*/

	console.log("received OSC: " + address + ", " + message);

	// if (address == '/kuatro/processing' && message.typeTag() == 'ff') {
	//
	// 	let rawX = abs(message.get(0).floatValue());
	// 	let rawY = abs(message.get(1).floatValue());
	//
	// 	let x = mapValue(rawX, 100, 700, 1900, 0);
	// 	let y = mapValue(rawY, 100, 700, 0, 1900);
	// }
}

function setupOsc(oscPortIn, oscPortOut) {
	console.log(oscPortIn, oscPortOut);
	socket = io.connect('http://127.0.0.1:8083', { port: 8083, rememberTransport: false });
	socket.on('connect', function() {
		socket.emit('config', {
			server: { port: 13000,  host: 'http://127.0.0.1'},
			client: { port: 57111, host: 'http://127.0.0.1'}
		});
	});
	socket.on('connect', function() {
		console.log("I AM CONNECTED");
		isConnected = true;
	});
	socket.on('message', function(msg) {
		console.log("in .on message");
		if (msg[0] == '#bundle') {
			for (var i=2; i<msg.length; i++) {
				receiveOsc(msg[i][0], msg[i].splice(1));
			}
		} else {
			receiveOsc(msg[0], msg.splice(1));
		}
	});
}
