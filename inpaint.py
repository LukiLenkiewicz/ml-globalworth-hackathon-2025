from typing import List
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse

from globalworth.inpainting.pipeline import get_pipeline, generate_inpainted_image
from globalworth.inpainting.api import read_image, encode_image



app = FastAPI()
pipeline = get_pipeline()


@app.post("/process-images")
async def process_images(
    images: List[UploadFile] = File(...), prompts: List[str] = Form(...)
):
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
