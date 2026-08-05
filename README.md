# TutorBot

TutorBot is a terminal-based (TUI) AI tutor that runs a small local language model to explain concepts, answer questions Socratically, generate quizzes grounded in live web search, export those quizzes to Word documents, and track your daily study streak.

## Features

- **Conversational Tutoring:** A Socratic, patient tutor that guides you toward answers instead of just handing them over, adapting to your grade level and prior responses.
- **Web-Grounded Quiz Generation:** The `/quiz` command searches the web for reference material on your topic and generates a quiz (MCQ, True/False, Fill in the Blank, Short Answer, or Matching) scoped to what was actually found, with an answer key withheld until you ask for it.
- **Word Document Export:** The `/doc` command exports your last generated quiz to a `.docx` file — a clean student-facing version, an answer key, or both.
- **Reference Search:** The `/search` command looks up reference material for a topic on demand.
- **Daily Study Streak:** TutorBot tracks how many consecutive days you've opened the app, persisted locally so it survives restarts, and shows it as a flame next to the startup banner.
- **Runs Fully Locally:** Powered by a local GGUF model via `llama-cpp-python` — no API key or account required.

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Pip (Python package installer)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/AI-assistant.git
   cd AI-assistant-main
   ```

2. **Install the dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Download the language model:**
   - The application will automatically download the required language model on the first run.
   - The model will be saved in the `models/` directory.
   - If not working try running:
   ```bash
   hf download Qwen/Qwen2.5-0.5B-Instruct-GGUF qwen2.5-0.5b-instruct-q4_k_m.gguf --local-dir models
   ```

### Usage

1. **Run the application:**
   ```bash
   python main.py
   ```

2. **Interact with the bot:**
   - The main interface will appear in your terminal.
   - Type a question to chat with the tutor directly, or use a slash command:

   | Command | Usage | Description |
   |---|---|---|
   | `/quiz` | `/quiz <topic>` | Generate a quiz on a topic |
   | `/doc` | `/doc [answers\|split]` | Export the last quiz to a Word document |
   | `/search` | `/search <query>` | Search the web for reference material |
   | `/model` | `/model` | Show current model information |
   | `/clear` | `/clear` | Clear the conversation |
   | `/help` | `/help` | Show all available commands |
   | `/exit` | `/exit` | Exit TutorBot |

   - Press `ctrl+l` to clear conversation history, `ctrl+j` to refocus the input box.

## Project Structure

- `main.py`: The main entry point for the application. It initializes and runs the Textual user interface.
- `config.py`: Contains configuration settings, such as the language model path and the tutor/quiz/doc-formatter system prompts.
- `model.py`: Manages the interaction with the local language model, including loading the model and generating responses.
- `context_fetcher.py`: Searches the web and extracts readable page text to give the model real reference material for quizzes.
- `doc_generator.py`: Parses structured quiz text and generates `.docx` quiz and answer-key documents.
- `quiz_generator.py`: Builds the quiz-generation prompt, pulls in web context, and normalizes the model's output into a parseable format.
- `streak.py`: Tracks and persists the user's daily usage streak to `streak_data.json`.
- `streak_data.json`: Local persisted record of the current and longest streak. Created automatically on first run.
- `ui/`: The directory for all user interface components.
  - `app.py`: The core of the Textual-based user interface, including the startup banner, chat view, and command handling.
  - `commands.py`: Defines the application's slash-command registry.
  - `theme.tcss`: The stylesheet that defines the look and feel of the UI.
- `models/`: This directory stores the language models. It is created automatically on the first run.
- `requirements.txt`: A list of the Python packages required for the project.
- `LICENSE`: The GNU General Public License v3.0 for the project.
- `.gitignore`: Specifies which files and directories to exclude from version control.
- `README.md`: The file you are currently reading.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue if you have any suggestions or find any bugs.

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.