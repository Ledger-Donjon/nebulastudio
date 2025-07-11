import pytest
from nebulastudio.nebulaimage import NebulaImage
from os import path
from nebulastudio.application import NebulaStudioApplication
import numpy as np
from hashlib import md5


@pytest.fixture
def app():
    return NebulaStudioApplication([])


def test_nebula_image_initialization_png(app):
    # Test the initialization of NebulaImage with a valid image URL
    image_url = "images/tests/7_1_pe_counter0.png"
    nebula_image = NebulaImage(image_url)

    assert nebula_image.image_url == image_url
    assert nebula_image.reference_url is None
    assert nebula_image.image is not None
    assert nebula_image.diff_image is None
    assert nebula_image.reference_image is None
    assert nebula_image.pattern is None
    assert nebula_image.balances == (0.0, 1.0)

    # Get hash of the image data
    load = np.load(image_url)
    assert load.shape == (512, 640, 1)
    assert load.dtype == np.uint64
    data = load.tobytes()
    data2 = nebula_image.image.tobytes()


def test_nebula_image_initialization():
    # Test the initialization of NebulaImage with a valid image URL
    image_url = "images/tests/7_1_pe_counter0.npy"
    reference_url = "images/tests/zeros.npy"

    nebula_image = NebulaImage(image_url, reference_url)

    assert nebula_image.image_url == image_url
    assert nebula_image.reference_url == reference_url
    assert nebula_image.image is not None
    assert nebula_image.diff_image is not None
    assert nebula_image.reference_image is not None
    assert nebula_image.pattern is None
    assert nebula_image.balances == (0.0, 1.0)

    # Get hash of the image data
    load = np.load(image_url)
    assert load.shape == (512, 640, 1)
    assert load.dtype == np.uint64
    data = load.tobytes()
    data2 = nebula_image.image.tobytes()
    assert data == data2
    assert md5(data2).digest() == md5(data).digest()
    assert md5(data2).digest() == b"\xdah2\xb7\xa5\x00\x95\x03\t\x9ak\xb2\x1c\xea\x7fr"

    assert (
        nebula_image.reference_image.tobytes() == b"\x00" * 512 * 640 * 8
    )  # Reference image is all zeros

    # Get the second channel of the diff image
    pos = nebula_image.diff_image[:, :, 1]
    assert pos.shape == (512, 640)
    assert pos.dtype == np.uint64

    original = nebula_image.image.squeeze()
    assert original.shape == (512, 640)
    assert original.dtype == np.uint64

    assert (original == pos).all()
    assert (0 == nebula_image.diff_image[:, :, 0]).all()
    assert (0 == nebula_image.diff_image[:, :, 2]).all()

    assert (
        pos.tobytes() == original.tobytes()
    )  # Diff image should match the original image
