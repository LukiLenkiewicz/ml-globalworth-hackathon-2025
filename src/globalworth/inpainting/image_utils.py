import numpy as np
from PIL import Image


def generate_center_white_image(width=256, height=256, central_ratio=0.75):
    assert 0 < central_ratio < 1, "central_ratio must be between 0 and 1"

    image = np.zeros((height, width), dtype=np.uint8)

    margin_x = int(width * (1 - central_ratio) / 2)
    margin_y = int(height * (1 - central_ratio) / 2)

    image[margin_y : height - margin_y, margin_x : width - margin_x] = 255

    return Image.fromarray(image)
