import os
from pathlib import Path
from llama_cpp import Llama
from PIL import Image, ImageStat

from config import IMAGE_MODEL_PATH

cpu_threads = max(1, min(4, os.cpu_count() or 2))
vision_llm = Llama(
    model_path=IMAGE_MODEL_PATH,
    n_ctx=4096,
    n_threads=cpu_threads,
    n_batch=128,
    n_gpu_layers=0,
    use_mmap=True,
    use_mlock=False,
    verbose=False,
)


def analyze_image_layout(image: Image.Image) -> str:
    width, height = image.size
    stat = ImageStat.Stat(image)
    mean = stat.mean
    grayscale = all(abs(mean[i] - mean[0]) < 12 for i in range(1, len(mean)))
    aspect = width / height if height else 1
    mode_text = "grayscale" if grayscale else "color"

    histogram = image.convert("HSV").histogram()
    hue_values = histogram[0:256]
    dominant_hue = hue_values.index(max(hue_values)) if sum(hue_values) else 0
    desc = [f"Image dimensions are {width}×{height}", f"visual mode is {mode_text}", f"aspect ratio is {aspect:.2f}"]

    if dominant_hue < 43:
        desc.append("the image has a warm hue tint")
    elif dominant_hue < 85:
        desc.append("the image has a greenish tint")
    elif dominant_hue < 171:
        desc.append("the image has a cool blue tint")
    else:
        desc.append("the image has a purple/red tint")

    return ". ".join(desc) + "."


def describe_image(image_path: Path) -> str:
    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            width, height = img.size
            layout_description = analyze_image_layout(img)

        prompt = (
            "You are a lightweight image analysis assistant. Based on the image features and any detected text, "
            "describe what is shown in clear student-friendly language. Emphasize visible content and avoid guesses. "
            "Use only observations that could be directly inferable from the image."
        )

        response = vision_llm.create_chat_completion(
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": (
                        f"Image size: {width}x{height}. "
                        f"Summary of visual features: {layout_description} "
                        "If the image shows text, diagrams, or objects, describe them as accurately as possible."
                    ),
                },
            ],
            max_tokens=256,
            temperature=0.2,
            top_p=0.9,
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        return f"Image description failed: {exc}"
