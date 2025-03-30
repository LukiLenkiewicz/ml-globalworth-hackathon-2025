from PIL import Image
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from globalworth.inpainting.api import encode_image
from globalworth.inpainting.models import OfficeDesignRequest, InpaintModification

load_dotenv()

app = FastAPI()

IMAGES = [
    "office_mocks/space1/empty_office_3_1_inpaint.png",
    "office_mocks/space2/empty_office_3_2_inpaint.png",
    "office_mocks/space3/empty_office_3_3_inpaint.png"
]

FIXED_IMAGES = [
    "office_mocks/space3/empty_office_3_3_inpaint2.png",
    "office_mocks/space3/empty_office_3_3_inpaint3.png"
]

@app.post("/get-initial-design")
async def process_images(
    data: OfficeDesignRequest
):  
    results = []

    for image in IMAGES:
        pil_image = Image.open(image)
        image = encode_image(pil_image)

        results.append(
            {
                "image": image,
                "prompt": "custom prompt",
            }
        )
    return JSONResponse(content={"results": results})


@app.post("/modify-design")
async def modify_image(
    data: InpaintModification
):
    image = FIXED_IMAGES.pop(0)
    pil_image = Image.open(image)
    image = encode_image(pil_image)

    results = []
    results.append(
        {
            "image": image,
            "prompt": "custom prompt",
        }
    )
    return JSONResponse(content={"results": results})
