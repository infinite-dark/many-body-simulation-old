#from wmzf.simulation import *
import os, datetime


class ListParser:
    def __init__(self, string):
        if not isinstance(string, str):
            raise TypeError("[ERROR] Argument must be a string.")
        self.string = string
        self.illegal_characters = " \n\t\'\"()[]{}_;:!?*~`*/\\+"
        self.clearup_characters = "-."

    def parse(self):
        for character in self.illegal_characters:
            self.string = self.string.replace(character, "")

        self.string = self.string.split(",")

        for i in range(len(self.string)):
            substring = list(self.string[i])
            if not len(substring):
                continue
            negative = (substring[0] == "-")
            for character in self.clearup_characters:
                while substring.count(character) > self.clearup_characters.index(character):
                    substring.remove(character)
            if negative:
                substring.insert(0, "-")
            substring = "".join(substring)
            self.string[i] = substring

        while self.string.count("") > 0:
            self.string.remove("")

        for i in range(len(self.string)):
            self.string[i] = float(self.string[i])

        return self.string


class SimulationParser:

    def __init__(self, line: str):
        nameset = ("PARTICLE", "FIELD", "SIMULATION")
        keysets = (("M", "C", "R", "V", "S"), ("E", "M"), ("T", "P", "I"))
        keyset = nameset.index(line[:line.index(" ")])

        if keyset < 0:
            raise TypeError("[ERROR] Undefined element.")
        if not all((key in line[line.index(" "):]) for key in keysets[keyset]):
            raise ValueError("[ERROR] Broken line.")
        self.line = line.replace("\n", "")
        self.keys = keysets[keyset]

    def parse(self):
        values = []

        space = self.line.index(" ") + 1
        self.line = self.line[space:]
        self.line = self.line.replace(", ", ",").split(" ")

        if "" in self.line:
            self.line.remove("")

        for i in range(len(self.line)):
            colon = self.line[i].index(":") + 1
            values.append(self.line[i][colon:])

        for i in range(len(values)):
            try:
                values[i] = float(values[i])
            except ValueError:
                try:
                    listparser = ListParser(values[i])
                    values[i] = listparser.parse()
                except ValueError:
                    values[i] = None
        if None in values:
            raise ValueError("[ERROR] Broken parameter line.")
        else:
            return values


class SimulationSaver:

    def __init__(self, name="", path="."):
        self.destination = ""
        self.name = ""
        self.path = ""

        if name == "":
            self.name = "simulation-" + datetime.datetime.now().strftime("%H-%M-%S-%d-%m-%Y") + ".txt"
        else:
            self.name = name

        if path != "." and not path.endswith("/"):
            self.path = path + "/"

        self.destination = self.path + self.name

        directory = os.listdir(path)
        directory = filter(lambda file: file.endswith(".txt"), directory)
        if self.name in directory:
            self.name = "simulation-" + datetime.datetime.now().strftime("%H-%M-%S-%d-%m-%Y") + ".txt"

    def save(self, world):
        fields = (world.getElectric(), world.getMagnetic())
        particles = tuple(world.getParticles())

        paramstring = str(world)
        fieldstring = "FIELD "
        for field in fields:
            fieldstring += str(field) + " "
        fieldstring = fieldstring[:-1]

        particlelines = []
        for particle in particles:
            particlelines.append(str(particle))

        try:
            with open(self.destination, "w") as simfile:
                simfile.write(paramstring + "\n")
                simfile.write(fieldstring + "\n")
                for line in particlelines:
                    simfile.write(line + "\n")
        except IOError:
            print("[ERROR] Could not write to file", self.destination)


class SimulationLoader:

    def __init__(self, name="", path="."):
        directory = os.listdir(path)
        if name == "" or name not in directory:
            raise IOError("[ERROR] No such file.")
        else:
            self.source = int(path != ".")*(path + int(path.endswith("/"))*"/") + name
            self.data = None

    def load(self):
        self.loadFile()
        if self.data is not None:
            for i in range(len(self.data)):
                line = self.data[i]
                parser = SimulationParser(line)
                self.data[i] = parser.parse()
            return self.data
        else:
            return None

    def loadFile(self):
        try:
            with open(self.source) as simfile:
                self.data = simfile.readlines()
        except IOError:
            print("[ERROR] Could not read file", self.source)

        if not self.data[0].startswith("SIMULATION"):
            raise AttributeError("[ERROR] Invalid data format - no simulation parameters")
        if not any(line.startswith("PARTICLE") for line in self.data):
            raise AttributeError("[ERROR] Invalid data format - no particles in the system")
