import pyttsx3 as pt3


def say_text(text: str) -> None:
    """Speak the given text aloud using pyttsx3."""
    try:
        engine = pt3.init()
        engine.say(text)
        engine.runAndWait()
    except Exception:
        # Fail silently so the main app can continue without audio.
        pass
