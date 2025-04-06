#!/usr/bin/python3
from PyQt6.QtWidgets import QApplication, QVBoxLayout
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QLocale
import sys
from .nebulastudio import NebulaStudio


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Nebula Studio")
    win = NebulaStudio()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
