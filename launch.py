from wmzf.gui import *
import sys


class MainApplication(QApplication):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.w = SimulationWindow()
        self.w.show()
        self.exec_()


if __name__ == "__main__":
    MainApplication(sys.argv)

