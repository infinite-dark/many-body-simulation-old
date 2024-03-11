from PySide2.QtCore import *
from PySide2.QtWidgets import *

class MenuButton(QPushButton):

    def __init__(self):
        super(MenuButton, self).__init__()
        self.setMinimumSize(90, 90)
        self.setObjectName("menuButton")

class BaseProperties(QWidget):

    def __init__(self):
        super().__init__()
        self.setMinimumWidth(180)
        self.setFixedHeight(50)
        if not isinstance(self, QPushButton):
            self.setAlignment(Qt.AlignCenter)


class Label(QLabel, BaseProperties):

    def __init__(self, text: str):
        super().__init__()
        self.setText(text)
        self.setMinimumWidth(140)


class Button(QPushButton, BaseProperties):

    def __init__(self, text: str):
        super().__init__()
        self.setText(text)


class Entry(QLineEdit, BaseProperties):

    def __init__(self):
        super().__init__()


class LabeledEntry(QWidget):

    def __init__(self, ltext):
        super().__init__()
        self.entry = Entry()

        self.setLayout(QHBoxLayout())
        self.layout().addWidget(Label(ltext), 1)
        self.layout().addWidget(self.entry, 2)

        self.entry.setDisabled(True)

    def getText(self):
        return self.entry.text()

    def setText(self, text):
        self.entry.setText(text)

    def isDisabled(self, value=None):
        if value is None:
            return self.entry.isEnabled()
        else:
            self.entry.setDisabled(value)

    def setPlaceholderText(self, text: str):
        self.entry.setPlaceholderText(text)
