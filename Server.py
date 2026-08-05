<<<<<<< HEAD
import re
from pathlib import Path
from uuid import uuid4

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.serving import run_simple

from config import SYSTEM_PROMPT
from model import ask_ai
from context_fetcher import get_context_for_topic
from doc_generator import create_quiz_and_answer_key, create_quiz_document
from quiz_generator import generate_quiz, reformat_quiz_for_doc
from ui.commands import COMMANDS


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


def tutorbot_reply(prompt: str) -> str:
    chat_history.append({"role": "user", "content": prompt})
    reply = ask_ai(chat_history, SYSTEM_PROMPT, max_tokens=1024)
    chat_history.append({"role": "assistant", "content": reply})
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


def command_response(command_text: str):
    global last_quiz_content, last_quiz_doc_content, last_quiz_topic, last_quiz_grade

    command_name, _, argument = command_text.strip().partition(" ")
    command_name = command_name.lower()
    argument = argument.strip()

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

    if command_name == "/model":
        return {
            "type": "system",
            "response": "\n".join(f"{key}: {value}" for key, value in MODEL_INFO.items()),
        }

    if command_name == "/search":
        if not argument:
            return {"type": "error", "response": "Usage: /search <query>"}
        context, source = get_context_for_topic(argument)
        if not context:
            return {"type": "system", "response": f"No reference material found for '{argument}'."}
        preview = context[:1200] + ("..." if len(context) > 1200 else "")
        return {"type": "system", "response": f"Source: {source}\n\n{preview}"}

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
        )
        last_quiz_content = quiz
        last_quiz_doc_content = None
        last_quiz_topic = topic
        last_quiz_grade = grade
        return {
            "type": "assistant",
            "response": quiz
            + "\n\nQuiz ready. Use /doc, /doc answers, or /doc split to export Word documents.",
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

    if not isinstance(prompt, str) or not prompt.strip():
        return jsonify({"error": "JSON field 'prompt' is required"}), 400

    prompt = prompt.strip()

    try:
        if prompt.startswith("/"):
            return jsonify(command_response(prompt))
        return jsonify({"type": "assistant", "response": tutorbot_reply(prompt)})
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


if __name__ == "__main__":
    print("TutorBot server running at http://0.0.0.0:5000/")
    run_simple("0.0.0.0", 5000, app, threaded=True, use_reloader=False)
=======
from flask import Flask, request, jsonify

app = Flask(__name__)

# Load your AI model here (e.g., Llama 3 via Ollama, Hugging Face, or custom LMS logic)
def query_ai_model(prompt):
    # Placeholder for your AI model inference logic
    response_text = f"AI processed your LMS query: '{prompt}'"
    return response_text

@app.route('/ai-chat', methods=['POST'])
def ai_chat():
    data = request.get_json()
    if not data or 'prompt' not in data:
        return jsonify({"error": "Invalid payload, 'prompt' required"}), 400
    
    user_prompt = data['prompt']
    print(f"Received prompt from ESP32 bridge: {user_prompt}")
    
    # Get response from your AI model
    ai_answer = query_ai_model(user_prompt)
    
    return jsonify({"response": ai_answer})

if __name__ == '__main__':
    # Run on port 5000, accessible locally by the ESP32
    app.run(host='0.0.0.0', port=5000)
>>>>>>> 6696ff70c425dd6f93af6c93d97bcaa324f38300
