/*
This file takes from:
1. VISUAL SHADER JS LIB HERE
2. p5 processing OSC here

*/


const MAX_PARTICLE_COUNT = 70;
const MAX_TRAIL_COUNT = 30;

// we need a handle to the socket to send our osc values
var socket;
var isConnected;

// globals
var shaded = true;
var theShader;
var shaderTexture;

// empty list to hold each user's particle systems
let particleSystems = [];

// actual particle class
function Particle(x, y, vx, vy) {
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

class ParticleSystem {
	constructor(colorScheme) {
		this.colorScheme = colorScheme;
		this.trail = [];
		this.particles = [];

		//["#E69F66", "#DF843A", "#D8690F", "#B1560D", "#8A430A"];
	}

	serializeParticles() {

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
	setupOsc(57111, 57110);


	colors = ["#E69F66", "#DF843A", "#D8690F", "#B1560D", "#8A430A"];
	colors2 = ["#ff3377", "#ff5533", "#ffbb33", "#ddff33", "#77ff33"];

	p = new ParticleSystem(colors);
	p2 = new ParticleSystem(colors2);
	particleSystems.push(p);
	particleSystems.push(p2);


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
				//particleSystems[i].particles.push(new Particle(mouse.x, mouse.y, pmouseX, pmouseY ));
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
			// Display points.
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

// OSC stuff

function receiveOsc(address, value) {
	console.log("received OSC: " + address + ", " + value);
}

function sendOsc(address, value) {
	socket.emit('message', [address, value]);
}

function setupOsc(oscPortIn, oscPortOut) {
	socket = io.connect('http://127.0.0.1:8081', { port: 8081, rememberTransport: false });
	socket.on('connect', function() {
		socket.emit('config', {
			server: { port: oscPortIn,  host: '127.0.0.1'},
			client: { port: oscPortOut, host: '127.0.0.1'}
		});
	});
	socket.on('connect', function() {
		isConnected = true;
	});
	socket.on('message', function(msg) {
		if (msg[0] == '#bundle') {
			for (var i=2; i<msg.length; i++) {
				receiveOsc(msg[i][0], msg[i].splice(1));
			}
		} else {
			receiveOsc(msg[0], msg.splice(1));
		}
	});
}
