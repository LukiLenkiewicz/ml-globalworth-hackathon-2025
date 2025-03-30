import json
from openai import OpenAI
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from dotenv import load_dotenv


from globalworth.inpainting.pipeline import get_pipeline, generate_inpainted_image
from globalworth.inpainting.api import read_image, encode_image
from globalworth.inpainting.openai import get_inpainting_prompts
from globalworth.inpainting.models import OfficeDesignRequest, InpaintModification

load_dotenv()

app = FastAPI()
pipeline = get_pipeline()
client = OpenAI()


@app.post("/get-initial-design")
async def process_images(
    data: OfficeDesignRequest
):  
    prompts = get_inpainting_prompts(client, data)
    images = data.images.value

    if len(images) != len(prompts):
        return JSONResponse(
            status_code=400,
            content={"error": "Number of images and prompts must be equal."},
        )

    results = []

    for image, prompt in zip(images, prompts):
        pil_image = await read_image(image)
        image = generate_inpainted_image(pipeline, pil_image, prompt)
        image = encode_image(image)

        results.append(
            {
                "image": image,
                "prompt": prompt,
            }
        )
    return JSONResponse(content={"results": results})


@app.post("/modify-design")
async def modify_image(
    data: InpaintModification
):
    image = data.image
    prompt = data.prompt

    pil_image = await read_image(image)
    image = generate_inpainted_image(pipeline, pil_image, prompt)
    image = encode_image(image)
    results = []
    results.append(
        {
            "image": image,
            "prompt": prompt,
        }
    )
    return JSONResponse(content={"results": results})
