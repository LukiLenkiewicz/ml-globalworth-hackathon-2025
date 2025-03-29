# ml-globalworth-hackathon-2025


## Inpaint API usage
Assuuming that service for inpainting runs on port 8000 run:
```
files = [
    ("images", ("image.jpg", open("image.jpg", "rb"), "image/jpeg")),
]

data = [
    ("prompts", "Desk and pool table"),
]

response = requests.post(
    "http://127.0.0.1:8000/process-images/", files=files, data=data
)
```