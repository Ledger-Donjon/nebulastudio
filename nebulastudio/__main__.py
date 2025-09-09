#!/usr/bin/python3
import sys
import logging
from .application import NebulaStudioApplication
from .utils.colors import LedgerStyle, LedgerPalette


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    app = NebulaStudioApplication(sys.argv)
    app.setStyle(LedgerStyle)
    app.setPalette(LedgerPalette)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
