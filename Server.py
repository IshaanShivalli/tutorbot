import json
import re
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from PIL import Image
from werkzeug.utils import secure_filename
from werkzeug.serving import run_simple
import pytesseract
import socket
import smtplib
from email.mime.text import MIMEText
import random
from urllib.parse import quote
import requests
from config import SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_USE_TLS, SYSTEM_PROMPT

from vision_model import describe_image
from model import ask_ai
from context_fetcher import get_context_for_topic
from doc_generator import create_quiz_and_answer_key, create_quiz_document
from quiz_generator import generate_quiz, reformat_quiz_for_doc
from ui.commands import COMMANDS
from ui import user_management, analytics, gamification

# ---- Reader Mode: optional doc-parsing libraries, imported lazily/safely ----
try:
    import pdfplumber
    HAVE_PDFPLUMBER = True
except ImportError:
    HAVE_PDFPLUMBER = False

try:
    import docx as python_docx  # python-docx package
    HAVE_DOCX = True
except ImportError:
    HAVE_DOCX = False

verification_codes = {}


def send_otp_email(to_email: str, otp: str):
    msg = MIMEText(f"Your TutorBot verification code is: {otp}\n\nUse this code to complete registration/login.")
    msg["Subject"] = "TutorBot Verification OTP"
    msg["From"] = SMTP_USER
    msg["To"] = to_email

    try:
        if SMTP_USE_TLS:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, [to_email], msg.as_string())
        server.quit()
        return True
    except Exception as exc:
        print(f"[SMTP] Error sending email: {exc}")
        return False


ROOT_DIR = Path(__file__).resolve().parent
WEB_DIR = ROOT_DIR / "web"
UPLOAD_DIR = ROOT_DIR / "uploads"
DOWNLOAD_DIR = ROOT_DIR / "downloads"

UPLOAD_DIR.mkdir(exist_ok=True)
DOWNLOAD_DIR.mkdir(exist_ok=True)

chat_history = []
MAX_HISTORY_MESSAGES = 12  # keep last ~6 user/assistant exchanges to stay within the model's context window

# Message-count alone doesn't protect against a single huge message (e.g. a
# reader-mode doc dump can be ~12,000 chars / ~3000 tokens). If that sits in
# history for a few turns, prompt + max_tokens can exceed the model's n_ctx
# and llama.cpp aborts the whole process with a native GGML_ASSERT -- not a
# Python exception, so no try/except can catch it. These are conservative
# safety limits (roughly 4 chars/token) applied on every call so the request
# sent to the model can never exceed a safe context budget.
SAFE_CONTEXT_TOKENS = 3800          # assume a conservative n_ctx; trim to fit under it
CHARS_PER_TOKEN_ESTIMATE = 4


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN_ESTIMATE)


def _trim_history_to_budget(history: list, reserved_tokens: int) -> list:
    """Drop oldest messages until the remaining history fits the token budget
    left over after reserving space for the system prompt and the reply."""
    budget = max(200, SAFE_CONTEXT_TOKENS - reserved_tokens)
    trimmed = list(history)
    while trimmed:
        total = sum(_estimate_tokens(m.get("content", "")) for m in trimmed)
        if total <= budget:
            break
        trimmed.pop(0)  # drop oldest first
    return trimmed

last_quiz_content = None
last_quiz_doc_content = None
last_quiz_topic = "quiz"
last_quiz_grade = "Grade 9"
esp32_settings = {"ssid": "", "password": ""}

app = Flask(__name__, static_folder=str(WEB_DIR), static_url_path="")
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0  # disable Flask's default static-file caching
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)


@app.after_request
def _disable_caching(response):
    # Without this, browsers keep reusing a stale cached copy of app.js /
    # styles.css (you'll see "304 Not Modified" in this server's log for
    # them) even after the files on disk have changed -- so a real fix can
    # look like it "didn't work" when it's actually just not being loaded.
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


def _read_request_data() -> dict:
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        data = request.form.to_dict() or {}
        if not data:
            try:
                payload = request.get_data(as_text=True)
                if payload:
                    data = json.loads(payload)
            except (TypeError, ValueError):
                data = {}
    return data if isinstance(data, dict) else {}


def _normalize_auth_mode(mode: str) -> str:
    normalized = str(mode or "").strip().lower()
    if normalized in {"register", "registration", "signup", "sign_up"}:
        return "register"
    if normalized in {"login", "signin", "sign_in"}:
        return "login"
    return "login"


MODEL_INFO = {
    "Model": "Qwen2.5 0.5B Instruct",
    "Format": "GGUF (Q4_K_M)",
    "Context": "8192 tokens",
    "Device": "CPU",
    "Backend": "llama.cpp",
}

SUPPORTED_LANGUAGES = {
    "english": "English",
    "hindi": "Hindi",
    "kannada": "Kannada",
    "tamil": "Tamil",
    "telugu": "Telugu",
    "malayalam": "Malayalam",
    "marathi": "Marathi",
    "bengali": "Bengali",
    "gujarati": "Gujarati",
    "spanish": "Spanish",
    "french": "French",
    "german": "German",
    "portuguese": "Portuguese",
    "italian": "Italian",
    "arabic": "Arabic",
    "chinese": "Chinese",
    "japanese": "Japanese",
    "korean": "Korean",
    "russian": "Russian",
}

GOOGLE_TRANSLATE_CODES = {
    "english": "en",
    "hindi": "hi",
    "kannada": "kn",
    "tamil": "ta",
    "telugu": "te",
    "malayalam": "ml",
    "marathi": "mr",
    "bengali": "bn",
    "gujarati": "gu",
    "spanish": "es",
    "french": "fr",
    "german": "de",
    "portuguese": "pt",
    "italian": "it",
    "arabic": "ar",
    "chinese": "zh-CN",
    "japanese": "ja",
    "korean": "ko",
    "russian": "ru",
}


def normalize_language(language: str) -> str:
    if not language:
        return "English"
    return SUPPORTED_LANGUAGES.get(str(language).strip().lower(), str(language).strip() or "English")


def google_translate(text: str, target_language: str, source_language: str = "auto") -> str:
    text = str(text or "")
    target_language = normalize_language(target_language)
    target_code = GOOGLE_TRANSLATE_CODES.get(target_language.lower(), "en")
    source_code = GOOGLE_TRANSLATE_CODES.get(str(source_language).lower(), source_language or "auto")
    if not text.strip() or target_code == source_code == "en":
        return text
    try:
        url = (
            "https://translate.googleapis.com/translate_a/single"
            f"?client=gtx&sl={quote(source_code)}&tl={quote(target_code)}&dt=t&q={quote(text)}"
        )
        response = requests.get(url, timeout=12)
        response.raise_for_status()
        payload = response.json()
        translated = "".join(part[0] for part in payload[0] if part and part[0])
        return translated or text
    except Exception as exc:
        print(f"[Translate] Google Translate failed: {exc}")
        return text


def tutorbot_reply(prompt: str, language: str = "English", profile: dict = None, force_english: bool = False, max_tokens: int = 8192) -> str:
    language = normalize_language(language)
    english_prompt = prompt
    if language.lower() != "english":
        english_prompt = google_translate(prompt, "English", source_language=language)

    chat_history.append({"role": "user", "content": english_prompt})
    if len(chat_history) > MAX_HISTORY_MESSAGES:
        del chat_history[: len(chat_history) - MAX_HISTORY_MESSAGES]
    request_prompt = SYSTEM_PROMPT
    if profile:
        grade = str(profile.get("grade", "Grade 9") or "Grade 9")
        subject = str(profile.get("subject", "General") or "General")
        request_prompt += (
            f"\n\nThe student is currently in {grade} and wants to focus on {subject}. "
            "Tailor explanations, examples, and quiz challenges to this grade and subject focus. "
            "Keep responses aligned with the selected subject, and explain how other topics connect if needed."
        )
    request_prompt += "\n\nAlways produce the final answer in English. Do not translate it yourself."

    # Clamp the reply budget, then trim history so (system + history + reply)
    # can't exceed the safe context budget -- this is what actually prevents
    # the native crash, not a try/except.
    system_tokens = _estimate_tokens(request_prompt)
    max_tokens = max(64, min(max_tokens, SAFE_CONTEXT_TOKENS - system_tokens - 200))
    trimmed_history = _trim_history_to_budget(chat_history, reserved_tokens=system_tokens + max_tokens)
    if len(trimmed_history) < len(chat_history):
        del chat_history[: len(chat_history) - len(trimmed_history)]

    reply = ask_ai(chat_history, request_prompt, max_tokens=max_tokens)
    chat_history.append({"role": "assistant", "content": reply})
    if len(chat_history) > MAX_HISTORY_MESSAGES:
        del chat_history[: len(chat_history) - MAX_HISTORY_MESSAGES]
    if language.lower() != "english" and not force_english:
        return google_translate(reply, language, source_language="English")
    return reply


def parse_quiz_args(argument: str):
    tokens = argument.split()
    topic_tokens = []
    grade = "Grade 9"
    count = 5
    use_web = True

    for token in tokens:
        if "=" not in token:
            topic_tokens.append(token)
            continue

        key, _, value = token.partition("=")
        key = key.lower().lstrip("-")

        if key == "grade":
            grade = f"Grade {value}" if value.isdigit() else value or grade
        elif key in ("count", "questions", "question", "num"):
            try:
                count = max(1, min(20, int(value)))
            except ValueError:
                count = 5
        elif key == "web":
            use_web = value.lower() in ("y", "yes", "true", "1")

    topic = " ".join(topic_tokens).strip() or argument
    return topic, grade, count, use_web


def safe_doc_name(topic: str, suffix: str) -> Path:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", topic.strip().lower()).strip("_") or "quiz"
    return DOWNLOAD_DIR / f"{slug}_{suffix}.docx"


def extract_document_text(file_path: Path, filename: str) -> str:
    """Extract plain text from an uploaded document for Reader Mode.
    Supports .txt, .pdf (via pdfplumber), .docx (via python-docx).
    Returns "" if extraction fails or the format isn't supported.
    """
    suffix = Path(filename).suffix.lower()
    try:
        if suffix == ".txt":
            return file_path.read_text(encoding="utf-8", errors="ignore").strip()

        if suffix == ".pdf":
            if not HAVE_PDFPLUMBER:
                print("[Server] Reader Mode: pdfplumber not installed, cannot read PDF")
                return ""
            text_parts = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    if page_text:
                        text_parts.append(page_text)
            return "\n\n".join(text_parts).strip()

        if suffix == ".docx":
            if not HAVE_DOCX:
                print("[Server] Reader Mode: python-docx not installed, cannot read .docx")
                return ""
            doc = python_docx.Document(str(file_path))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n".join(paragraphs).strip()

        # .doc (legacy binary Word) is not supported without extra tooling
        return ""
    except Exception as exc:
        print(f"[Server] Reader Mode extraction failed for {filename}: {exc}")
        return ""


def extract_image_text(image_path: Path) -> str:
    try:
        with Image.open(image_path) as image:
            image = image.convert("RGB")
            variants = [image]
            gray = image.convert("L")
            variants.append(gray)
            variants.append(gray.point(lambda px: 255 if px > 165 else 0))

            results = []
            for variant in variants:
                try:
                    text = pytesseract.image_to_string(
                        variant,
                        lang="eng",
                        config="--oem 3 --psm 6",
                    ).strip()
                    if text:
                        results.append(text)
                except Exception:
                    continue
            if not results:
                return ""
            return max(results, key=len).strip()
    except Exception as exc:
        print(f"[Server] OCR failed: {exc}")
        return ""


def command_response(command_text: str, language: str = "English", profile: dict = None):
    global last_quiz_content, last_quiz_doc_content, last_quiz_topic, last_quiz_grade

    command_name, _, argument = command_text.strip().partition(" ")
    command_name = command_name.lower()
    argument = argument.strip()
    language = language or "English"
    profile = profile or {}

    if command_name == "/help":
        return {
            "type": "system",
            "response": "\n".join(f"{cmd.usage} - {cmd.description}" for cmd in COMMANDS),
        }

    if command_name == "/clear":
        chat_history.clear()
        last_quiz_content = None
        last_quiz_doc_content = None
        return {"type": "system", "response": "Conversation cleared."}

    if command_name == "/stats":
        profile_state = gamification.get_profile(streak_count=int(profile.get("streak", 0) or 0))
        weak_subject = profile.get("weakSubject") or profile.get("weak_subject") or "None"
        lines = [
            f"Level: {profile_state['level']} - {profile_state['title']} ({profile_state['xp']} XP)",
            f"Current streak: {profile_state['streak']} day(s)",
            f"Messages sent: {profile_state['messages_sent']}",
            f"Quizzes generated: {profile_state['quizzes_generated']}",
            f"Documents exported: {profile_state['docs_exported']}",
            f"Searches run: {profile_state['searches_run']}",
            f"Weak subject: {weak_subject}",
            f"Spelling score: {profile.get('spellScore', 0)}",
            f"Longest practice streak: {profile.get('longestStreak', 0)}",
        ]
        return {"type": "system", "response": "\n".join(lines)}

    if command_name == "/report":
        report = analytics.build_report(days=7)
        lines = [
            "Activity Report (last 7 days)",
            "",
            f"Messages sent: {report['messages_sent']}",
            f"Quizzes generated: {report['quizzes_generated']}",
            f"Documents exported: {report['docs_exported']}",
            f"Searches run: {report['searches_run']}",
        ]
        if report.get("first_used"):
            lines.append(f"Tracking since: {report['first_used']}")
        if report.get("top_topics"):
            lines.append("")
            lines.append("Top quiz topics:")
            lines.extend(f"- {topic.title()} ({count})" for topic, count in report["top_topics"])
        if report.get("performance_graph"):
            lines.append("")
            lines.append("Performance graph:")
            lines.extend(report["performance_graph"])
        return {"type": "system", "response": "\n".join(lines)}

    if command_name == "/model":
        return {
            "type": "system",
            "response": "\n".join(f"{key}: {value}" for key, value in MODEL_INFO.items()),
        }

    if command_name == "/language":
        if not argument:
            language_list = ", ".join(SUPPORTED_LANGUAGES.values())
            return {
                "type": "system",
                "response": f"Usage: /language <language>\nSupported: {language_list}",
            }

        normalized = SUPPORTED_LANGUAGES.get(argument.lower())
        if not normalized:
            language_list = ", ".join(SUPPORTED_LANGUAGES.values())
            return {
                "type": "error",
                "response": f"Unsupported language '{argument}'. Supported: {language_list}",
            }

        return {
            "type": "system",
            "response": f"Preferred learning language set to {normalized}.",
            "settings": {"learningLanguage": normalized},
        }

    if command_name == "/spell":
        requested_word = argument.strip()
        if not requested_word:
            return {
                "type": "assistant",
                "response": "Usage: /spell <word> — type a word you want to hear pronounced.",
            }
        return {
            "type": "assistant",
            "response": f"Sure — I will pronounce the word for you: {requested_word}",
        }

    if command_name == "/search":
        if not argument:
            return {"type": "error", "response": "Usage: /search <query>"}
        context, source = get_context_for_topic(argument)
        if not context:
            return {"type": "system", "response": f"No reference material found for '{argument}'."}
        preview = context[:1200] + ("..." if len(context) > 1200 else "")
        response_text = (
            f"Search results for '{argument}':\n"
            f"Source: {source}\n\n"
            f"{preview}"
        )
        if language.lower() != "english":
            response_text = tutorbot_reply(
                "Summarize this reference material for the student in "
                f"{language}. Keep the source title and explain the key ideas clearly.\n\n"
                f"Source: {source}\n\n{context[:2500]}",
                language=language,
                profile=profile,
            )
        return {"type": "assistant", "response": response_text}

    if command_name == "/quiz":
        if not argument:
            return {
                "type": "error",
                "response": "Usage: /quiz <topic> grade=8 count=5 web=y",
            }
        topic, grade, count, use_web = parse_quiz_args(argument)
        quiz = generate_quiz(
            topic=topic,
            grade=grade,
            number_of_questions=count,
            use_web_context=use_web,
            quiz_language=language,
        )
        last_quiz_content = quiz
        last_quiz_topic = topic
        last_quiz_grade = grade
        
        last_quiz_doc_content = reformat_quiz_for_doc(
            last_quiz_content,
            topic=last_quiz_topic,
            grade=last_quiz_grade,
        )
        
        quiz_path = safe_doc_name(last_quiz_topic, "quiz")
        create_quiz_document(last_quiz_doc_content, output_path=str(quiz_path), include_answers=False)
        
        ans_path = safe_doc_name(last_quiz_topic, "answer_key")
        create_quiz_document(last_quiz_doc_content, output_path=str(ans_path), include_answers=True)
        
        files = [
            {"name": quiz_path.name, "download_url": f"/downloads/{quiz_path.name}"},
            {"name": ans_path.name, "download_url": f"/downloads/{ans_path.name}"}
        ]
        
        return {
            "type": "assistant",
            "response": f"I've generated the quiz documents for your lesson on **{topic}** ({grade}). Click below to download them directly:",
            "files": files,
        }

    if command_name == "/doc":
        if not last_quiz_content:
            return {"type": "error", "response": "No quiz has been generated yet. Run /quiz first."}

        if last_quiz_doc_content is None:
            last_quiz_doc_content = reformat_quiz_for_doc(
                last_quiz_content,
                topic=last_quiz_topic,
                grade=last_quiz_grade,
            )

        if argument.lower() == "answers":
            path = safe_doc_name(last_quiz_topic, "quiz_with_answers")
            create_quiz_document(last_quiz_doc_content, output_path=str(path), include_answers=True)
            files = [{"name": path.name, "download_url": f"/downloads/{path.name}"}]
        elif argument.lower() == "split":
            quiz_path = safe_doc_name(last_quiz_topic, "quiz")
            answer_path = safe_doc_name(last_quiz_topic, "answer_key")
            create_quiz_and_answer_key(
                last_quiz_doc_content,
                quiz_path=str(quiz_path),
                answer_key_path=str(answer_path),
            )
            files = [
                {"name": quiz_path.name, "download_url": f"/downloads/{quiz_path.name}"},
                {"name": answer_path.name, "download_url": f"/downloads/{answer_path.name}"},
            ]
        else:
            path = safe_doc_name(last_quiz_topic, "quiz")
            create_quiz_document(last_quiz_doc_content, output_path=str(path), include_answers=False)
            files = [{"name": path.name, "download_url": f"/downloads/{path.name}"}]

        return {"type": "system", "response": "Document ready.", "files": files}

    return {
        "type": "error",
        "response": f"Unknown mobile command: {command_name}. Use /help to see commands.",
    }


@app.post("/process-image")
def process_image():
    image_file = request.files.get("image")
    if image_file is None or image_file.filename == "":
        return jsonify({"error": "Field 'image' is required."}), 400

    filename = secure_filename(image_file.filename) or "image.png"
    saved_path = UPLOAD_DIR / f"{uuid4().hex}_{filename}"
    image_file.save(saved_path)

    ocr_text = extract_image_text(saved_path)
    if not ocr_text:
        ocr_text = "No readable text was detected in the image."

    profile = request.form.get("profile")
    profile_data = {}
    if profile:
        try:
            profile_data = json.loads(profile)
        except Exception:
            profile_data = {}
    language = request.form.get("language", "English")

    image_description = describe_image(saved_path)

    image_prompt = (
        "I have processed an uploaded image using OCR and layout analysis. "
        "Report only what is visible in the image and what text was extracted. "
        "Do not infer missing words, do not make assumptions about the question, "
        "and do not solve or explain concepts unless they are clearly present in the image. "
        f"Image description:\n{image_description}\n\n"
        f"OCR text extracted from the image:\n{ocr_text}\n\n"
        "Keep the response factual and aligned with the student's grade and subject focus."
    )

    response_text = tutorbot_reply(image_prompt, language=language, profile=profile_data)
    return jsonify(
        {
            "type": "assistant",
            "response": response_text,
            "ocr_text": ocr_text,
        }
    )


@app.post("/read-document")
def read_document():
    """Reader Mode: accept an uploaded document (.txt/.pdf/.docx), extract its
    text, and have the AI read/summarize it back to the student."""
    doc_file = request.files.get("document")
    if doc_file is None or doc_file.filename == "":
        return jsonify({"error": "Field 'document' is required."}), 400

    filename = secure_filename(doc_file.filename) or "document.txt"
    saved_path = UPLOAD_DIR / f"{uuid4().hex}_{filename}"
    doc_file.save(saved_path)

    extracted_text = extract_document_text(saved_path, filename)
    if not extracted_text:
        suffix = Path(filename).suffix.lower()
        if suffix == ".doc":
            hint = "Legacy .doc files are not supported -- please upload .docx, .pdf, or .txt."
        elif suffix == ".pdf" and not HAVE_PDFPLUMBER:
            hint = "PDF reading isn't available on this server (pdfplumber not installed)."
        elif suffix == ".docx" and not HAVE_DOCX:
            hint = ".docx reading isn't available on this server (python-docx not installed)."
        else:
            hint = "No readable text was found in this document."
        return jsonify({"error": hint}), 422

    profile = request.form.get("profile")
    profile_data = {}
    if profile:
        try:
            profile_data = json.loads(profile)
        except Exception:
            profile_data = {}
    language = request.form.get("language", "English")
    mode = request.form.get("mode", "summarize")  # "summarize" or "read"

    # Cap extremely long documents to keep the prompt reasonable
    max_chars = 4000
    truncated = len(extracted_text) > max_chars
    doc_text_for_prompt = extracted_text[:max_chars]

    if mode == "read":
        # "Read full content back" doesn't need an LLM call at all -- routing
        # it through the model just makes it slowly retype the document one
        # token at a time (capped at 8192 output tokens, which is why this
        # used to take forever). The extracted text IS the reading, so hand
        # it back directly and only translate it if the student's learning
        # language isn't English.
        response_text = extracted_text
        if normalize_language(language).lower() != "english":
            response_text = google_translate(response_text, language, source_language="English")
    else:
        reader_prompt = (
            "The student uploaded a document for Reader Mode. Summarize its content clearly, "
            "highlight key points, and explain anything that may need clarification for their "
            "grade/subject level. Stay factual and based only on the document text provided.\n\n"
            f"Document text:\n{doc_text_for_prompt}"
        )
        # Summaries should be short -- a small token budget makes this return
        # in a couple seconds instead of budgeting for an 8192-token reply.
        response_text = tutorbot_reply(reader_prompt, language=language, profile=profile_data, max_tokens=900)
    return jsonify(
        {
            "type": "assistant",
            "response": response_text,
            "extracted_text": extracted_text,
            "truncated": truncated,
            "filename": filename,
        }
    )


@app.get("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")


@app.get("/health")
def health():
    return jsonify({"ok": True, "service": "TutorBot mobile and ESP32 bridge"})


@app.get("/student-stats")
def student_stats():
    """Compact stats summary for the ESP32's TFT (not the full /stats command
    text, which is meant for the chat window). Streak is server-tracked here
    since the ESP32 has no browser localStorage to read a client profile from."""
    profile_state = gamification.get_profile(streak_count=0)
    return jsonify(
        {
            "level": profile_state["level"],
            "title": profile_state["title"],
            "xp": profile_state["xp"],
            "streak": profile_state["streak"],
        }
    )


@app.get("/commands")
def commands():
    return jsonify(
        {
            "commands": [
                {"name": cmd.name, "usage": cmd.usage, "description": cmd.description}
                for cmd in COMMANDS
            ]
        }
    )


@app.post("/ai-chat")
def ai_chat():
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt") or data.get("message") or data.get("text")
    language = data.get("language")
    interface_language = normalize_language(data.get("interfaceLanguage") or data.get("appLanguage") or "English")

    if not isinstance(prompt, str) or not prompt.strip():
        return jsonify({"error": "JSON field 'prompt' is required"}), 400

    prompt = prompt.strip()
    language = normalize_language(str(language).strip() if isinstance(language, str) else "English")
    force_english = language.lower() != "english" and language.lower() == interface_language.lower()

    try:
        if prompt.startswith("/"):
            result = command_response(prompt, language=language or "English", profile=data.get("profile"))
            if (
                isinstance(result, dict)
                and isinstance(result.get("response"), str)
                and language.lower() != "english"
                and not force_english
            ):
                result["response"] = google_translate(result["response"], language, source_language="English")
            return jsonify(result)

        return jsonify(
            {
                "type": "assistant",
                "response": tutorbot_reply(
                    prompt,
                    language=language,
                    profile=data.get("profile"),
                    force_english=force_english,
                ),
            }
        )
    except Exception as exc:
        return jsonify({"error": f"TutorBot model failed: {exc}"}), 500


@app.route("/clear", methods=["GET", "POST"])
def clear_chat():
    global last_quiz_content, last_quiz_doc_content
    chat_history.clear()
    last_quiz_content = None
    last_quiz_doc_content = None
    return jsonify({"ok": True, "message": "Conversation cleared."})


@app.post("/dictionary")
def dictionary_lookup():
    data = request.get_json(silent=True) or {}
    word = str(data.get("word") or "").strip()
    if not word:
        return jsonify({"error": "Word is required"}), 400

    prompt = (
        f"Give a short, student-friendly definition of the word '{word}'. "
        "Respond in 2 short paragraphs maximum: first give the meaning, then one simple example sentence."
    )
    try:
        meaning = tutorbot_reply(prompt, language="English", profile=data.get("profile"))
        return jsonify({"ok": True, "word": word, "meaning": meaning})
    except Exception as exc:
        return jsonify({"error": f"Dictionary lookup failed: {exc}"}), 500


EASY_SPELL_WORDS = {
    "Grade 6": [
        {"word": "planet", "hint": "A celestial body in space orbiting a star", "example": "Earth is our home planet."},
        {"word": "garden", "hint": "A plot of ground where plants and flowers grow", "example": "We planted roses in the garden."},
        {"word": "friend", "hint": "A person you know well and like", "example": "She is my best friend at school."},
        {"word": "bridge", "hint": "A structure carrying a road across water", "example": "We walked across the golden bridge."},
        {"word": "summer", "hint": "The warmest season of the year", "example": "I love swimming during the summer."},
        {"word": "island", "hint": "A piece of land surrounded by water", "example": "They took a ferry to the island."},
        {"word": "camera", "hint": "A device for taking photographs", "example": "He snapped a photo with his camera."},
        {"word": "market", "hint": "A place where goods and food are sold", "example": "We bought fresh apples at the market."},
        {"word": "forest", "hint": "A large area covered with trees", "example": "The deer ran into the green forest."},
        {"word": "window", "hint": "An opening in a wall to let in light", "example": "Open the window for fresh air."},
        {"word": "travel", "hint": "To go from one place to another", "example": "They love to travel around the world."},
        {"word": "silver", "hint": "A shiny precious gray metal", "example": "She wore a shiny silver necklace."},
        {"word": "animal", "hint": "A living creature that is not a plant", "example": "The elephant is a large wild animal."},
    ],
    "Grade 7": [
        {"word": "balance", "hint": "An even distribution of weight or stability", "example": "He kept his balance on the beam."},
        {"word": "climate", "hint": "The weather conditions prevailing in an area", "example": "The tropical climate is warm and sunny."},
        {"word": "courage", "hint": "The ability to do something that frightens one", "example": "It took courage to speak in front of everyone."},
        {"word": "history", "hint": "The study of past events", "example": "We learned about ancient history today."},
        {"word": "journey", "hint": "An act of traveling from one place to another", "example": "Their journey lasted three days."},
        {"word": "library", "hint": "A building containing books for reading", "example": "I borrowed three books from the library."},
        {"word": "pattern", "hint": "A repeated decorative design or sequence", "example": "The fabric had a checkered pattern."},
        {"word": "science", "hint": "The study of the natural world through observation", "example": "Biology is a fascinating branch of science."},
        {"word": "station", "hint": "A place where trains or buses stop", "example": "We waited for the train at the station."},
        {"word": "weather", "hint": "The state of the atmosphere at a time and place", "example": "The weather forecast predicts sunshine."},
    ],
    "Grade 8": [
        {"word": "capture", "hint": "To take into one's possession by force or skill", "example": "The photographer managed to capture the sunset."},
        {"word": "culture", "hint": "The arts and customs of a particular nation or people", "example": "Music is a vital part of every culture."},
        {"word": "explore", "hint": "To travel through an unfamiliar area to learn about it", "example": "The team set out to explore the cave."},
        {"word": "horizon", "hint": "The line at which the earth's surface and the sky meet", "example": "The sun dipped below the ocean horizon."},
        {"word": "machine", "hint": "An apparatus using mechanical power to perform work", "example": "The washing machine cleaned our clothes quickly."},
        {"word": "measure", "hint": "To ascertain the size, amount, or degree of something", "example": "Use a ruler to measure the length."},
        {"word": "natural", "hint": "Existing in or caused by nature; not artificial", "example": "Honey is a natural sweetener."},
        {"word": "observe", "hint": "To notice or perceive something carefully", "example": "Astronomers observe the stars through telescopes."},
        {"word": "project", "hint": "An individual or collaborative enterprise", "example": "Our science project won first prize."},
        {"word": "surface", "hint": "The outside part or uppermost layer of something", "example": "Leaves floated on the water's surface."},
    ],
    "Grade 9": [
        {"word": "advance", "hint": "To move forward in a purposeful way", "example": "Technological advance has changed our daily lives."},
        {"word": "concept", "hint": "An abstract idea or general notion", "example": "Gravity is a fundamental concept in physics."},
        {"word": "develop", "hint": "To grow or cause to grow and become more mature", "example": "Students develop strong problem-solving skills."},
        {"word": "element", "hint": "An essential part or aspect of something", "example": "Trust is a key element in friendship."},
        {"word": "feature", "hint": "A distinctive attribute or aspect of something", "example": "The phone's main feature is its high-res camera."},
        {"word": "general", "hint": "Affecting or concerning all or most people", "example": "There is a general agreement on the plan."},
        {"word": "improve", "hint": "To make or become better", "example": "Daily practice will improve your spelling."},
        {"word": "justice", "hint": "Just behavior or treatment; fairness", "example": "Courts uphold law and justice for all."},
        {"word": "network", "hint": "An interconnected group or system", "example": "Computers are linked through a global network."},
        {"word": "opinion", "hint": "A view or judgment formed about something", "example": "Everyone is entitled to their own opinion."},
        {"word": "process", "hint": "A series of actions or steps taken to achieve an end", "example": "Photosynthesis is a vital natural process."},
        {"word": "quality", "hint": "The standard of something as measured against other things", "example": "We prioritize quality over quantity."},
    ],
    "Grade 10": [
        {"word": "benefit", "hint": "An advantage or profit gained from something", "example": "Exercise provides great benefit to your health."},
        {"word": "connect", "hint": "To bring together or into contact", "example": "The bridge will connect the two islands."},
        {"word": "discuss", "hint": "To talk about something with another person", "example": "Let us discuss our project ideas together."},
        {"word": "example", "hint": "A thing characteristic of its kind, illustrating a rule", "example": "Can you give an example of a mammal?"},
        {"word": "graphic", "hint": "Relating to visual art, especially illustration", "example": "The textbook features clear graphic diagrams."},
        {"word": "medical", "hint": "Relating to the science or practice of medicine", "example": "She wants to pursue a medical career."},
        {"word": "popular", "hint": "Liked, admired, or enjoyed by many people", "example": "Football is a popular sport worldwide."},
        {"word": "routine", "hint": "A sequence of actions regularly followed", "example": "Morning exercise is part of my daily routine."},
        {"word": "similar", "hint": "Resembling without being identical", "example": "The two paintings look very similar."},
        {"word": "support", "hint": "To give assistance, comfort, or approval to", "example": "Friends always support each other."},
    ],
    "Grade 11": [
        {"word": "analysis", "hint": "Detailed examination of the elements or structure of something", "example": "Data analysis revealed interesting trends."},
        {"word": "category", "hint": "A class or division of people or things with shared characteristics", "example": "Whales fall into the mammal category."},
        {"word": "creative", "hint": "Relating to or involving the imagination or original ideas", "example": "She has a creative approach to art."},
        {"word": "describe", "hint": "To give an account in words of someone or something", "example": "Please describe what happened in the story."},
        {"word": "economic", "hint": "Relating to the economy or production of wealth", "example": "Trade boosts national economic growth."},
        {"word": "function", "hint": "An activity or purpose natural to a person or thing", "example": "The function of the heart is to pump blood."},
        {"word": "material", "hint": "The matter from which a thing is or can be made", "example": "Wood is a common construction material."},
        {"word": "positive", "hint": "Expressing or showing optimism and constructive confidence", "example": "A positive attitude helps in overcoming challenges."},
        {"word": "specific", "hint": "Clearly defined or identified", "example": "Is there a specific topic you want to study?"},
        {"word": "standard", "hint": "A level of quality or attainment used as a measure", "example": "The school maintains high academic standards."},
    ],
    "Grade 12": [
        {"word": "academic", "hint": "Relating to education and scholarship", "example": "He received an award for academic excellence."},
        {"word": "critical", "hint": "Expressing analysis or forming important evaluations", "example": "Critical thinking is essential in science."},
        {"word": "evaluate", "hint": "To form an idea of the amount, number, or value of something", "example": "Judges will evaluate each performance."},
        {"word": "generate", "hint": "To cause something to arise or come into being", "example": "Solar panels generate clean electrical energy."},
        {"word": "instance", "hint": "An example or single occurrence of something", "example": "For instance, birds can fly long distances."},
        {"word": "maintain", "hint": "To cause or enable a condition or state of affairs to continue", "example": "It is important to maintain good study habits."},
        {"word": "overview", "hint": "A general review or summary of a subject", "example": "The teacher gave an overview of the chapter."},
        {"word": "priority", "hint": "The fact or condition of being regarded as more important", "example": "Safety is our number one priority."},
        {"word": "resource", "hint": "A supply of materials, money, or staff", "example": "The internet is a vast educational resource."},
        {"word": "strategy", "hint": "A plan of action designed to achieve a major aim", "example": "We need an effective study strategy for exams."},
    ],
    "College": [
        {"word": "adaptive", "hint": "Able to adjust to new conditions or environments", "example": "Smart software has adaptive learning algorithms."},
        {"word": "coherent", "hint": "Logical and consistent; easy to understand", "example": "Her essay presented a clear and coherent argument."},
        {"word": "dialogue", "hint": "Conversation between two or more people", "example": "Constructive dialogue resolves misunderstandings."},
        {"word": "emphasis", "hint": "Special importance, value, or prominence given to something", "example": "The course places strong emphasis on practical skills."},
        {"word": "flexible", "hint": "Capable of bending easily without breaking; adaptable", "example": "We have flexible schedules for group study."},
        {"word": "guidance", "hint": "Advice or information aimed at resolving a problem", "example": "Teachers provide valuable academic guidance."},
        {"word": "moderate", "hint": "Average in amount, intensity, quality, or degree", "example": "Exercise at a moderate pace for best results."},
        {"word": "parallel", "hint": "Side by side and having the same distance continuously between them", "example": "Train tracks run parallel to the highway."},
        {"word": "reliable", "hint": "Consistently good in quality or performance; trustworthy", "example": "He is a reliable partner for group projects."},
        {"word": "validate", "hint": "To check or prove the validity or accuracy of something", "example": "Scientists run experiments to validate the theory."},
    ],
    "Adult": [
        {"word": "advocate", "hint": "A person who publicly supports or recommends a particular cause", "example": "She is a strong advocate for public libraries."},
        {"word": "capacity", "hint": "The maximum amount that something can contain or produce", "example": "The stadium has a seating capacity of fifty thousand."},
        {"word": "database", "hint": "A structured set of data held in a computer", "example": "The library database organizes all catalog records."},
        {"word": "feedback", "hint": "Information about reactions to a product or a person's performance", "example": "Constructive feedback helps students improve."},
        {"word": "gradient", "hint": "An inclined part of a road, or a smooth transition of color", "example": "The app interface uses a stylish purple gradient."},
        {"word": "heritage", "hint": "Property or traditions that are or may be inherited", "example": "We take pride in our rich cultural heritage."},
        {"word": "momentum", "hint": "The quantity of motion of a moving body, or driving power", "example": "Our study group gained great momentum this semester."},
        {"word": "optimize", "hint": "To make the best or most effective use of a situation or resource", "example": "Developers optimize code for faster loading speeds."},
        {"word": "platform", "hint": "A raised level surface, or a standard computing environment", "example": "TutorBot is an interactive learning platform."},
        {"word": "workflow", "hint": "The sequence of processes through which a piece of work passes", "example": "A clear workflow makes group projects easier."},
    ],
}


def generate_ai_spell_word(grade: str = "Grade 9", difficulty: str = "easy") -> dict:
    grade = grade or "Grade 9"
    difficulty = difficulty or "easy"
    grade_words = EASY_SPELL_WORDS.get(grade) or EASY_SPELL_WORDS["Grade 9"]
    fallback_item = random.choice(grade_words)

    prompt = (
        f"Generate one student-friendly English spelling practice word suitable for {grade} level. "
        f"Difficulty: {difficulty}. The word must be an everyday, practical, easy-to-spell vocabulary word "
        "between 4 and 8 letters long (e.g. 'planet', 'bridge', 'friend', 'market', 'balance', 'journey'). "
        "Avoid obscure, archaic, or excessively difficult words. "
        "Output ONLY a single valid JSON object in this exact format with no extra text:\n"
        '{"word": "example", "hint": "A short, simple clue or meaning of the word", "example": "A simple sentence using the word."}'
    )

    try:
        raw_reply = tutorbot_reply(prompt, language="English", max_tokens=150)
        json_match = re.search(r"\{[\s\S]*\}", raw_reply)
        if json_match:
            data = json.loads(json_match.group(0))
            word = str(data.get("word") or "").strip().lower()
            hint = str(data.get("hint") or "").strip()
            example = str(data.get("example") or "").strip()
            word = re.sub(r"[^a-zA-Z]", "", word)
            if 3 <= len(word) <= 12 and word.isalpha():
                return {
                    "ok": True,
                    "word": word,
                    "hint": hint or fallback_item["hint"],
                    "example": example or fallback_item["example"],
                    "grade": grade,
                    "difficulty": difficulty,
                    "source": "ai",
                }
    except Exception as exc:
        print(f"[SpellGen] AI spell generation fallback: {exc}")

    return {
        "ok": True,
        "word": fallback_item["word"],
        "hint": fallback_item["hint"],
        "example": fallback_item["example"],
        "grade": grade,
        "difficulty": difficulty,
        "source": "curated",
    }


@app.route("/generate-spell-word", methods=["GET", "POST"])
@app.route("/api/spell-word", methods=["GET", "POST"])
def api_generate_spell_word():
    data = _read_request_data() if request.method == "POST" else request.args.to_dict()
    grade = str(data.get("grade") or "Grade 9").strip()
    difficulty = str(data.get("difficulty") or "easy").strip()
    result = generate_ai_spell_word(grade=grade, difficulty=difficulty)
    return jsonify(result)


@app.get("/esp32/settings")
def get_esp32_settings():
    return jsonify(
        {
            "ssid": esp32_settings["ssid"],
            "password_set": bool(esp32_settings["password"]),
            "flash_note": "Browser apps cannot rewrite ESP32 firmware. Use these values when flashing tutorbot-main.ino.",
        }
    )


@app.post("/esp32/settings")
def set_esp32_settings():
    data = request.get_json(silent=True) or {}
    ssid = str(data.get("ssid", "")).strip()
    password = str(data.get("password", ""))

    if not ssid:
        return jsonify({"error": "SSID is required"}), 400

    esp32_settings["ssid"] = ssid
    esp32_settings["password"] = password
    return jsonify({"ok": True, "ssid": ssid, "password_set": bool(password)})


@app.post("/files")
def upload_file():
    uploaded_file = request.files.get("file")
    if uploaded_file is None or uploaded_file.filename == "":
        return jsonify({"error": "multipart field 'file' is required"}), 400

    original_name = secure_filename(uploaded_file.filename) or "upload.bin"
    file_id = uuid4().hex
    saved_name = f"{file_id}_{original_name}"
    saved_path = UPLOAD_DIR / saved_name
    uploaded_file.save(saved_path)

    return jsonify(
        {
            "ok": True,
            "file_id": file_id,
            "filename": original_name,
            "stored_as": saved_name,
            "size": saved_path.stat().st_size,
            "download_url": f"/files/{saved_name}",
        }
    )


@app.get("/files")
def list_files():
    files = []
    for path in sorted(UPLOAD_DIR.iterdir(), key=lambda item: item.stat().st_mtime, reverse=True):
        if path.is_file():
            files.append(
                {
                    "name": path.name,
                    "size": path.stat().st_size,
                    "download_url": f"/files/{path.name}",
                }
            )
    return jsonify({"files": files})


@app.get("/files/<path:filename>")
def download_file(filename):
    return send_from_directory(UPLOAD_DIR, filename, as_attachment=True)


@app.get("/downloads/<path:filename>")
def download_generated_file(filename):
    return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)


@app.route("/api/send-otp", methods=["POST"])
@app.route("/api/send-otp", methods=["GET"])
def api_send_otp():
    if request.method == "GET":
        return jsonify({"error": "Use POST to send OTP."}), 405

    data = _read_request_data()
    username = str(data.get("username") or data.get("identifier") or data.get("email") or "").strip()
    email = str(data.get("email") or data.get("user_email") or "").strip()
    password = str(data.get("password", ""))
    confirm_password = str(data.get("confirmPassword") or data.get("confirm_password") or "")
    mode = _normalize_auth_mode(data.get("mode", "login"))

    if mode == "register":
        if not username or not email or not password:
            return jsonify({"error": "Please enter a username, email, and password"}), 400
        if password != confirm_password:
            return jsonify({"error": "Passwords do not match"}), 400
        try:
            user, verification, sent = user_management.register(username, email, password)
        except (KeyError, ValueError) as exc:
            return jsonify({"error": str(exc)}), 400
    else:
        if not username or not password:
            return jsonify({"error": "Please enter your username or email and password"}), 400
        try:
            user, verification, sent = user_management.login(username, password)
        except (KeyError, ValueError) as exc:
            return jsonify({"error": str(exc)}), 400

    return jsonify({
        "ok": True,
        "mode": mode,
        "message": "OTP code sent to your email" if sent else "OTP code prepared for verification",
        "user": user,
    })


@app.route("/api/verify-otp", methods=["POST"])
@app.route("/api/verify-otp", methods=["GET"])
def api_verify_otp():
    if request.method == "GET":
        return jsonify({"error": "Use POST to verify OTP."}), 405

    data = _read_request_data()
    username = str(data.get("username") or data.get("identifier") or data.get("email") or "").strip()
    code = str(data.get("code") or data.get("otp") or "").strip()
    mode = _normalize_auth_mode(data.get("mode", "login"))

    if not username or not code:
        return jsonify({"error": "Username and code are required"}), 400

    try:
        user = user_management.verify(username, code, purpose=mode)
    except (KeyError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({"ok": True, "user": user})


@app.get("/api/survey-questions")
def api_survey_questions():
    return jsonify({"questions": user_management.get_survey_questions()})


@app.post("/api/survey-questions")
def api_set_survey_questions():
    data = request.get_json(silent=True) or {}
    try:
        questions = user_management.set_survey_questions(data.get("questions", []))
        return jsonify({"ok": True, "questions": questions})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.post("/api/user-profile")
def api_user_profile():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip().lower()
    profile = data.get("profile") or {}
    if not username:
        return jsonify({"error": "Username is required"}), 400
    try:
        user = user_management.update_user_profile(username, **profile)
        return jsonify({"ok": True, "user": user})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.errorhandler(404)
def handle_not_found(error):
    path = request.path if request else "unknown"
    if path.startswith("/api/"):
        return jsonify({"error": f"Endpoint not found: {path}", "path": path}), 404
    return send_from_directory(WEB_DIR, "index.html")


# ---- mDNS: advertise this PC as tutorbot-server.local ---------------------
# The ESP32 hosts the primary mobile interface at http://tutorbot.local:80.
# This PC server advertises itself as tutorbot-server.local:5000 so the
# ESP32 and mobile clients can reliably find it dynamically across networks
# without IP configuration or mDNS collisions.
#
# Requires: pip install zeroconf
SERVER_PORT = 5000
MDNS_HOSTNAME = "tutorbot-server.local."


def get_local_ip():
    """Best-effort LAN IP of this machine (works on Windows/macOS/Linux)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))  # doesn't actually send anything
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def start_mdns():
    from zeroconf import Zeroconf, ServiceInfo

    ip = get_local_ip()
    zc = Zeroconf()

    info_server = ServiceInfo(
        "_http._tcp.local.",
        "TutorBot-Server._http._tcp.local.",
        addresses=[socket.inet_aton(ip)],
        port=SERVER_PORT,
        server="tutorbot-server.local.",
    )
    zc.register_service(info_server)
    print(f"mDNS: advertising tutorbot-server.local -> {ip}:{SERVER_PORT}")

    try:
        info_pc = ServiceInfo(
            "_http._tcp.local.",
            "TutorBot-PC._http._tcp.local.",
            addresses=[socket.inet_aton(ip)],
            port=SERVER_PORT,
            server="tutorbot-pc.local.",
        )
        zc.register_service(info_pc)
        print(f"mDNS: advertising tutorbot-pc.local -> {ip}:{SERVER_PORT}")
    except Exception as exc:
        print(f"mDNS: secondary registration note: {exc}")

    return zc  # keep a reference alive for the life of the process


if __name__ == "__main__":
    try:
        _zeroconf_handle = start_mdns()
    except ImportError:
        print("mDNS: 'zeroconf' package not installed -- run: pip install zeroconf")
        print("mDNS: tutorbot-server.local will NOT resolve until this is installed.")
    print("TutorBot server running at http://0.0.0.0:5000/")
    run_simple("0.0.0.0", 5000, app, threaded=True, use_reloader=False)
    