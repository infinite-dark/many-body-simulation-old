import os
from PySide2.QtGui import QIcon, QFont

from wmzf.base.sublcasses.widgets import *
from wmzf.base.simtools import SimulationParser


class Menu(QWidget):

    def __init__(self, window):
        super().__init__()
        self.mainwindow = window
        self.buttons = []

        self.layout = QVBoxLayout()
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.showsimulation = MenuButton()
        self.showsimulation.setIconSize(QSize(45, 45))
        self.showsimulation.setIcon(QIcon("resources/icons/simulation.png"))
        self.showsimulation.clicked.connect(self.mainwindow.showSimulation)

        self.showsettings = MenuButton()
        self.showsettings.setIconSize(QSize(52, 52))
        self.showsettings.setIcon(QIcon("resources/icons/settings.png"))
        self.showsettings.clicked.connect(self.mainwindow.showSettings)

        self.savesimulation = MenuButton()
        self.savesimulation.setIconSize(QSize(43, 43))
        self.savesimulation.setIcon(QIcon("resources/icons/save.png"))
        self.savesimulation.clicked.connect(self.mainwindow.showSaveScreen)
        self.savesimulation.setDisabled(True)
        self.buttons.append(self.savesimulation)

        self.loadsimulation = MenuButton()
        self.loadsimulation.setIconSize(QSize(93, 93))
        self.loadsimulation.setIcon(QIcon("resources/icons/load.png"))
        self.loadsimulation.clicked.connect(self.mainwindow.showLoadScreen)
        self.buttons.append(self.loadsimulation)

        self.playbutton = MenuButton()
        self.playbutton.setIconSize(QSize(54, 54))
        self.playbutton.setIcon(QIcon("resources/icons/play.png"))
        self.playbutton.clicked.connect(lambda: self.mainwindow.simview.startSimulation())
        self.playbutton.setDisabled(True)
        self.buttons.append(self.playbutton)

        self.pausebutton = MenuButton()
        self.pausebutton.setIconSize(QSize(32, 32))
        self.pausebutton.setIcon(QIcon("resources/icons/pause.png"))
        self.pausebutton.clicked.connect(lambda: self.mainwindow.simview.pauseSimulation())
        self.pausebutton.setDisabled(True)
        self.buttons.append(self.pausebutton)

        self.stopbutton = MenuButton()
        self.stopbutton.setIconSize(QSize(30, 30))
        self.stopbutton.setIcon(QIcon("resources/icons/stop.png"))
        self.stopbutton.clicked.connect(lambda: self.mainwindow.simview.restartSimulation())
        self.stopbutton.setDisabled(True)
        self.buttons.append(self.stopbutton)

        self.runbutton = MenuButton()
        self.runbutton.setIconSize(QSize(45, 45))
        self.runbutton.setIcon(QIcon("resources/icons/run.png"))
        self.runbutton.clicked.connect(lambda: self.mainwindow.simulate())
        self.runbutton.setDisabled(True)
        self.buttons.append(self.runbutton)

        self.layout.addWidget(self.showsimulation, 1)
        self.layout.addWidget(self.showsettings, 1)
        self.layout.addWidget(self.savesimulation, 1)
        self.layout.addWidget(self.loadsimulation, 1)
        self.layout.addWidget(self.playbutton, 1)
        self.layout.addWidget(self.pausebutton, 1)
        self.layout.addWidget(self.stopbutton, 1)
        self.layout.addWidget(self.runbutton, 1)

        self.allbuttons = self.buttons + [self.showsimulation, self.showsettings]

        self.setLayout(self.layout)

    def disable(self, disabled=True):
        self.savesimulation.setDisabled(disabled)
        self.playbutton.setDisabled(disabled)
        self.pausebutton.setDisabled(disabled)
        self.stopbutton.setDisabled(disabled)
        self.runbutton.setDisabled(disabled)

    def disableControls(self):
        self.disable()
        self.savesimulation.setDisabled(False)

    def validityCheck(self, valid):
        if valid:
            self.savesimulation.setDisabled(False)
            self.runbutton.setDisabled(False)
        else:
            self.savesimulation.setDisabled(True)
            self.runbutton.setDisabled(True)


class ParticleList(QListWidget):

    particleSelected = Signal(int)
    particleUnselected = Signal()
    toggleStationary = Signal(int)

    def __init__(self):
        super().__init__()

        self.listfont = QFont()
        self.listfont.setFamily("Arial")
        self.listfont.setPixelSize(13)
        self.setFont(self.listfont)
        self.setIconSize(QSize(64, 64))

        self.proton = QIcon("resources/icons/proton.png")
        self.electron = QIcon("resources/icons/electron.png")

        self.setStyleSheet("color: white;")

    def addElement(self, particle):
        item = QListWidgetItem()
        values = self.createDescription(particle)

        if particle.getCharge() < 0:
            item.setIcon(self.electron)
        else:
            item.setIcon(self.proton)

        item.setText(values)
        self.addItem(item)

    def createDescription(self, particle):
        values = 60 * "*" + "\n"
        values += "Mass: \t" + str(particle.getMass()) + " kg\n"
        values += "Charge: \t" + str(particle.getCharge()) + " C\n"
        values += "Position: \t" + str(list(particle.getInitialPosition())) + " px\n"
        values += "Velocity: \t" + str(list(particle.getInitialVelocity())) + " px\n"
        values += "Stationary: " + str(particle.is_stationary()) + "\n"
        values += 60 * "*"
        return values

    def mousePressEvent(self, e):
        if e.button() == 1:
            super().mousePressEvent(e)
        else:
            self.clearSelection()
            self.particleUnselected.emit()
            if e.button() == 4:
                self.toggleStationary.emit(self.currentRow())

    def mouseDoubleClickEvent(self, e):
        if e.button() == 1:
            super().mouseDoubleClickEvent(e)
            row = self.currentRow()
            self.particleSelected.emit(row)

    def currentChanged(self, current, previous):
        self.particleUnselected.emit()


class ParticleForm(QWidget):

    particleAdded = Signal(tuple)
    particleChanged = Signal(tuple)
    particleRemoved = Signal()
    inputCancelled = Signal()

    def __init__(self):
        super().__init__()

        self.layout = QFormLayout()
        self.entries = []
        self.mode = "add"

        self.mass = LabeledEntry("MASS")
        self.mass.setPlaceholderText("[kilograms]")
        self.layout.addWidget(self.mass)
        self.entries.append(self.mass)

        self.charge = LabeledEntry("CHARGE")
        self.charge.setPlaceholderText("[coulombs]")
        self.layout.addWidget(self.charge)
        self.entries.append(self.charge)

        self.position = LabeledEntry("POSITION")
        self.position.setPlaceholderText("x, y, z [meters]")
        self.layout.addWidget(self.position)
        self.entries.append(self.position)

        self.velocity = LabeledEntry("VELOCITY")
        self.velocity.setPlaceholderText("x, y, z [meters/second]")
        self.layout.addWidget(self.velocity)
        self.entries.append(self.velocity)

        self.buttons = QWidget()
        self.buttonlayout = QHBoxLayout()

        self.confirmbutton = Button("")

        self.cancelbutton = Button("CANCEL")
        self.cancelbutton.clicked.connect(self.inputCancelled.emit)

        self.setMode(self.mode)

        self.buttonlayout.addWidget(self.confirmbutton)
        self.buttonlayout.addWidget(self.cancelbutton)
        self.buttons.setLayout(self.buttonlayout)

        self.layout.addWidget(self.buttons)
        self.setLayout(self.layout)

    def fillForm(self, particle):
        data = tuple(str(parameter) for parameter in SimulationParser(str(particle)).parse())
        for i in range(len(self.entries)):
            self.entries[i].setText(data[i])

    def readForm(self):
        data = tuple(entry.getText() for entry in self.entries)
        return data

    def clearForm(self):
        for entry in self.entries:
            entry.setText("")
            entry.isDisabled(True)

    def setActive(self, active):
        for entry in self.entries:
            entry.isDisabled(not active)

    def setMode(self, mode):
        self.disconnectConfirm()
        mode = mode.lower()
        self.mode = mode

        self.confirmbutton.setText(mode.upper())
        self.confirmbutton.clicked.connect(lambda: self.changeMode(mode))

    def getMode(self):
        return self.mode

    def setCancel(self):
        self.disconnectCancel()
        self.cancelbutton.setText("CANCEL")
        self.cancelbutton.clicked.connect(self.inputCancelled.emit)

    def setRemove(self):
        self.disconnectCancel()
        self.cancelbutton.setText("REMOVE")
        self.cancelbutton.clicked.connect(self.removeParticle)

    def changeMode(self, mode):
        mode = mode.lower()
        self.disconnectConfirm()
        self.setActive(True)
        self.confirmbutton.setText("SAVE")

        self.confirmbutton.clicked.connect(lambda: self.changeParticle(mode))
        if mode == "edit":
            self.setCancel()

    def changeParticle(self, mode):
        signal = { "add": self.particleAdded.emit, "edit": self.particleChanged.emit }
        self.setMode(mode)
        data = self.readForm()
        self.setActive(False)
        signal[mode](data)

    def disconnectConfirm(self):
        try:
            self.confirmbutton.disconnect()
        except TypeError:
            pass

    def disconnectCancel(self):
        try:
            self.cancelbutton.disconnect()
        except TypeError:
            pass

    def removeParticle(self):
        self.setMode("add")
        self.particleRemoved.emit()


class FieldForm(QWidget):

    fieldsChanged = Signal()

    def __init__(self):
        super().__init__()
        self.layout = QFormLayout()

        self.electricfield = LabeledEntry("ELECTRIC")
        self.electricfield.setPlaceholderText("x, y, z [newtons/coulomb]")
        self.layout.addWidget(self.electricfield)

        self.magneticfield = LabeledEntry("MAGNETIC")
        self.magneticfield.setPlaceholderText("x, y, z [tesla]")
        self.layout.addWidget(self.magneticfield)

        self.setbutton = Button("SET")
        self.setbutton.clicked.connect(self.fieldsChanged.emit)
        self.layout.addWidget(self.setbutton)

        self.setLayout(self.layout)

        self.electricfield.isDisabled(False)
        self.magneticfield.isDisabled(False)

    def fillEntries(self, electric, magnetic):
        self.electricfield.setText(electric)
        self.magneticfield.setText(magnetic)

    def getElectric(self):
        return self.electricfield.getText()

    def getMagnetic(self):
        return self.magneticfield.getText()


class ParametersForm(QWidget):

    parametersChanged = Signal()

    def __init__(self):
        super().__init__()
        self.layout = QFormLayout()

        self.timefield = LabeledEntry("TIME")
        self.timefield.setPlaceholderText("[seconds]")
        self.layout.addWidget(self.timefield)

        self.precisionfield = LabeledEntry("PRECISION")
        self.precisionfield.setPlaceholderText("[seconds]")
        self.layout.addWidget(self.precisionfield)

        self.setbutton = Button("SET")
        self.setbutton.clicked.connect(self.parametersChanged.emit)
        self.layout.addWidget(self.setbutton)

        self.setLayout(self.layout)

        self.timefield.isDisabled(False)
        self.precisionfield.isDisabled(False)

    def fillEntries(self, time, precision):
        self.timefield.setText(time)
        self.precisionfield.setText(precision)

    def getTime(self):
        return self.timefield.getText()

    def getPrecision(self):
        return self.precisionfield.getText()


class SimulationForm(QWidget):

    def __init__(self):
        super().__init__()
        self.layout = QHBoxLayout()

        self.fieldform = FieldForm()
        self.parametersform = ParametersForm()

        self.layout.addWidget(self.fieldform)
        self.layout.addWidget(self.parametersform)

        self.setLayout(self.layout)

    def getFieldForm(self):
        return self.fieldform

    def getParametersForm(self):
        return self.parametersform

    def fillEntries(self, world):
        electric = str(list(world.getElectric().getVector()))
        magnetic = str(list(world.getMagnetic().getVector()))
        self.fieldform.fillEntries(electric, magnetic)

        time = str(world.getTime())
        precision = str(world.getPrecision())
        self.parametersform.fillEntries(time, precision)


class NewWorld(QWidget):

    def __init__(self, w):
        super().__init__()
        self.mainwindow = w

        self.layout = QFormLayout()
        self.layout.setContentsMargins(400, 200, 400, 100)

        self.timeentry = LabeledEntry("TIME")
        self.timeentry.isDisabled(False)

        self.precisionentry = LabeledEntry("PRECISION")
        self.precisionentry.isDisabled(False)

        self.interactions = QCheckBox("Interactions Enabled")
        self.interactions.setChecked(True)

        self.checkboxholder = QWidget()
        self.checkboxholder.setLayout(QHBoxLayout())
        self.checkboxholder.layout().setAlignment(Qt.AlignCenter)
        self.checkboxholder.layout().addWidget(self.interactions)

        self.setbutton = Button("CREATE NEW WORLD")
        self.setbutton.clicked.connect(self.createWorld)
        self.setbutton.setDisabled(True)

        self.infolabel = Label("enter data to create world")
        self.infolabel.setObjectName("info")

        self.layout.addWidget(self.timeentry)
        self.layout.addWidget(self.precisionentry)
        self.layout.addWidget(self.checkboxholder)
        self.layout.addWidget(self.setbutton)
        self.layout.addWidget(self.infolabel)

        self.setLayout(self.layout)

        self.fillBackground()
        self.setStyleSheet("QLabel { border: 1px solid #00770D; } QLabel#info { border: none; }")

    def fillBackground(self):
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), Qt.black)
        self.setPalette(palette)

    def keyReleaseEvent(self, e):
        message = ""
        time, precision = (self.timeentry.getText(), self.precisionentry.getText())
        try:
            time = float(time)
        except ValueError:
            message += "time must be a number"

        try:
            precision = float(precision)
        except ValueError:
            if len(message):
                message += "\n"
            message += "precision must be a number"

        if isinstance(time, float) and isinstance(precision, float):
            if precision <= 0 or time <= 0:
                if len(message):
                    message += "\n"
                message += "all parameters must be positive"
            elif time < precision:
                message = "time must be greater than precision"
            else:
                message = ""
        self.infolabel.setText(message)

        if not len(message):
            self.setbutton.setDisabled(False)
        else:
            self.setbutton.setDisabled(True)

    def createWorld(self):
        time = float(self.timeentry.getText())
        precision = float(self.precisionentry.getText())
        interactions = self.interactions.isChecked()
        self.mainwindow.newWorld(time, precision, interactions)
        self.mainwindow.showSettings()


class FileExplorer(QListWidget):

    pathChanged = Signal(str)
    fileChosen = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("fileList")
        self.path = os.getcwd()
        self.directory = os.scandir(self.path)
        self.showDirectory()
        self.selected = ""

    def showDirectory(self):
        self.clear()
        try:
            self.directory = os.scandir(self.path)
        except PermissionError:
            os.chdir("..")
            self.path = os.getcwd()
            self.directory = os.scandir(self.path)
        self.pathChanged.emit(os.getcwd())

        self.addItem("\n\t<DIR>\t\t\t..\n")
        for file in self.directory:
            filetype = ""
            if file.is_dir(): filetype = "<DIR>"
            if file.is_file(): filetype = "<FILE>"
            description = "\n\t" + filetype + "\t\t\t" + file.name + "\n"

            self.addItem(description)

    def getCurrentPath(self):
        return self.path

    def mouseDoubleClickEvent(self, e):
        row = self.currentRow()
        if row > -1:
            if row == 0:
                os.chdir("..")
                self.path = os.getcwd()
                self.showDirectory()
            else:
                item = self.item(row)
                description = item.text()
                names = os.listdir(self.path)
                self.selected = names[row - 1]
                if "<DIR>" in description:
                    dirname = self.selected
                    os.chdir("./" + dirname)
                    self.path = os.getcwd()
                    self.showDirectory()
                elif "<FILE>" in description:
                    self.fileChosen.emit(self.selected)


class FileSelectorWidget(QWidget):

    def __init__(self):
        super().__init__()
        self.setObjectName("fileSelector")
        self.setContentsMargins(100, 50, 100, 50)

        self.layout = QVBoxLayout()

        self.explorer = FileExplorer()
        self.layout.addWidget(self.explorer, 10)
        self.explorer.pathChanged.connect(self.updateSelector)

        self.pathlabel = Label(self.explorer.getCurrentPath())
        self.layout.addWidget(self.pathlabel)

        self.setLayout(self.layout)

    def updateSelector(self):
        self.pathlabel.setText(self.explorer.getCurrentPath())

    def currentPath(self):
        return self.explorer.getCurrentPath()

    def refreshView(self):
        self.explorer.showDirectory()


class LoadFileWidget(FileSelectorWidget):

    loadFile = Signal(tuple)

    def __init__(self):
        super().__init__()

        self.confirm = Button("LOAD")
        self.confirm.clicked.connect(self.getFilePath)
        self.layout.addWidget(self.confirm)

        self.loadlabel = Label("")
        self.layout.addWidget(self.loadlabel)

        self.pathlabel.setStyleSheet("border: 1px solid #00770D;")
        self.explorer.fileChosen.connect(self.getFileName)

        self.filename = ""

    def getFileName(self, path):
        self.filename = path
        self.loadlabel.setText("Selected: " + path)

    def getFilePath(self):
        directory = os.getcwd() + "/"
        self.loadFile.emit((directory, self.filename))

    def confirmLoad(self, loaded=True):
        if loaded:
            self.loadlabel.setText("World loaded!")
        else:
            self.loadlabel.setText("ERROR")


class SaveFileWidget(FileSelectorWidget):

    saveFile = Signal(tuple)

    def __init__(self):
        super().__init__()

        self.input = Entry()
        self.layout.addWidget(self.input)

        self.confirm = Button("SAVE")
        self.confirm.clicked.connect(lambda: self.saveFile.emit(self.getFilePath()))
        self.layout.addWidget(self.confirm)

        self.savelabel = Label("")
        self.layout.addWidget(self.savelabel)

        self.pathlabel.setStyleSheet("border: 1px solid #00770D;")

    def getFilePath(self):
        filename = self.input.text()
        if len(filename):
            return self.currentPath(), filename
        else:
            return self.currentPath(), ""

    def confirmSave(self, saved=True):
        if saved:
            self.savelabel.setText("World saved!")
        else:
            self.savelabel.setText("ERROR")
