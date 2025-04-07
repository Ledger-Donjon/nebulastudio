#!/usr/bin/python3
import sys
from .nebulastudio import NebulaStudioApplication


def main():
    app = NebulaStudioApplication(sys.argv)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
