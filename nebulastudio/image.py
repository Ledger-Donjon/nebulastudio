from PyQt6.QtWidgets import (
    QGraphicsPixmapItem,
)
from PyQt6.QtGui import QPixmap
import os
import numpy
from .diff import make_rgb_pixmap


class NebulaImage(QGraphicsPixmapItem):
    """
    A class representing an image in Nebula Studio.
    """

    def __init__(self, image_url: str):
        """
        Initializes the NebulaImage instance.

        Args:
            image_url (str): The URL of the image.
        """
        super().__init__()
        self.image_url = image_url
        self.numpy_image = None
        self.load_file(self.image_url)

    def load_file(self, filename: str):
        if not (os.path.exists(filename) and os.path.isfile(filename)):
            raise FileNotFoundError(f"File {filename} does not exist")

        if filename.endswith(".npy"):
            # Load the image from the numpy file
            image = numpy.load(filename)
            # Convert the image to a QPixmap
            pixmap = make_rgb_pixmap(image)
        else:
            # Load the image from the file
            pixmap = QPixmap(filename)
            # Convert the image to a numpy array
            image = None

        # assert pixmap.isNull(), f"Failed to load image: {self.image_url}"

        self.image_url = filename
        self.numpy_image = image
        self.setPixmap(pixmap)
