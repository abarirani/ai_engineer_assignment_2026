from google import genai
from PIL import Image

client = genai.Client()

prompt = ("Make the logo be more vibrant.",)

image = Image.open("/home/owner/Pictures/Screenshots/Screenshot_20260326_093800.png")

response = client.models.generate_content(
    model="gemini-3.1-flash-image-preview",
    contents=[prompt, image],
)

for part in response.parts:
    if part.text is not None:
        print(part.text)
    elif part.inline_data is not None:
        image = part.as_image()
        image.save("generated_image.png")
