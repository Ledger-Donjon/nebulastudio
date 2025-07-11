#!/usr/bin/python3
import sys
from .application import NebulaStudioApplication
from .utils.colors import LedgerStyle, LedgerPalette


def main():
    app = NebulaStudioApplication(sys.argv)
    app.setStyle(LedgerStyle)
    app.setPalette(LedgerPalette)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
