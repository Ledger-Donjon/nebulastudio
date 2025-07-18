import numpy
from PyQt6.QtGui import QPixmap, QImage


def normalize_to_8bits(
    image: numpy.ndarray[tuple[int, int], numpy.dtype[numpy.uint64]], min=None, max=None
):
    """
    Convert a 64-bit image to an 8-bits image.
    """
    # Normalize the image to the range [0, 255]
    if min is None or max is None:
        # If min and max are not provided, calculate them from the image
        min, max = image.min(), image.max()
    image -= min
    if max != min:
        image *= 255
        image //= max - min
    norm_image = image.clip(min=0, max=255)

    # Convert to uint8
    return norm_image.astype(numpy.uint8).squeeze()


def apply_balances(
    image: numpy.ndarray,
    balances: tuple[float, float],
) -> numpy.ndarray[tuple[int, int, int], numpy.dtype[numpy.uint8]]:
    """
    Apply the balance to the image.
    The balance is a tuple of two floats, where the first float is the minimum value
    and the second float is the maximum value. The image is expected to be in the range
    [0, 1] for each channel.
    """
    if balances[0] == 0.0 and balances[1] == 1.0:
        return image

    # Apply the balance to the image
    image = image.astype(numpy.float32)
    image -= balances[0] * 255
    image /= balances[1] - balances[0]
    image = image.clip(min=0, max=255).astype(numpy.uint8)
    return image


def make_rgb_pixmap(
    image: numpy.ndarray, balances=(0.0, 1.0), minmax: tuple[int, int] | None = None
) -> QPixmap:
    """
    Convert a numpy array to a QPixmap.
    """
    # Make a copy of the image to avoid modifying the original
    image = image.astype(numpy.uint64)
    # Convert the numpy array to a PIL image
    image = normalize_to_8bits(
        image, min=minmax[0] if minmax else None, max=minmax[1] if minmax else None
    )
    image = apply_balances(image, balances)
    qimage = QImage(
        image.tobytes(),
        image.shape[1],
        image.shape[0],
        # Use strides to ensure correct memory layout
        image.strides[0],
        QImage.Format.Format_Grayscale8
        if image.ndim == 2
        else QImage.Format.Format_RGB888,
    )
    return QPixmap.fromImage(qimage)


def construct_diff_ndarray(
    image: numpy.ndarray,
    reference: numpy.ndarray,
) -> numpy.ndarray[tuple[int, int, int], numpy.dtype[numpy.uint64]]:
    width, height = image.shape[:2]
    zer = numpy.zeros((width, height), dtype=numpy.uint64)
    pos = (
        (image - reference)
        .astype(numpy.int64)
        .clip(min=0)
        .astype(numpy.uint64)
        .reshape(width, height)
    ).copy()

    neg = (
        (reference - image)
        .astype(numpy.int64)
        .clip(min=0)
        .astype(numpy.uint64)
        .reshape(width, height)
    ).copy()
    return numpy.stack([neg, pos, zer], axis=2).reshape(width, height, 3).copy()
