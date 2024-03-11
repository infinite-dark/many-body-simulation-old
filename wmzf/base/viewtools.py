import numpy as np


class Camera:

    def __init__(self):
        self.center = np.array([675, 360, 0], dtype=float).reshape((3,))
        self.offset = np.zeros(shape=(3,), dtype=float)
        self.start = np.zeros(shape=(3,), dtype=float)
        self.end = np.zeros(shape=(3,), dtype=float)
        self.dR = np.zeros(shape=(3,), dtype=float)
        self.scale = 1
        self.moving = False

    def adjustView(self, point):
        converted = self.convertCoordinates(point)
        scaled = self.scalePoint(converted)
        moved = self.movePoint(scaled)
        return moved

    def convertCoordinates(self, point):
        return np.array([point[0], -point[1], 0]).reshape((3,)) + self.center

    def movePoint(self, point):
        return point + self.dR + self.offset

    def scalePoint(self, point):
        if self.scale == 1:
            return point
        return point*self.scale + (1-self.scale)*self.center

    def changeScale(self, direction):
        if direction < 0:
            self.scale /= 2
        else:
            self.scale *= 2

    def getScale(self):
        return self.scale

    def updateOffset(self):
        self.offset += self.dR
        self.dR = np.zeros(shape=(3,), dtype=float)
        self.moving = False

    def resetPosition(self):
        self.offset = np.zeros(shape=(3,), dtype=float)

    def resetScale(self):
        self.scale = 1

    def updateCenter(self, w, h):
        self.center[0] = w*15//32
        self.center[1] = h//2

    def getCenter(self):
        return self.center[0], self.center[1]

    def setStartPoint(self, start):
        self.start = start
        self.moving = True

    def setEndPoint(self, end):
        self.end = end
        self.dR = self.end - self.start

    def getOffset(self):
        return self.offset

    def getDelta(self):
        return self.dR

    def getCenter(self):
        return self.center

    def isMoving(self, moving=None):
        if moving is None:
            return self.moving
        else:
            self.moving = moving

    def getCameraPosition(self):
        dR = np.array(self.dR)
        offset = np.array(self.offset)

        dR[0] *= -1
        offset[0] *= -1
        return list((dR + offset)/self.scale)
