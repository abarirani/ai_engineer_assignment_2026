import torch
from diffusers import Flux2KleinPipeline
from PIL import Image

device = "cuda"
dtype = torch.bfloat16

pipe = Flux2KleinPipeline.from_pretrained("black-forest-labs/FLUX.2-klein-4B", torch_dtype=dtype)
pipe.enable_model_cpu_offload()  # save some VRAM by offloading the model to CPU

image = Image.open("/home/owner/Pictures/Screenshots/Screenshot_20260326_093800.png")

prompt = "Make the logo be more vibrant."
image = pipe(
    image=image,
    prompt=prompt,
    height=image.height,
    width=image.width,
    guidance_scale=1.0,
    num_inference_steps=4,
    generator=torch.Generator(device=device).manual_seed(0)
).images[0]
image.save("flux-klein.png")
