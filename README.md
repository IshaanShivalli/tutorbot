
# AI Tutor Bot

This project is an AI-powered tutor bot that helps users learn about various subjects. It uses a large language model to provide explanations, answer questions, and generate quizzes.

## Features

- **Conversational Tutoring:** Engage in a natural conversation with the AI tutor to get explanations and ask questions.
- **Document Analysis:** Provide documents (in .docx format) for the AI to analyze and answer questions about.
- **Quiz Generation:** Generate quizzes based on the conversation history or provided documents to test your knowledge.

## Getting Started

### Prerequisites

- Python 3.7 or higher
- Pip (Python package installer)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/isip962/tutorbot.git
   cd tutorbot
   ```

2. **Install the dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Download the language model:**
   - The application will automatically download the required language model on the first run.
   - The model will be saved in the `models/` directory.
   - If not working try running ```bash
    hf download Qwen/Qwen2.5-0.5B-Instruct-GGUF qwen2.5-0.5b-instruct-q4_k_m.gguf --local-dir models
    ```

### Usage

1. **Run the application:**
   ```bash
   python main.py
   ```

2. **Interact with the bot:**
   - The main interface will appear in your terminal.
   - Use the available commands to interact with the bot (e.g., `/ask`, `/quiz`, `/load`).

## Project Structure

- `main.py`: The main entry point for the application. It initializes and runs the Textual user interface.
- `config.py`: Contains configuration settings, such as the language model path and other constants.
- `model.py`: Manages the interaction with the large language model, including loading the model and generating responses.
- `context_fetcher.py`: Fetches and processes context from external sources like documents to provide relevant information to the model.
- `doc_generator.py`: Generates `.docx` documents from the conversation history.
- `quiz_generator.py`: Creates quizzes based on the conversation or provided documents.
- `ui/`: The directory for all user interface components.
  - `app.py`: The core of the Textual-based user interface.
  - `commands.py`: Defines the application's command system.
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