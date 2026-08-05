# TutorBot

TutorBot is a local AI tutor with a terminal UI, a mobile-friendly web interface, an ESP32 relay sketch, and an Android WebView wrapper. It runs a small GGUF language model on your PC, answers tutoring questions, generates quizzes, exports Word documents, and can be accessed from a phone on the same network.

## Features

- **Conversational tutoring:** A Socratic tutor that explains concepts, asks follow-up questions, and helps students reason through problems.
- **Quiz generation:** The `/quiz` command creates focused quizzes using optional web reference material.
- **Word document export:** The `/doc` command exports the latest quiz as a `.docx` file, with optional answer keys.
- **Reference search:** The `/search` command fetches reference material for a topic.
- **Terminal UI:** Run TutorBot locally in the Textual-based command-line interface.
- **Mobile web UI:** Run `Server.py` and open TutorBot from a phone browser.
- **ESP32 relay:** Forward phone chat requests through an ESP32 to the PC running TutorBot.
- **Android wrapper:** Build a WebView APK/App Bundle that loads the TutorBot web interface.
- **Local model:** Powered by `llama-cpp-python`; no external AI API key is required.

## Prerequisites

- Python 3.9 or higher
- Pip
- A local GGUF model in `models/`
- Tesseract OCR installed on your PC for OCR image processing
- For Android builds: Android Studio
- For ESP32 builds: Arduino IDE or PlatformIO with ESP32 board support

## Installation

```bash
pip install -r requirements.txt
```

### Downloading the models

TutorBot needs at least one local GGUF model in `models/` before it can run.

- Main chat model: `models/qwen2.5-0.5b-instruct-q4_k_m.gguf`
- Lightweight image model: `models/llama-2-1.1b.gguf`

The repository includes the packages needed for local execution and model downloads.

If you do not already have the Hugging Face CLI installed, install it first:

```bash
pip install huggingface-hub
```

Then log in and download the models:

```bash
huggingface-cli login
hf download Qwen/Qwen2.5-0.5B-Instruct-GGUF qwen2.5-0.5b-instruct-q4_k_m.gguf --local-dir models
```

For the lightweight image model, use a valid public GGUF repository with a model under 2B parameters. One known public example is `unsloth/Inkling-Small-GGUF`.

Download it and save it to `models/llama-2-1.1b.gguf` so it matches the configured path in `config.py`.

```bash
hf download unsloth/Inkling-Small-GGUF llama-2-1.1b.gguf --local-dir models
```

If you want to choose a different model, search Hugging Face for a public GGUF model and use the same download pattern:

```text
https://huggingface.co/models?search=gguf+1.1b
```

Then download your chosen repo and save the file as `models/llama-2-1.1b.gguf`, or update `IMAGE_MODEL_PATH` in `config.py` if you keep a different filename.

If `hf` is not available, you can also use the Python module:

```bash
python -m huggingface_hub download Qwen/Qwen2.5-0.5B-Instruct-GGUF --filename qwen2.5-0.5b-instruct-q4_k_m.gguf --cache-dir models
python -m huggingface_hub download meta-llama/Llama-2-1.1B-GGUF --filename llama-2-1.1b.gguf --cache-dir models
```

If you prefer, download the model files directly from Hugging Face and place them inside the `models/` folder.

### Email verification setup

If you want account registration and login verification to work properly, configure `EMAIL_FROM` to match the SMTP account used by `SMTP_USER` when using Gmail or other providers that require a verified sender address.

Update `config.py` with your email server settings:

```python
EMAIL_FROM = "your-email@example.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "your-email@example.com"
SMTP_PASSWORD = "your-app-password"
SMTP_USE_TLS = True
```

If email delivery fails, login and registration verification codes may not be sent, but the account will still be created locally.

## Terminal App

Run:

```bash
python main.py
```

Useful commands:

| Command | Description |
|---|---|
| `/quiz <topic>` | Generate a quiz |
| `/doc [answers\|split]` | Export the latest quiz as Word documents |
| `/search <query>` | Search for reference material |
| `/model` | Show model information |
| `/clear` | Clear the conversation |
| `/help` | Show all commands |
| `/exit` | Exit TutorBot |

## PC Server, Web App, and API

Run:

```powershell
python .\Server.py
```

Expected startup message:

```text
TutorBot server running at http://0.0.0.0:5000/
```

Open the web interface on the PC:

```text
http://localhost:5000/
```

Open it from a phone on the same Wi-Fi:

```text
http://YOUR_PC_IP:5000/
```

Find your PC IP on Windows:

```powershell
ipconfig
```

Use the IPv4 address for your active Wi-Fi adapter.

### Server Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | `GET` | Mobile-friendly TutorBot web interface |
| `/health` | `GET` | Server health check |
| `/commands` | `GET` | Slash-command metadata for the web UI |
| `/ai-chat` | `POST` | Send TutorBot prompts or slash commands |
| `/clear` | `POST` | Clear server chat history |
| `/esp32/settings` | `GET/POST` | Store ESP32 Wi-Fi setup values on the PC server |
| `/files` | `POST` | Upload a file using multipart field `file` |
| `/files` | `GET` | List uploaded files |
| `/files/<filename>` | `GET` | Download uploaded files |
| `/downloads/<filename>` | `GET` | Download generated quiz documents |

Example chat request:

```json
{"prompt": "Teach me Newton's second law"}
```

Example command request:

```json
{"prompt": "/quiz photosynthesis grade=8 count=5 web=y"}
```

The web/mobile UI supports:

| Command | Description |
|---|---|
| `/help` | Show available commands |
| `/clear` | Clear mobile chat history |
| `/model` | Show local model info |
| `/search <query>` | Search for reference material |
| `/quiz <topic> grade=8 count=5 web=y` | Generate a quiz |
| `/doc` | Export the latest quiz |
| `/doc answers` | Export quiz with answer key |
| `/doc split` | Export quiz and answer key as separate files |

## ESP32 Phone Bridge

The ESP32 sketch is in `tutorbot-main.ino`. It relays chat requests from the phone to the PC server and returns TutorBot's response.

Before flashing, edit:

```cpp
const char* ssid = "YOUR_WIFI_NAME";
const char* password = "YOUR_WIFI_PASSWORD";
const char* pcBaseUrl = "http://YOUR_PC_IP:5000";
```

After flashing, open the Serial Monitor. It prints the ESP32 URL:

```text
ESP32 relay: http://ESP32_IP
```

Send phone chat requests through:

```text
http://ESP32_IP/ask
```

Example JSON:

```json
{"prompt": "Explain fractions with an example"}
```

For file transfer, use the PC server directly for best speed. The ESP32 exposes:

```text
http://ESP32_IP/files
```

That returns the PC file upload/list URLs. The ESP32 intentionally does not buffer large files in RAM.

## ESP32 Wi-Fi Settings in the App

The web/mobile interface includes a settings icon where you can enter an ESP32 SSID and password. These values are stored on the TutorBot PC server for setup reference.

Important: a browser or Android WebView app cannot rewrite already-flashed ESP32 firmware by itself. To actually change the ESP32 Wi-Fi network, update and flash `tutorbot-main.ino` with the same values, or add ESP32 captive-portal provisioning later.

## Android App

An Android WebView wrapper is included in `android/`.

To build:

1. Open the `android/` folder in Android Studio.
2. Edit `android/app/src/main/java/com/tutorbot/mobile/MainActivity.java`.
3. Set `TUTORBOT_URL` to your TutorBot server URL.
4. Build an APK for testing or a signed Android App Bundle for Play Store upload.

For local testing:

```java
private static final String TUTORBOT_URL = "http://192.168.1.100:5000/";
```

For a Play Store release, host TutorBot on a stable HTTPS domain. A local `192.168.x.x` address only works on your own Wi-Fi network.

## Troubleshooting

### `OSError: Windows error: 6` when running `python Server.py`

This can happen when Flask/Click tries to print its startup banner through a broken Windows console handle. `Server.py` now uses Werkzeug's `run_simple()` with the reloader disabled to avoid that banner path.

If it still happens, open a fresh PowerShell or Windows Terminal tab and run:

```powershell
python .\Server.py
```

### Phone cannot open `http://YOUR_PC_IP:5000/`

- Make sure the PC and phone are on the same Wi-Fi network.
- Use the PC's active Wi-Fi IPv4 address from `ipconfig`.
- Allow Python through Windows Firewall if prompted.
- Test on the PC first with `http://localhost:5000/`.

### Android app opens but cannot reach TutorBot

- Check `TUTORBOT_URL` in `MainActivity.java`.
- Use the PC LAN URL for local testing.
- Use a public HTTPS URL for Play Store releases.

### Model is slow

- The ESP32 is only a relay; model speed depends on the PC.
- Keep file upload/download directly on the PC server.
- Use a smaller GGUF model or enable GPU support in `llama-cpp-python` if available.

## Project Structure

- `main.py`: Terminal TutorBot entry point.
- `Server.py`: PC server for the web UI, Android app, ESP32 relay, chat API, files, and generated documents.
- `tutorbot-main.ino`: ESP32 relay sketch.
- `web/`: Mobile-friendly browser UI served by `Server.py`.
- `android/`: Android WebView wrapper project.
- `config.py`: Model path and system prompts.
- `model.py`: Local GGUF model loading and response generation.
- `context_fetcher.py`: Web search and page text extraction.
- `quiz_generator.py`: Quiz prompt construction and output normalization.
- `doc_generator.py`: Word document export helpers.
- `ui/`: Textual terminal UI components.
- `models/`: Local model files.
- `uploads/`: Uploaded files, ignored by Git.
- `downloads/`: Generated `.docx` files, ignored by Git.
- `requirements.txt`: Python dependencies.

## License

This project is licensed under the GNU General Public License v3.0. See `LICENSE` for details.
