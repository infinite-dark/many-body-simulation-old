from PySide2.QtGui import *
from PySide2.QtCore import *
from PySide2.QtWidgets import *

from wmzf.simulation import *

from wmzf.base.widgets import Menu, ParticleList, ParticleForm, SimulationForm, NewWorld, LoadFileWidget, SaveFileWidget
from wmzf.base.simtools import ListParser
from wmzf.base.viewtools import Camera

from time import perf_counter
from random import randint
from math import ceil


class StyleLoader:

    def __init__(self, widget: QWidget, name: str, file: str):
        widget.setObjectName(name)
        try:
            with open("resources/stylesheets/" + file) as stylesheet:
                style = stylesheet.readlines()
                style = [line.rstrip() for line in style]
                style = " ".join(style)
            widget.setStyleSheet(style)
        except IOError:
            print("Unable to load style for element:", name)


class SimulationStateTracker(QObject):

    started = Signal()
    progressed = Signal()
    finished = Signal(bool)
    valid = Signal(bool)

    saved = Signal()
    loaded = Signal()

    def __init__(self, delay):
        super().__init__()

        self.world = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.checkState)

        self.startedEmited = False
        self.finishedEmited = False
        self.isvalid = False

        self.timer.start(delay)

    def checkState(self):
        if self.world is not None:
            progress = self.world.getProgress()
            active = self.world.isActive()
            finished = progress == 100

            if active and not finished:
                self.progressed.emit()
            valid = self.world.validate()

            if active and not self.startedEmited:
                self.started.emit()
                self.startedEmited = True
            if not active and self.startedEmited:
                self.startedEmited = False

            if finished and not self.finishedEmited:
                self.finished.emit(finished)
                self.finishedEmited = True
            if not finished and self.finishedEmited:
                self.finishedEmited = False

            if valid != self.isvalid:
                self.valid.emit(self.world.validate())
                self.isvalid = valid

    def reset(self):
        self.startedEmited = False
        self.finishedEmited = False
        self.isvalid = False

    def setWorld(self, world):
        self.world = world


class SimulationView(QWidget):

    def __init__(self):
        super().__init__()
        self.fillBackground()
        self.dimensions = np.array([1350, 720, 0], dtype=float).reshape((3,))
        self.setEnabled(True)

        self.timer = QTimer(self)
        self.camera = Camera()

        self.world = None
        self.step = 0
        self.skip = 0
        self.timer.timeout.connect(self.callPaintEvent)
        self.timer.setInterval(11)
        self.clockevent = False

        self.finished = False

        self.positive = QImage("resources/icons/proton.png")
        self.negative = QImage("resources/icons/electron.png")

        self.followedParticle = -1

        self.mincharge = 0
        self.maxcharge = 0

        self.continuous = True

        self.overlay = True
        self.data = True
        self.trails = True
        self.trajectories = False
        self.autoscale = False

    def fillBackground(self):
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor(30, 30, 30, 255))
        self.setPalette(palette)

    def setWorld(self, world):
        self.world = world
        if self.world is not None:
            if self.world.isEmpty():
                self.mincharge = self.maxcharge = 1
            else:
                self.mincharge, self.maxcharge = self.world.getMinMaxCharge()

    def paintEvent(self, e):
        start = perf_counter()
        painter = QPainter(self)

        painter.setPen(QColor(0, 154, 26, 255))
        painter.setFont(QFont("Arial", 24))
        painter.drawText(20, 50, "SIMULATION: CHARGED N-BODY SYSTEM")
        painter.setFont(QFont("Arial", 10))
        painter.drawText(20, 70, "Author: infinite-dark")

        if self.world is not None:
            if not self.trajectories:
                self.drawParticles(painter)
                if self.world.isActive():
                    self.drawProgress(painter)
                if self.overlay:
                    self.drawOverlay(painter)
            else:
                self.drawTrajectories(painter)
                if not self.followedParticle < 0:
                    painter.drawText(30, 100, "ID: " + str(self.followedParticle))

        center = self.camera.getCenter()
        painter.setPen(Qt.white)
        painter.drawLine(center[0], center[1] - 10, center[0], center[1] + 10)
        painter.drawLine(center[0] - 10, center[1], center[0] + 10, center[1])
        painter.end()
        finish = perf_counter()

        if self.world is not None and not self.trajectories and self.clockevent:
            self.skip = ceil((0.007 + finish - start - 0.0005)/self.world.getPrecision())
            if self.step + self.skip - 1 < self.world.getSteps():
                self.step += self.skip - 1
            else:
                if self.continuous:
                    self.step = 0
                else:
                    self.step = self.world.getSteps() - 1
                    self.timer.stop()

    def drawParticles(self, painter):
        if -1 < self.followedParticle < self.world.countParticles():
            followed = self.world.getParticle(self.followedParticle)
            target = followed.getPoint(self.step)
            target = self.camera.adjustView(target)
        else:
            target = self.camera.getCenter()
        points = []

        for particle in self.world.getParticles():
            point = particle.getPoint(self.step)
            point = self.camera.adjustView(point)

            point = point - target + self.camera.getCenter()
            image, diameter = self.particleIcon(particle)
            try:
                painter.drawImage(point[0] - diameter/2, point[1] - diameter/2, image)
            except OverflowError:
                continue
            if self.data:
                painter.setFont(QFont("Arial", 7))
                painter.setPen(Qt.white)
                self.drawParticleDetails(painter, point, particle)
            if self.autoscale:
                points.append(point)
            if self.trails and self.followedParticle < 0:
                length = int(1/self.world.getPrecision())
                painter.setPen(Qt.white)
                if self.step > length:
                    start = self.step - length
                else:
                    start = 0
                for i in range(start, self.step, int(length/50)):
                    coords = particle.getPoint(i)
                    coords = self.camera.adjustView(coords)
                    try:
                        painter.drawPoint(coords[0], coords[1])
                    except OverflowError:
                        pass

        if self.autoscale:
            center = self.camera.getCenter()
            if not all((0 < point[0] < 2*center[0] and 0 < point[1] < 2*center[1]) for point in points)\
                    and any((0 < point[0] < 2*center[0] and 0 < point[1] < 2*center[1]) for point in points):
                self.camera.changeScale(-1)
            else:
                if all((center[0]//2 < point[0] < 3*center[0]//2 and center[1]//2 < point[1] < 3*center[1]//2) for point in points) \
                        and self.camera.getScale() < 4:
                    self.camera.changeScale(1)

    def particleIcon(self, particle):
        if particle.getCharge() < 0:
            icon = self.negative
        else:
            icon = self.positive
        diameter = int((10*abs(particle.getCharge())/self.maxcharge + 14)*self.camera.scale)
        if diameter < 5: diameter = 5
        if diameter > 26: diameter = 26
        return icon.scaled(diameter, diameter), diameter

    def drawTrajectories(self, painter):
        painter.setPen(Qt.white)
        painter.setFont(QFont("Arial", 10))
        increment = 5*int(0.007/self.world.getPrecision())

        if self.followedParticle < 0:
            particles = self.world.getParticles()
        else:
            particles = [self.world.getParticle(self.followedParticle)]

        for particle in particles:
            for i in range(0, self.world.getSteps(), increment):
                try:
                    coords = particle.getPoint(i)
                    coords = self.camera.adjustView(coords)
                    painter.drawPoint(coords[0], coords[1])
                except OverflowError:
                    continue
                except ValueError:
                    break

    def drawOverlay(self, painter):
        self.drawTable(painter, 30, 130, "SIMULATION", ["Physics time:", "Frame skip:", "Step:", "Continuous:"],
                                                       [self.getSimulationTime, self.getSkip, self.getStep, self.getContinuous],
                                                       [" s", "", "", ""])

        self.drawTable(painter, 30, 252, "CAMERA", ["Position:", "Scale:", "Auto-scaling:", "Following:", "Trails:"],
                                                   [self.camera.getCameraPosition, self.camera.getScale, self.autoscaling, self.isFollowing, self.getTrails],
                                                   [" px", " px/m", "", "", ""])

        self.drawTable(painter, 30, 390, "WORLD", ["Time:", "Precision:", "Interactions:", "Particles:", "Ready:"],
                                                  [self.world.getTime, self.world.getPrecisionMilliseconds, self.world.interacting, self.world.countParticles, self.getFinished],
                                                  [" s", " ms", "", "", ""])

        self.drawTable(painter, 30, 535, "FIELD", ["Electric:", "Magnetic:"],
                                                  [self.world.getElectric().getVector, self.world.getMagnetic().getVector],
                                                  [" N/C", " T"])

        if not self.followedParticle < 0:
            painter.setPen(QColor(0, 154, 26, 255))
            painter.setFont(QFont("Arial", 14))
            painter.drawText(1160, 160, "NOW FOLLOWING")
            painter.setFont(QFont("Arial", 9))
            particle = self.world.getParticle(self.followedParticle)
            self.drawParticleDetails(painter, np.array([1190, 200]), particle)

    def drawTable(self, painter, x, y, title, rows, data, units):
        painter.setPen(QColor(0, 154, 26, 255))
        painter.setFont(QFont("Arial", 14))
        painter.drawText(x, y, title)

        painter.setFont(QFont("Arial", 10))
        for i in range(1, len(rows) + 1, 1):
            painter.drawText(x + 10, y + 20*i, rows[i-1])
            value = data[i-1]()
            if isinstance(value, np.ndarray):
                value = list(value)
            painter.drawText(x + 100, y + 20*i, str(value) + units[i-1])

    def drawProgress(self, painter):
        painter.setFont(QFont("Arial", 14))
        painter.setPen(QColor(0, 154, 26, 255))
        center = self.camera.getCenter()
        painter.drawText(center[0] - 30, center[1]*2 - 30, "Calculating... " + str(self.world.getProgress()) + " %")

    def drawParticleDetails(self, painter, position, particle):
        x = position[0] + 20
        y = position[1] - 20

        coords = particle.getPoint(self.step)
        index = self.world.getParticleIndex(particle)
        mass = particle.getMass()
        charge = particle.getCharge()

        painter.drawText(x, y, "ID: " + str(index))
        painter.drawText(x, y + 12, "M: {:.2e} kg".format(mass))
        painter.drawText(x, y + 24, "C: {:.2e} C".format(charge))
        painter.drawText(x, y + 36, "P: [" + str(int(coords[0])) + ", " + str(int(coords[1])) + "] px")

    def callPaintEvent(self):
        self.clockevent = True
        self.repaint()
        self.clockevent = False

    def getStep(self):
        return self.step

    def getSimulationTime(self):
        return round(self.step*self.world.getPrecision(), 2)

    def getSkip(self):
        return self.skip

    def updateSkip(self):
        if self.world is not None:
            pass

    def getFinished(self):
        return self.finished

    def setFinished(self, finished):
        self.finished = finished
        self.repaint()

    def getContinuous(self):
        return self.continuous

    def autoscaling(self):
        return self.autoscale

    def getTrails(self):
        return self.trails

    def isFollowing(self):
        return not self.followedParticle < 0

    def setWindowSize(self, size):
        self.camera.updateCenter(size.width(), size.height())

    #funkcje sterujące animacją
    def startSimulation(self):
        if self.world is not None and self.finished:
            self.timer.start()
            self.setFocus()

    def pauseSimulation(self):
        self.timer.stop()
        self.setFocus()

    def restartSimulation(self):
        self.step = 0
        self.timer.stop()
        self.repaint()
        self.setFocus()

    def mousePressEvent(self, e):
        if self.world is not None and not self.autoscale:
            pos = np.array([e.pos().x(), e.pos().y(), 0], dtype=float).reshape((3,))
            if e.button() == 1:
                self.camera.setStartPoint(pos)

            if not self.timer.isActive():
                self.repaint()

    def mouseMoveEvent(self, e):
        if self.world is not None and self.followedParticle < 0 and not self.autoscale:
            pos = np.array([e.pos().x(), e.pos().y(), 0], dtype=float).reshape((3,))
            if self.camera.isMoving():
                self.camera.setEndPoint(pos)

            if not self.timer.isActive():
                self.repaint()

    def mouseReleaseEvent(self, e):
        if self.world is not None and self.followedParticle < 0 and not self.autoscale:
            if e.button() == 1:
                self.camera.updateOffset()
            if e.button() == 2:
                self.camera.resetPosition()
                self.camera.resetScale()

            if not self.timer.isActive():
                self.repaint()

    def wheelEvent(self, e):
        if self.world is not None:
            if not self.timer.isActive() or not self.autoscale:
                self.camera.changeScale(e.angleDelta().y())

            if not self.timer.isActive():
                self.repaint()

    def keyReleaseEvent(self, e):
        if e.key() == Qt.Key_F3:
            self.overlay = not self.overlay
            self.repaint()
        if self.world is not None and self.world.countParticles() > 0:
            if e.key() == 16777236:
                self.followedParticle += 1
                if self.followedParticle >= self.world.countParticles():
                    self.followedParticle = self.world.countParticles() - 1
            if e.key() == 16777234:
                self.followedParticle -= 1
                if self.followedParticle < -1:
                    self.followedParticle = -1
            if e.key() == Qt.Key_P:
                self.data = not self.data
            if e.key() == Qt.Key_Z:
                self.autoscale = not self.autoscale
            if e.key() == Qt.Key_T:
                self.restartSimulation()
                self.trajectories = not self.trajectories
            if e.key() == Qt.Key_R:
                self.trails = not self.trails
            if e.key() == Qt.Key_C:
                self.continuous = not self.continuous
            self.repaint()


#panel ustawień
class SettingsView(QWidget):

    worldChanged = Signal()

    def __init__(self):
        super().__init__()
        self.world = None

        ############################################################

        self.layout = QHBoxLayout()
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(50, 50, 50, 50)

        ############################################################

        self.leftpanel = QWidget()
        self.leftlayout = QVBoxLayout()

        self.particlelist = ParticleList()      #lista cząstek
        self.particlelist.particleSelected.connect(self.fillForm)
        self.particlelist.particleUnselected.connect(self.clearForm)
        self.particlelist.toggleStationary.connect(self.toggleStationary)

        self.leftlayout.addWidget(self.particlelist)
        self.leftpanel.setLayout(self.leftlayout)

        ############################################################

        self.rightpanel = QWidget()
        self.rightlayout = QVBoxLayout()

        ############################################################

        self.particleform = ParticleForm()
        self.particleform.particleAdded.connect(lambda data: self.particleAction(data, "add"))
        self.particleform.particleChanged.connect(lambda data: self.particleAction(data, "edit"))
        self.particleform.particleRemoved.connect(self.removeParticle)
        self.particleform.inputCancelled.connect(self.cancelInput)

        self.simulationform = SimulationForm()

        self.paramsform = self.simulationform.getParametersForm()
        self.paramsform.parametersChanged.connect(self.updateSimulationParameters)

        self.fieldsform = self.simulationform.getFieldForm()
        self.fieldsform.fieldsChanged.connect(self.updateElectromagneticField)

        ############################################################

        self.rightlayout.addWidget(self.particleform, 2)
        self.rightlayout.addWidget(self.simulationform, 1)
        self.rightpanel.setLayout(self.rightlayout)

        ############################################################

        self.layout.addWidget(self.leftpanel, 1)
        self.layout.addWidget(self.rightpanel, 2)
        self.setLayout(self.layout)
        self.fillBackground()

        ############################################################

    def fillBackground(self):
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor(20, 20, 20))
        self.setPalette(palette)

    def updateSimulationParameters(self):
        try:
            try:
                time = float(self.paramsform.getTime())
                precision = float(self.paramsform.getPrecision())
            except ValueError:
                self.paramsform.fillEntries(str(self.world.getTime()), str(self.world.getPrecision()))
            else:
                if precision > time:
                    raise ValueError("Seriously?")
                else:
                    self.world.setTime(time)
                    self.world.setPrecision(precision)
                    self.paramsform.fillEntries(str(self.world.getTime()), str(self.world.getPrecision()))
                    self.worldChanged.emit()
        except ValueError:
            self.paramsform.fillEntries(str(self.world.getTime()), str(self.world.getPrecision()))

    def updateElectromagneticField(self):
        try:
            parser = ListParser(self.fieldsform.getElectric())
            electric = parser.parse()
            parser = ListParser(self.fieldsform.getMagnetic())
            magnetic = parser.parse()

            fields = [electric, magnetic]
            for i in range(len(fields)):
                if len(fields[i]) > 3:
                    fields[i] = fields[i][:3]
                else:
                    while len(fields[i]) < 3:
                        fields[i].append(0.0)
                if not i:
                    fields[i][2] = 0.0
                else:
                    if fields[i][2] == 0.0:
                        fields[i][2] = fields[i][0]
                        fields[i][0] = 0.0
            try:
                self.world.setElectric(electric[0], electric[1])
                self.world.setMagnetic(magnetic[2])
                self.fieldsform.fillEntries(str(list(self.world.getElectric().getVector())), str(list(self.world.getMagnetic().getVector())))
                self.worldChanged.emit()
            except ValueError:
                self.fieldsform.fillEntries(str(list(self.world.getElectric().getVector())), str(list(self.world.getMagnetic().getVector())))
        except ValueError:
            self.fieldsform.fillEntries(str(list(self.world.getElectric().getVector())), str(list(self.world.getMagnetic().getVector())))

    #przetwarzanie wejścia z formularza
    def processFormInput(self, data):
        if "" in data:
            raise AttributeError("[ERROR] Empty field in particle form.")
        if len(data) < 4:
            raise AttributeError("[ERROR] Bad data.")
        params = [float(value) for value in data[:2]]
        for value in data[2:]:
            parser = ListParser(value)
            parsedlist = parser.parse()

            while len(parsedlist) < 3:
                parsedlist.append(0.0)
            if len(parsedlist) > 3:
                parsedlist = parsedlist[:3]
            parsedlist[2] = 0.0

            params.append(parsedlist)
        return params

    def setWorld(self, world):
        self.world = world

    def fillList(self):
        self.particlelist.clear()
        for particle in self.world.getParticles():
            self.particlelist.addElement(particle)

    def fillForm(self, index):
        particle = self.world.getParticle(index)
        self.particleform.fillForm(particle)
        self.particleform.setMode("edit")
        self.particleform.setRemove()

    def clearForm(self):
        self.particleform.clearForm()
        self.particleform.setMode("add")
        self.particleform.setCancel()

    def particleAction(self, data, origin):
        try:
            try:
                params = self.processFormInput(data)
            except (ValueError, TypeError):
                raise AttributeError("[ERROR] Incorrect particle parameters.")
        except AttributeError:
            if origin == "add":
                self.clearForm()
            else:
                row = self.particlelist.currentRow()
                self.particleform.setRemove()
                self.fillForm(row)
        else:
            if origin == "add":
                try:
                    self.world.addParticle(params)
                except ValueError:
                    pass
                self.fillList()
                self.clearForm()
            else:
                row = self.particlelist.currentRow()
                self.world.editParticle(params, row)
                self.fillList()
            self.worldChanged.emit()

    def removeParticle(self):
        row = self.particlelist.currentRow()
        particle = self.world.getParticle(row)
        self.world.removeParticle(particle)
        self.clearForm()
        self.fillList()
        self.worldChanged.emit()

    def cancelInput(self):
        self.particleform.setActive(False)
        selected = self.particlelist.selectionModel().hasSelection()
        row = self.particlelist.currentRow()
        mode = self.particleform.getMode()

        if selected and mode == "add" or not selected:
            self.particlelist.clearSelection()
            self.particleform.clearForm()
            self.particleform.setMode("add")
        elif selected and mode == "edit":
            self.fillForm(row)
            self.particleform.setMode("edit")
            self.particleform.setRemove()

    def toggleStationary(self, row):
        if row >= 0:
            particle = self.world.getParticle(row)
            stationary = particle.is_stationary()
            particle.is_stationary(not stationary)

            listitem = self.particlelist.item(row)
            description = listitem.text()
            description = description.replace(str(stationary), str(particle.is_stationary()))
            listitem.setText(description)
            self.worldChanged.emit()

    def fillParameters(self):
        self.simulationform.fillEntries(self.world)


class SimulationWindow(QMainWindow):

    resized = Signal(QSize)

    def __init__(self):
        super().__init__()
        self.world = None

        self.setWindowTitle("SIMPLE N-BODY SIMULATION")
        self.centerWindow()
        self.fillBackground()

        self.frame = QWidget()
        self.mainlayout = QHBoxLayout()
        self.mainlayout.setContentsMargins(0, 0, 0, 0)
        self.mainlayout.setSpacing(0)
        self.setCentralWidget(self.frame)

        self.menu = Menu(self)
        self.view = QStackedWidget()

        self.simview = SimulationView()
        self.settings = SettingsView()
        self.settings.worldChanged.connect(self.editWorld)

        self.savesim = SaveFileWidget()
        self.savesim.saveFile.connect(self.saveWorld)

        self.loadsim = LoadFileWidget()
        self.loadsim.loadFile.connect(self.loadWorld)

        self.view.addWidget(self.simview)
        self.view.addWidget(self.settings)
        self.view.addWidget(NewWorld(self))
        self.view.addWidget(self.savesim)
        self.view.addWidget(self.loadsim)

        self.mainlayout.addWidget(self.menu, 1)
        self.mainlayout.addWidget(self.view, 15)
        self.frame.setLayout(self.mainlayout)

        StyleLoader(self.frame, "frame", "stylesheet.css")
        StyleLoader(self.menu, "menu", "menu.css")

        self.stateTracker = SimulationStateTracker(25)
        #self.randomWorld(15, 0.005, 7)

        self.stateTracker.started.connect(self.menu.disableControls)
        self.stateTracker.progressed.connect(self.simview.repaint)
        self.stateTracker.finished.connect(self.simulationReady)
        self.stateTracker.valid.connect(self.menu.validityCheck)

        self.resized.connect(self.simview.setWindowSize)

        self.simview.setFocus()

    def centerWindow(self):
        geometry = self.frameGeometry()
        centerPoint = QDesktopWidget().availableGeometry().center()
        geometry.moveCenter(centerPoint)
        self.move(geometry.topLeft())

    def fillBackground(self):
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor(22, 22, 22, 255))
        self.setPalette(palette)

    def showSimulation(self):
        self.view.setCurrentIndex(0)
        self.simview.setFocus()

    def showSettings(self):
        if self.world is not None:
            self.view.setCurrentIndex(1)
            self.settings.fillList()
            self.settings.fillParameters()
            self.simview.pauseSimulation()
        else:
            self.view.setCurrentIndex(2)

    def showSaveScreen(self):
        self.view.setCurrentIndex(3)
        self.savesim.savelabel.setText("")
        self.savesim.refreshView()
        self.simview.pauseSimulation()

    def showLoadScreen(self):
        self.view.setCurrentIndex(4)
        self.loadsim.loadlabel.setText("")
        self.loadsim.refreshView()
        self.simview.pauseSimulation()

    def newWorld(self, time, precision, interactions):
        self.world = Simulation(time, precision)
        self.world.interacting(interactions)

        self.simview.setWorld(self.world)
        self.settings.setWorld(self.world)

        self.stateTracker.setWorld(self.world)

    def editWorld(self):
        if self.world.getProgress() == 100:
            self.stateTracker.reset()
            self.simview.updateSkip()
            self.menu.disableControls()

            self.world = self.world.reset()
            self.simview.setWorld(self.world)
            self.settings.setWorld(self.world)
            self.stateTracker.setWorld(self.world)

    def simulate(self):
        if self.world is not None:
            self.world.beginCalculations()
            self.simview.setFocus()
            self.menu.disable()

    def simulationReady(self, finished):
        self.simview.setFocus()
        self.simview.setFinished(finished)

        self.menu.disable(False)
        self.menu.runbutton.setDisabled(True)

    def saveWorld(self, path):
        try:
            simsaver = SimulationSaver(path[1], path[0])
            simsaver.save(self.world)
            self.savesim.refreshView()
            self.savesim.confirmSave()
        except Exception:
            self.savesim.confirmSave(False)

    def loadWorld(self, path):
        self.world = Simulation(1, 0.1)
        self.world.load(path[1], path[0])

        self.simview.restartSimulation()
        self.simview.setWorld(self.world)
        self.settings.setWorld(self.world)

        self.stateTracker.setWorld(self.world)

        self.simview.setFinished(False)
        self.menu.disable(True)
        self.menu.runbutton.setDisabled(False)
        self.menu.savesimulation.setDisabled(False)

        self.loadsim.confirmLoad()
        self.loadsim.refreshView()

    def randomWorld(self, time, precision, n):
        self.world = Simulation(time, precision)
        for i in range(n):
            self.world.addParticle([randint(1, 100), randint(-100, 100)/3400,
                                            [randint(-500, 500), randint(-500, 500), 0],
                                            [randint(-100, 100), randint(-100, 100), 0],
                                            not not randint(0, 1), self.world.getSteps()])
        self.settings.setWorld(self.world)
        self.simview.setWorld(self.world)

        self.stateTracker.setWorld(self.world)

    def getWorld(self):
        return self.world

    def setWorld(self, world):
        self.world = world

    def resizeEvent(self, *args, **kwargs):
        self.resized.emit(self.size())
        for button in self.menu.allbuttons:
            button.setMaximumHeight(self.size().height()//8)
