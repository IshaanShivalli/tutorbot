from pathlib import Path
from vision_model import describe_image

image = Path("test.jpg")

if not image.exists():
    print("ERROR: test.jpg not found")
    exit()

print("Loading image model...")
print("Image:", image)

result = describe_image(image)

print("\n===== RESULT =====")
print(result)
print("==================")