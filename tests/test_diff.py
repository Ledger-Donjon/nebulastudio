from nebulastudio.diff import normalize_to_8bits


def test_normalize_to_8bits():
    import numpy as np

    # Test with a simple case
    image = np.array([[0, 128, 255], [64, 192, 32]], dtype=np.uint64)
    normalized_image = normalize_to_8bits(image)

    # Check the shape and dtype
    assert normalized_image.shape == (2, 3)
    assert normalized_image.dtype == np.uint8

    # Check the values
    expected = np.array([[0, 128, 255], [64, 192, 32]], dtype=np.uint8)
    np.testing.assert_array_equal(normalized_image, expected)
