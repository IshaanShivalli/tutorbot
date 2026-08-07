# TutorBot

TutorBot is a local AI tutor that runs on your PC and supports a terminal interface, a mobile-friendly web UI, an ESP32 phone bridge, and an Android WebView wrapper.

It uses local GGUF models and on-device OCR to answer questions, generate quizzes, export Word documents, practice spelling with a dedicated Spell Practice mode, and look up word meanings through a built-in Dictionary tool.

## Key Features

- **AI tutoring:** Ask questions, get explanations, and follow-up guidance.
- **Dictionary lookup:** Use the Dictionary button in the top bar to look up a word and get a short definition plus a simple example.
- **Spelling practice:** Use the Spell Practice button in the mobile UI for pronunciation and spelling drills.
- **Quiz generation:** Create quizzes with `/quiz` and optional web reference content.
- **Document export:** Save quizzes as `.docx` files with answer keys.
- **Image OCR:** Upload or capture images to extract text using Tesseract.
- **Local model execution:** Runs with `llama-cpp-python` and local GGUF models.
- **Mobile web interface:** Access TutorBot from a phone browser on the same network.
- **ESP32 relay bridge:** Relay phone requests through an ESP32 to the PC.
- **Android wrapper:** Load the mobile UI inside a WebView app.

## Prerequisites

- Python 3.9 or higher
- Pip
- Local GGUF model files in `models/`
- Tesseract OCR installed for image text extraction
- Android Studio for building the Android wrapper
- Arduino IDE or PlatformIO for ESP32 support

## Installation

Install Python dependencies:

```bash
pip install -r requirements.txt
```

## Models

Place the required model files in `models/` before running the app.

- `models/qwen2.5-0.5b-instruct-q4_k_m.gguf`
- `models/llama-2-1.1b.gguf`

If you need to download models, use the Hugging Face CLI or Python module.

Example with Hugging Face CLI:

```bash
pip install huggingface-hub
huggingface-cli login
hf download Qwen/Qwen2.5-0.5B-Instruct-GGUF qwen2.5-0.5b-instruct-q4_k_m.gguf --local-dir models
```

Example with Python:

```bash
python -m huggingface_hub download Qwen/Qwen2.5-0.5B-Instruct-GGUF --filename qwen2.5-0.5b-instruct-q4_k_m.gguf --cache-dir models
python -m huggingface_hub download meta-llama/Llama-2-1.1B-GGUF --filename llama-2-1.1b.gguf --cache-dir models
```

Update `IMAGE_MODEL_PATH` in `config.py` if you save a different image model filename.

## Running TutorBot

### Terminal UI

```bash
python main.py
```

### Web/mobile UI

```bash
python Server.py
```

Open on your PC:

```text
http://localhost:5000/
```

Open on your phone on the same network:

```text
http://YOUR_PC_IP:5000/
```

### Android wrapper

Open the `android/` folder in Android Studio and set your TutorBot server URL in `MainActivity.java`.

## Commands

### Terminal commands

| Command | Description |
|---|---|
| `/quiz <topic>` | Generate a quiz |
| `/doc [answers\|split]` | Export the latest quiz |
| `/search <query>` | Search for reference material |
| `/model` | Show model information |
| `/clear` | Clear the conversation |
| `/help` | Show available commands |
| `/exit` | Exit TutorBot |

### Mobile/web commands

The mobile UI uses persistent buttons and a chat prompt for commands. The Spell Practice button opens spelling/pronunciation practice, and the Dictionary button opens a word lookup tool for quick meaning checks.

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

### Dictionary feature

Use the Dictionary button in the web/mobile top bar to look up a word. The app sends the word to TutorBot and returns a short meaning and one example sentence.

## Server API

### Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | `GET` | Load the mobile-friendly TutorBot UI |
| `/health` | `GET` | Health check |
| `/commands` | `GET` | Get available slash commands |
| `/ai-chat` | `POST` | Send prompts or commands |
| `/clear` | `POST` | Clear server chat history |
| `/dictionary` | `POST` | Look up a word and return a short meaning |
| `/esp32/settings` | `GET/POST` | Save ESP32 network settings |
| `/files` | `POST` | Upload a file |
| `/files` | `GET` | List uploaded files |
| `/files/<filename>` | `GET` | Download an uploaded file |
| `/downloads/<filename>` | `GET` | Download generated quiz documents |

### Example request

```json
{"prompt": "Explain Newton's second law"}
```

## ESP32 Phone Bridge

The ESP32 sketch lives in `tutorbot-main.ino` and relays chat requests from your phone to the PC server.

Before flashing, update the Wi-Fi and PC server URL:

```cpp
const char* ssid = "YOUR_WIFI_NAME";
const char* password = "YOUR_WIFI_PASSWORD";
const char* pcBaseUrl = "http://YOUR_PC_IP:5000";
```

After flashing, use the Serial Monitor to find the ESP32 URL, then send requests through:

```text
http://ESP32_IP/ask
```

## Android WebView App

Build the Android wrapper in Android Studio from the `android/` folder. Update `TUTORBOT_URL` in `MainActivity.java` and build an APK or App Bundle.

## Notes

- The mobile Spell Practice button is the supported spelling/pronunciation flow. `/spell` entry is disabled in the mobile chat prompt.
- The Dictionary button is the supported word-meaning lookup flow in the mobile/web UI.
- Recent auth updates also improve the mobile login and registration flow by accepting the same payload shape the web form sends.
- Keep your local GGUF models in `models/` for offline model execution.
- Tesseract OCR must be installed on the PC for image processing.

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
