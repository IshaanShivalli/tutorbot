import json
import re
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from flask import Flask, jsonify, request, send_from_directory
from PIL import Image
from werkzeug.utils import secure_filename
from werkzeug.serving import run_simple
import pytesseract

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
last_quiz_content = None
last_quiz_doc_content = None
last_quiz_topic = "quiz"
last_quiz_grade = "Grade 9"
esp32_settings = {"ssid": "", "password": ""}

app = Flask(__name__, static_folder=str(WEB_DIR), static_url_path="")

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


def tutorbot_reply(prompt: str, language: str = "English", profile: dict = None, force_english: bool = False) -> str:
    language = normalize_language(language)
    english_prompt = prompt
    if language.lower() != "english":
        english_prompt = google_translate(prompt, "English", source_language=language)

    chat_history.append({"role": "user", "content": english_prompt})
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
    reply = ask_ai(chat_history, request_prompt, max_tokens=1024)
    chat_history.append({"role": "assistant", "content": reply})
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


@app.get("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")


@app.get("/health")
def health():
    return jsonify({"ok": True, "service": "TutorBot mobile and ESP32 bridge"})


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


@app.post("/clear")
def clear_chat():
    global last_quiz_content, last_quiz_doc_content
    chat_history.clear()
    last_quiz_content = None
    last_quiz_doc_content = None
    return jsonify({"ok": True})


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


@app.post("/api/send-otp")
def api_send_otp():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    if not email:
        return jsonify({"error": "Email is required"}), 400
    
    otp = f"{random.randint(100000, 999999)}"
    verification_codes[email] = otp
    
    if send_otp_email(email, otp):
        return jsonify({"ok": True, "message": "OTP code sent to your email"})
    else:
        return jsonify({"error": "Failed to send email. Verify SMTP configurations."}), 500


@app.post("/api/verify-otp")
def api_verify_otp():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    code = data.get("code", "").strip()
    
    if not email or not code:
        return jsonify({"error": "Email and code are required"}), 400
    
    saved_code = verification_codes.get(email)
    if saved_code and saved_code == code:
        verification_codes.pop(email, None)
        return jsonify({"ok": True})
    else:
        return jsonify({"error": "Invalid verification code"}), 400


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


if __name__ == "__main__":
    print("TutorBot server running at http://0.0.0.0:5000/")
    run_simple("0.0.0.0", 5000, app, threaded=True, use_reloader=False)
