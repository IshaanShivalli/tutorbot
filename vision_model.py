import base64
import os
from pathlib import Path

from llama_cpp import Llama
from llama_cpp.llama_chat_format import MTMDChatHandler

from config import IMAGE_MODEL_PATH, IMAGE_MMPROJ_PATH

cpu_threads = max(1, min(4, os.cpu_count() or 2))

_vision_llm = None
_vision_load_error = None


def _load_vision_model():
    global _vision_llm, _vision_load_error

    if _vision_llm is not None or _vision_load_error is not None:
        return

    if not Path(IMAGE_MODEL_PATH).exists():
        _vision_load_error = f"Vision model not found at '{IMAGE_MODEL_PATH}'."
        return
    if not Path(IMAGE_MMPROJ_PATH).exists():
        _vision_load_error = (
            f"Vision projector (mmproj) not found at '{IMAGE_MMPROJ_PATH}'. "
            "Download the matching mmproj-*.gguf for SmolVLM-256M-Instruct "
            "and place it there -- image analysis cannot work without it."
        )
        return

    try:
        chat_handler = MTMDChatHandler(clip_model_path=IMAGE_MMPROJ_PATH, verbose=False)
        _vision_llm = Llama(
            model_path=IMAGE_MODEL_PATH,
            chat_handler=chat_handler,
            n_ctx=4096,
            n_threads=cpu_threads,
            n_batch=128,
            n_gpu_layers=0,
            use_mmap=True,
            use_mlock=False,
            verbose=False,
        )
    except Exception as exc:
        _vision_load_error = f"Failed to load vision model: {exc}"


def _image_to_data_uri(image_path: Path) -> str:
    ext = image_path.suffix.lower().lstrip(".") or "png"
    if ext == "jpg":
        ext = "jpeg"
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/{ext};base64,{b64}"


def describe_image(image_path: Path) -> str:
    _load_vision_model()

    if _vision_load_error:
        return f"Image description unavailable: {_vision_load_error}"

    try:
        data_uri = _image_to_data_uri(Path(image_path))

        prompt = (
            "You are a lightweight image analysis assistant. Look at the image and describe what is "
            "actually shown, in clear student-friendly language. Mention visible objects, any readable "
            "text, layout, and colors. Only describe what you can actually see -- do not guess at things "
            "not visible in the image."
        )

        response = _vision_llm.create_chat_completion(
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": data_uri}},
                        {"type": "text", "text": "Describe what is shown in this image."},
                    ],
                },
            ],
            max_tokens=256,
            temperature=0.2,
            top_p=0.9,
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        return f"Image description failed: {exc}"