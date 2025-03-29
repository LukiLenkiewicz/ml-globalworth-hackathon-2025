import base64
from io import BytesIO
from PIL import Image


async def read_image(image):
    content = await image.read()
    pil_image = Image.open(BytesIO(content))
    pil_image = pil_image.resize((512, 512))
    return pil_image


def encode_image(img):
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return encoded


def base64_to_image(base64_str: str) -> Image.Image:
    image_data = base64.b64decode(base64_str)
    return Image.open(BytesIO(image_data))