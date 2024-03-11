import gc
import numpy as np
from threading import Thread

from wmzf.base.simtools import SimulationSaver, SimulationLoader, SimulationParser

# noinspection PyTypeChecker
class Particle:

    def __init__(self, mass, charge, r0, v0, s, steps):

        self.mass = mass
        self.charge = charge

        self.r0 = np.array(r0, dtype=float)
        self.v0 = np.array(v0, dtype=float)
        self.stationary = s
        self.steps = steps

        self.coefficient = self.charge/self.mass

        if not self.stationary:
            self.r = np.array(self.r0)
            self.v = np.array(self.v0)
            self.a = np.zeros(shape=(3,), dtype=float)

            self.trajectory = np.zeros(shape=(self.steps, 3), dtype=float)
            self.trajectory[0] = np.array(self.r0)
        else:
            self.r = self.r0
            self.trajectory = self.r0.reshape((1, 3))
        self.check()

    def __eq__(self, other):
        return other.mass == self.mass and other.charge == self.charge and other.stationary == self.stationary \
               and all(v for v in other.r0 == self.r0) and all(v for v in other.v0 == self.v0)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        keys = ("M", "C", "R", "V", "S")
        values = (str(self.mass), str(self.charge), str(list(self.r0)), str(list(self.v0)), str(int(self.stationary)))
        stringified = "PARTICLE "
        for i in range(5):
            stringified += keys[i] + ":" + values[i] + " "
        return stringified

    def check(self):
        self.setMass(self.mass)
        self.setCharge(self.charge)
        self.setInitialPosition(self.r0)
        self.setInitialVelocity(self.v0)
        self.is_stationary(self.stationary)
        self.setSteps(self.steps)

    def reset(self):
        if not self.stationary:
            self.r = np.array(self.r0)
            self.v = np.array(self.v0)
            self.a = np.zeros(shape=(3,), dtype=float)

            self.trajectory = np.zeros(shape=(self.steps, 3), dtype=float)
            self.trajectory[0] = np.array(self.r0)
        else:
            self.r = self.r0
            self.trajectory = self.r0.reshape((1, 3))

    def updateAcceleration(self, world, interactions):
        superposition = np.zeros(shape=(3,), dtype=float)
        for particle in world.getParticles():
            if interactions and particle is not self:
                superposition += particle.getField(self.r)
            superposition += world.getElectric().getVector()
            superposition += np.cross(self.v, world.getMagnetic().getVector())
        self.a = self.coefficient * superposition

    def updateVelocity(self, dt):
        self.v += self.a * dt / 2.0

    def updatePosition(self, dt, step):
        self.r += self.v * dt
        self.updateTrajectory(step)

    def updateTrajectory(self, step):
        self.trajectory[step] = self.r

    def getPoint(self, index: int):
        return self.trajectory[index * int(not self.stationary)]

    def getField(self, r):
        delta = r - self.r
        distance = np.linalg.norm(delta)
        return 8.9875 * 10e9 * self.charge * delta / (distance ** 3 + 10e-6)

    def getMass(self):
        return self.mass

    def setMass(self, mass):
        if mass <= 0:
            raise ValueError("Mass must be positive. (At least we think so at the moment!)")
        elif not isinstance(mass, (float, int)):
            raise TypeError("Mass must be a number.")
        else:
            self.mass = mass

    def getCharge(self):
        return self.charge

    def setCharge(self, charge):
        if not isinstance(charge, (float, int)):
            raise TypeError("Charge must be a number.")
        elif charge == 0:
            raise ValueError("Charge must be non-zero.")
        else:
            self.charge = charge

    def getInitialPosition(self):
        return self.r0

    def setInitialPosition(self, position):
        if not len(position) == 3:
            raise TypeError("Initial position vector must be 1x3.")
        elif not all(isinstance(value, (float, int)) for value in position):
            raise TypeError("Initial position vector must contain numbers.")
        else:
            self.r0 = np.array(position).astype(float)
            self.trajectory[0] = self.r0

    def getInitialVelocity(self):
        return self.v0

    def setInitialVelocity(self, velocity):
        if not len(velocity) == 3:
            raise TypeError("Initial position vector must be 1x3.")
        elif not all(isinstance(value, (float, int)) for value in velocity):
            raise TypeError("Initial position vector must contain numbers.")
        else:
            self.v0 = np.array(velocity).astype(float)

    def getTrajectory(self):
        return self.trajectory

    def is_stationary(self, stationary=None):
        if stationary is None:
            return self.stationary
        else:
            if not isinstance(stationary, bool):
                raise ValueError("'Stationary' flag must be a boolean.")
            else:
                self.stationary = stationary

    def setSteps(self, steps):
        self.steps = steps
        if not self.stationary:
            self.trajectory = np.zeros(shape=(self.steps, 3), dtype=float)
            self.trajectory[0] = np.array(self.r0)
        else:
            self.r = self.r0
            self.trajectory = self.r0.reshape((1, 3))

    def is_overlapping(self, other):
        return all(v for v in other.r0 == self.r0)


class Field:

    def __init__(self, x: float, y: float, z: float, field: str):
        self.check(x, y, z, field)

        self.field = np.array([x, y, z], dtype=float).reshape((3,))
        self.fieldtype = field.lower()

    def __str__(self):
        return self.fieldtype.upper() + ":" + str(list(self.field))

    def check(self, x, y, z, field):
        if not all(isinstance(v, (float, int)) for v in (x, y, z)):
            raise TypeError("All components must be numbers.")
        if not field == "e" and not field == "m":
            raise TypeError("Field must be either electric (e) or magnetic (m).")

    def getVector(self):
        return self.field

    def setVector(self, vector):
        if not len(vector) == 3:
            raise TypeError("Field vector must be 1x3.")
        elif not all(isinstance(value, (float, int)) for value in vector):
            raise TypeError("Field vector must contain numbers.")
        else:
            self.field = np.array(vector)

    def is_electric(self):
        return self.fieldtype == "e"

    def is_magnetic(self):
        return self.fieldtype == "m"

    def is_zero(self):
        return np.linalg.norm(self.field) == 0.0


class Simulation(Thread):

    def __init__(self, time: float, precision: float):
        super().__init__(target=self.run, daemon=True)
        self.check(time, precision)

        self.time = time
        self.dt = precision

        self.steps = int(round(self.time / self.dt))

        self.particles = []
        self.kinetic = []
        self.static = []

        self.electricfield = Field(0, 0, 0, "e")
        self.magneticfield = Field(0, 0, 0, "m")

        self.interactions = True
        self.progress = 0

    def __str__(self):
        return "SIMULATION T:" + str(self.time) + " P:" + str(self.dt) + " I:" + str(int(self.interactions))

    def check(self, time, precision):
        if not all(isinstance(v, (float, int)) for v in (time, precision)):
            raise ValueError("Precision must be a number.")
        if not time > 0 or not precision > 0:
            raise ValueError("Time parameters must be positive.")
        if precision >= time:
            raise ValueError("Seriously?")

    def validate(self):
        noParticles = not len(self.particles)
        oneParticle = len(self.particles) == 1
        allStationary = all(particle.is_stationary() for particle in self.particles)
        noFields = self.electricfield.is_zero() and self.magneticfield.is_zero()

        return not (noParticles or oneParticle and noFields or allStationary)

    def beginCalculations(self):
        self.start()

    def run(self):
        if self.validate():
            self.kinetic = [particle for particle in self.particles if not particle.is_stationary()]
            self.static = [particle for particle in self.particles if particle.is_stationary()]

            for iteration in range(self.steps):
                for particle in self.kinetic:
                    particle.updateVelocity(self.dt)
                    particle.updatePosition(self.dt, iteration)
                for particle in self.kinetic:
                    particle.updateAcceleration(self, self.interactions)
                    particle.updateVelocity(self.dt)
                self.progress = int(round(100 * iteration / self.steps))

    def addParticle(self, params):
        newparticle = Particle(params[0], params[1], params[2], params[3], False, self.steps)
        if any(newparticle == particle for particle in self.particles):
            raise ValueError("This particle already exists!")
        elif any(particle.is_overlapping(newparticle) for particle in self.particles) and self.interactions:
            raise ValueError("This particle is overlapping with another!")
        else:
            self.particles.append(newparticle)
            if newparticle.is_stationary():
                self.static.append(newparticle)
            else:
                self.kinetic.append(newparticle)
        self.validate()

    def editParticle(self, params, index):
        particle = self.particles[index]
        particle.setMass(params[0])
        particle.setCharge(params[1])
        particle.setInitialPosition(params[2])
        particle.setInitialVelocity(params[3])

    def replaceParticle(self, replacement, index):
        self.particles[index] = replacement
        self.validate()

    def removeParticle(self, remove: Particle):
        if remove in self.particles:
            self.particles.remove(remove)
        elif remove in self.kinetic:
            self.kinetic.remove(remove)
        elif remove in self.static:
            self.static.remove(remove)
        else:
            print("Particle not found.")
        self.validate()

    def clearWorld(self):
        del self.particles
        del self.kinetic
        del self.static
        gc.collect()

        self.particles = []
        self.kinetic = []
        self.static = []
        self.validate()

    def reset(self):
        newWorld = Simulation(self.time, self.dt)

        electric = self.electricfield.getVector()
        magnetic = self.magneticfield.getVector()

        newWorld.setElectric(electric[0], electric[1])
        newWorld.setMagnetic(magnetic[2])

        for particle in self.particles:
            simparser = SimulationParser(str(particle))
            newWorld.addParticle(simparser.parse())

        copiedParticles = newWorld.getParticles()
        for i in range(len(copiedParticles)):
            copiedParticles[i].is_stationary(self.particles[i].is_stationary())
        return newWorld

    def save(self, name="", path="."):
        saver = SimulationSaver(name, path)
        saver.save(self)

    def load(self, name="", path="."):
        self.clearWorld()
        simloader = SimulationLoader(name, path)
        data = simloader.load()

        self.setTime(data[0][0])
        self.setPrecision(data[0][1])
        self.interacting(not not data[0][2])

        self.setElectric(data[1][0][0], data[1][0][1])
        self.setMagnetic(data[1][1][2])

        self.steps = int(round(self.time / self.dt))

        for i in range(2, len(data), 1):
            parameters = data[i]
            newparticle = Particle(parameters[0], parameters[1], parameters[2], parameters[3], not not parameters[4], self.steps)
            self.particles.append(newparticle)
        self.validate()

    def getParticle(self, index):
        return self.particles[int(index < len(self.particles))*index]

    def getParticles(self):
        return self.particles

    def getKinetic(self):
        return self.kinetic

    def getStatic(self):
        return self.static

    def getMinMaxCharge(self):
        if len(self.particles) > 0:
            mincharge = min(particle.getCharge() for particle in self.particles)
            maxcharge = max(particle.getCharge() for particle in self.particles)
            return abs(mincharge), abs(maxcharge)
        else:
            return None

    def countParticles(self):
        return len(self.particles)

    def getParticleIndex(self, particle):
        if particle in self.particles:
            return self.particles.index(particle)

    def setElectric(self, x: float, y: float):
        if not all(isinstance(v, (float, int)) for v in (x, y)):
            raise ValueError("Electric field components must be numbers.")
        else:
            self.electricfield = Field(x, y, 0, "e")
        self.validate()

    def getElectric(self):
        return self.electricfield

    def setMagnetic(self, z: float):
        if not isinstance(z, (float, int)):
            raise ValueError("Magnetic field component must be a number.")
        else:
            self.magneticfield = Field(0, 0, z, "m")
        self.validate()

    def getMagnetic(self):
        return self.magneticfield

    def interacting(self, interactions=None):
        if interactions is None:
            return self.interactions
        else:
            if not isinstance(interactions, bool):
                raise ValueError("'Interactions' flag must be a boolean.")
            else:
                self.interactions = interactions

    def updateSteps(self):
        self.steps = int(round(self.time / self.dt))
        for particle in self.particles:
            particle.setSteps(self.steps)

    def setTime(self, time: float):
        if not isinstance(time, (float, int)):
            raise ValueError("Time must be a number.")
        else:
            self.time = time
            self.updateSteps()

    def getTime(self):
        return self.time

    def setPrecision(self, precision: float):
        if not isinstance(precision, (float, int)):
            raise ValueError("Precision must be a number.")
        else:
            self.dt = precision
            self.updateSteps()

    def getPrecision(self):
        return self.dt

    def getPrecisionMilliseconds(self):
        return self.dt*1000

    def getSteps(self):
        return self.steps

    def getProgress(self):
        return self.progress

    def isEmpty(self):
        return not len(self.particles)

    def isActive(self):
        return self.is_alive()
