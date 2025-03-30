import numpy as np

import torch
from diffusers import AutoPipelineForInpainting

from globalworth.inpainting.image_utils import generate_center_white_image


def get_pipeline():
    pipeline = AutoPipelineForInpainting.from_pretrained(
        "runwayml/stable-diffusion-inpainting",
        torch_dtype=torch.float16,
        variant="fp16",
    )

    pipeline.enable_model_cpu_offload()
    pipeline.enable_xformers_memory_efficient_attention()
    return pipeline


def generate_inpainted_image(pipeline, image, prompt):
    mask_image = generate_center_white_image(
        image.size[0], image.size[1], central_ratio=0.80
    )
    blurred_mask = pipeline.mask_processor.blur(mask_image, blur_factor=33)
    # generator = torch.Generator("cuda").manual_seed(92)
    image = pipeline(
        prompt=prompt,
        image=image,
        mask_image=blurred_mask,  # generator=generator
    ).images[0]
    return image
