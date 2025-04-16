from PIL import Image
from PIL.ImageQt import ImageQt
import numpy
from PyQt6.QtGui import QPixmap


def normalize_to_8bits(
    image: numpy.ndarray[tuple[int, int], numpy.dtype[numpy.uint64]],
):
    """
    Convert a 64-bit image to an 8-bit image.
    """
    # Normalize the image to the range [0, 255]
    min, max = int(image.min()), int(image.max())
    image -= min
    if max != min:
        image *= 255
        image //= max - min
    norm_image = image.clip(min=0, max=255)

    # Convert to uint8
    return norm_image.astype(numpy.uint8)


def make_rgb_pixmap(image: numpy.ndarray) -> QPixmap:
    """
    Convert a numpy array to a QPixmap.
    """
    # Convert the numpy array to a PIL image
    pil_image = Image.fromarray(image.astype(numpy.uint8))

    # Convert the PIL image to a QPixmap
    qimage = ImageQt(pil_image)
    pixmap = QPixmap.fromImage(qimage)

    return pixmap


def construct_diff_ndarray(
    image: numpy.ndarray,
    reference: numpy.ndarray,
) -> numpy.ndarray[tuple[int, int, int], numpy.dtype[numpy.uint64]]:
    width, height = image.shape
    zer = numpy.zeros((width, height), dtype=numpy.uint64)
    pos = (
        (image - reference)
        .astype(numpy.int64)
        .clip(min=0)
        .astype(numpy.uint64)
        .reshape(width, height)
    )

    neg = (
        (reference - image)
        .astype(numpy.int64)
        .clip(min=0)
        .astype(numpy.uint64)
        .reshape(width, height)
    )
    return numpy.stack([neg, pos, zer], axis=2).reshape(width, height, 3)
