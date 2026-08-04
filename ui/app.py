"""
app.py

TutorBot TUI — a Claude Code / Gemini CLI style terminal interface built with Textual.
"""

import re
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, Horizontal
from textual.widgets import Input, Static
from textual.reactive import reactive
from textual import work

from rich.console import Group
from rich.markdown import Markdown
from rich.table import Table
from rich.text import Text

from model import ask_ai
from config import SYSTEM_PROMPT
from quiz_generator import generate_quiz, reformat_quiz_for_doc
from doc_generator import create_quiz_document, create_quiz_and_answer_key
from context_fetcher import get_context_for_topic
from .streak import update_streak_on_open
from .commands import COMMANDS, find_command, suggest_commands, render_help_text


MAX_QUIZ_QUESTIONS = 20

MODEL_INFO = {
    "Model": "Qwen2.5 0.5B Instruct",
    "Format": "GGUF (Q4_K_M)",
    "Context": "8192 tokens",
    "Device": "CPU",
    "Backend": "llama.cpp",
}


# ============================================================
# Widgets
# ============================================================

class MessageBubble(Static):
    """A single chat message, styled like a CLI session transcript with left accent borders and Markdown formatting."""

    def __init__(self, role: str, content: str):
        self.role = role
        prefix = {
            "user": "[bold #58a6ff]❯ You[/]\n",
            "assistant": "[bold #3fb950]● TutorBot[/]\n",
            "system": "[bold #d29922]ℹ System[/]\n",
            "error": "[bold #f85149]✖ Error[/]\n",
        }.get(role, f"[bold]{role.title()}[/]\n")

        # Parse assistant and user outputs as Markdown for syntax-highlighted code blocks
        if role in ("assistant", "user") and not content.startswith("\n[bold"):
            # Rich's Markdown renderer treats a single "\n" as a soft break
            # (collapsed to a space), so plain structured text (like our
            # quiz output, which only has single newlines between fields)
            # gets squished onto one line. Force each existing newline to
            # be a hard line break, but leave already-blank lines alone so
            # real Markdown paragraphs/lists still render normally.
            md_content = re.sub(r"(?<!\n)\n(?!\n)", "  \n", content)
            super().__init__(Group(prefix, Markdown(md_content)), classes=role)
        else:
            super().__init__(f"{prefix}{content}" if role != "system" else content, classes=role)


class SuggestionsBox(Static):
    """Shows matching slash commands as the user types '/'."""

    def update_suggestions(self, partial: str):
        matches = suggest_commands(partial)
        if not matches:
            self.display = False
            self.remove_class("visible")
            return

        lines = []
        for cmd in matches[:6]:
            lines.append(f"[cmd-name]{cmd.usage}[/cmd-name]  [dim]{cmd.description}[/dim]")
        self.update("\n".join(lines))
        self.add_class("visible")
        self.display = True

    def hide(self):
        self.display = False
        self.remove_class("visible")


class ThinkingIndicator(Static):
    """A custom animated thinking indicator using the vertical 6 dots and braille frames."""

    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def on_mount(self) -> None:
        self.frame_idx = 0
        self.update_spinner()
        self.set_interval(0.08, self.update_spinner)

    def update_spinner(self) -> None:
        frame = self.FRAMES[self.frame_idx]
        self.frame_idx = (self.frame_idx + 1) % len(self.FRAMES)
        self.update(f"[bold #58a6ff]⸽[/] [bold #79c0ff]{frame}[/] [italic #8b949e]Thinking...[/]")

# Small blocky flame built from the same solid-block character used in
# the TUTORBOT wordmark (█), so it reads as part of the same "font"
# instead of a mismatched glyph. Each row gets its own color, hottest
# (yellow-white) at the tip fading down to deep red at the base, so it
# reads as fire rather than a flat silhouette.
FLAME_ART_LINES = [
    "  ██  ",
    " ████ ",
    " ████ ",
    "██████",
    "██████",
]

FLAME_GRADIENT = [
    "#ffe17d",  # hot tip - pale yellow
    "#ffb347",  # yellow-orange
    "#f0883e",  # orange
    "#f85149",  # red-orange
    "#c62828",  # deep red base
]

FLAME_UNLIT_COLOR = "#6e7681"


def render_flame(count: int) -> str:
    """Builds the flame block as markup text. A live streak uses the
    warm multi-color gradient above; a streak of 0 renders as a single
    dim/unlit color to signal the user hasn't studied yet."""
    if count <= 0:
        lines = FLAME_ART_LINES
        art = "\n".join(f"[{FLAME_UNLIT_COLOR}]{line}[/]" for line in lines)
        label_color = FLAME_UNLIT_COLOR
    else:
        art = "\n".join(
            f"[{color}]{line}[/]"
            for line, color in zip(FLAME_ART_LINES, FLAME_GRADIENT)
        )
        label_color = FLAME_GRADIENT[-2]  # orange-red, easy to read

    number = f"[bold {label_color}]{count}[/]"
    label = "[dim]day streak[/]"
    return f"{art}\n{number}\n{label}"


# ============================================================
# Main App
# ============================================================

class TutorBotApp(App):

    TITLE = "TutorBot"
    CSS_PATH = "theme.tcss"

    BINDINGS = [
        ("ctrl+c", "quit", "Exit"),
        ("ctrl+l", "clear_chat", "Clear Chat"),
        ("ctrl+j", "focus_input", "Focus Input"),
    ]

    # Beautiful blocky ASCII art matching Claude / Gemini CLI aesthetic
    ASCII_ART = """
[bold #58a6ff]████████╗██╗   ██╗████████╗ ██████╗ ██████╗ ██████╗  ██████╗ ████████╗[/]
[bold #58a6ff]╚══██╔══╝██║   ██║╚══██╔══╝██╔═══██╗██╔══██╗██╔══█╗╗██╔═══██╗╚══██╔══╝[/]
[bold #79c0ff]   ██║   ██║   ██║   ██║   ██║   ██║██████╔╝██████╔╝██║   ██║   ██║   [/]
[bold #79c0ff]   ██║   ██║   ██║   ██║   ██║   ██║██╔══██╗██╔══██╗██║   ██║   ██║   [/]
[bold #d2a8ff]   ██║   ╚██████╔╝   ██║   ╚██████╔╝██║  ██║██████╔╝╚██████╔╝   ██║   [/]
[bold #d2a8ff]   ╚═╝    ╚═════╝    ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚═════╝  ╚═════╝    ╚═╝   [/]
"""

    START_TIPS = """
[bold #79c0ff]Tips for getting started:[/]
1. Ask educational questions, generate interactive quizzes, or export Word docs.
2. Use slash commands like [bold #d2a8ff]/quiz <topic>[/] or [bold #d2a8ff]/search <query>[/].
3. Press [bold #58a6ff]ctrl+l[/] to clear conversation history, [bold #58a6ff]ctrl+j[/] to refocus input.
"""
    def __init__(self):
        super().__init__()
        self.history = []
        self.last_quiz_content = None   # raw conversational quiz text (shown in chat)
        self.last_quiz_doc_content = None  # structured version, reformatted for doc_generator
        self.last_quiz_topic = "quiz"
        self.last_quiz_grade = "Grade 9"
        self.busy = False
        self.message_count = 0
        self.quiz_count = 0

    # -------------------- Layout --------------------

    def compose(self) -> ComposeResult:
        yield VerticalScroll(id="chat")
        yield ThinkingIndicator(id="thinking-indicator")
        yield SuggestionsBox(id="suggestions")

        with Horizontal(id="input-row"):
            yield Static("❯", id="prompt-symbol")
            yield Input(
                id="input",
            )

    def build_banner(self, streak_count: int):
        """Combines the TUTORBOT wordmark and the streak flame into a
        single row, instead of the flame living in its own column."""
        art_text = Text.from_markup(self.ASCII_ART.strip("\n"))
        flame_text = Text.from_markup(render_flame(streak_count))

        grid = Table.grid(padding=(0, 4))
        grid.add_column()
        grid.add_column()
        grid.add_row(art_text, flame_text)
        return grid

    def on_mount(self):
        self.query_one("#input", Input).focus()
        self.query_one("#thinking-indicator", ThinkingIndicator).display = False
        self.query_one("#suggestions", SuggestionsBox).display = False

        # Update the day-streak, persisted across restarts, so the count
        # is ready before we render the banner.
        streak = update_streak_on_open()
        self.streak_count = streak.count

        # Render startup banner (logo + flame in the same row), thought-of-
        # the-day, & starter guide.
        self.add_message("system", self.build_banner(streak.count))
        self.thought_message = self.add_message(
            "system",
            "[dim italic]Thinking of something inspiring...[/]",
        )
        self.add_message("system", self.START_TIPS)

        # Try to replace the placeholder with a freshly generated thought.
        self.run_thought_worker()

        if streak.is_new_day and streak.count > 1:
            self.add_message(
                "system",
                f"[bold #f0883e]\U0001F525 {streak.count}-day streak![/] Keep it going.",
            )


    # -------------------- Helpers --------------------

    def add_message(self, role: str, content: str):
        chat = self.query_one("#chat", VerticalScroll)
        bubble = MessageBubble(role, content)
        chat.mount(bubble)
        chat.scroll_end(animate=False)

        if role in ("user", "assistant"):
            self.message_count += 1

        return bubble

    def set_busy(self, busy: bool):
        self.busy = busy
        self.query_one("#thinking-indicator", ThinkingIndicator).display = busy

        input_widget = self.query_one("#input", Input)
        input_widget.disabled = busy
        if busy:
            input_widget.add_class("disabled-input")
        else:
            input_widget.remove_class("disabled-input")
            input_widget.focus()

    # -------------------- Input handling --------------------

    def on_input_changed(self, event: Input.Changed):
        value = event.value
        suggestions = self.query_one("#suggestions", SuggestionsBox)

        if value.startswith("/") and len(value) >= 1:
            suggestions.update_suggestions(value)
        else:
            suggestions.hide()

    def on_input_submitted(self, event: Input.Submitted):
        message = event.value.strip()
        if not message or self.busy:
            return

        event.input.value = ""
        self.query_one("#suggestions", SuggestionsBox).hide()

        self.add_message("user", message)

        if message.startswith("/"):
            self.dispatch_command(message)
        else:
            self.history.append({"role": "user", "content": message})
            self.run_chat_worker()

    # -------------------- Command dispatch --------------------

    def dispatch_command(self, raw: str):
        parts = raw.split(" ", 1)
        cmd_name = parts[0].lower()
        argument = parts[1].strip() if len(parts) > 1 else ""

        cmd = find_command(cmd_name)
        if not cmd:
            self.add_message(
                "error",
                f"Unknown command: {cmd_name}\nType [bold]/help[/bold] to see available commands.",
            )
            return

        handler = getattr(self, cmd.handler_name, None)
        if handler is None:
            self.add_message("error", f"Command '{cmd_name}' has no handler implemented.")
            return

        handler(argument)

    # -------------------- Command handlers --------------------

    def handle_help(self, argument: str):
        self.add_message("system", render_help_text())

    def handle_model_info(self, argument: str):
        lines = [f"[bold]{k}:[/bold] {v}" for k, v in MODEL_INFO.items()]
        self.add_message("system", "\n".join(lines))

    def handle_clear(self, argument: str):
        self.action_clear_chat()

    def handle_exit(self, argument: str):
        self.exit()

    def handle_search(self, argument: str):
        if not argument:
            self.add_message("error", "Usage: /search <query>")
            return
        self.run_search_worker(argument)

    def handle_quiz(self, argument: str):
        if not argument:
            self.add_message(
                "error",
                "Usage: /quiz <topic>\n\nExample:\n/quiz Photosynthesis grade=8 count=5 web=y",
            )
            return

        topic, grade, count, use_web, requested_count = self._parse_quiz_args(argument)
        if requested_count > MAX_QUIZ_QUESTIONS:
            self.add_message(
                "system",
                f"[bold]Note:[/bold] quizzes are capped at {MAX_QUIZ_QUESTIONS} questions "
                f"(you asked for {requested_count}) - generating {count} instead.",
            )
        self.add_message(
            "system",
            f"Generating a {count}-question quiz on [bold]{topic}[/bold] "
            f"({grade}, web reference: {'yes' if use_web else 'no'})...",
        )
        self.run_quiz_worker(topic, grade, count, use_web)

    def handle_doc(self, argument: str):
        if not self.last_quiz_content:
            self.add_message("error", "No quiz has been generated yet. Run /quiz first.")
            return

        arg = argument.lower().strip()
        self.run_doc_worker(arg)

    # -------------------- Argument parsing --------------------

    def _parse_quiz_args(self, argument: str):
        """
        Parses '/quiz Mauryan Empire grade=8 count=5 web=n' into
        (topic, grade, count, use_web). Unknown key=value pairs are
        stripped out of the topic text.
        Supports both 'grade=' and '--grade=' formats for parameters.
        """
        tokens = argument.split()
        topic_tokens = []
        grade = "Grade 9"
        count = 5
        requested_count = count
        use_web = True

        for token in tokens:
            if "=" in token:
                key, _, value = token.partition("=")
                key = key.lower().lstrip("-")  # allow both "grade=" and "--grade="
                
                # Validate and parse each parameter
                if key == "grade":
                    if value.isdigit():
                        grade = f"Grade {value}"
                    elif value:
                        grade = value
                elif key in ("count", "questions", "question", "num"):
                    if value:
                        try:
                            requested_count = int(value)
                            count = requested_count
                            if count < 1:
                                count = 5  # Reset to default if invalid
                                requested_count = count
                            elif count > MAX_QUIZ_QUESTIONS:
                                count = MAX_QUIZ_QUESTIONS  # hard cap
                        except ValueError:
                            pass  # Keep default if parsing fails
                elif key == "web":
                    use_web = value.lower() in ("y", "yes", "true", "1")
            else:
                topic_tokens.append(token)

        # Ensure we have a valid topic
        topic = " ".join(topic_tokens).strip()
        if not topic:
            # Fallback: if only parameters provided, use the full argument
            # This is not ideal, so we'll let the handler show an error
            topic = argument
        
        return topic, grade, count, use_web, requested_count

    # -------------------- Background workers --------------------

    @staticmethod
    def _looks_like_factual_question(text: str) -> bool:
        """
        Heuristic gate for whether a chat message actually warrants a web
        search. Casual chat ("hi", "thanks", venting, opinions) should NOT
        trigger a search - only genuine knowledge questions should.
        """
        stripped = text.strip()
        if len(stripped) < 8:
            return False

        lowered = stripped.lower()

        casual_starters = (
            "hi", "hello", "hey", "thanks", "thank you", "ok", "okay",
            "cool", "nice", "yes", "no", "sure", "i like", "i feel",
            "i think", "i want to say", "i'm", "im ",
        )
        if lowered.startswith(casual_starters):
            return False

        has_question_mark = "?" in stripped
        interrogative_starters = (
            "what", "why", "how", "when", "where", "who", "which",
            "explain", "define", "describe", "tell me about",
        )
        starts_interrogative = lowered.startswith(interrogative_starters)

        return (has_question_mark or starts_interrogative) and len(stripped.split()) >= 3

    @work(thread=True, exclusive=True)
    def run_chat_worker(self):
        self.call_from_thread(self.set_busy, True)
        try:
            user_msg = self.history[-1]["content"]

            system_prompt = SYSTEM_PROMPT

            # Only search the web when the message actually looks like a
            # factual question - not on every casual chat turn, and keep
            # the retrieved context to a reasonable size (not tens of
            # thousands of characters of raw scraped page text).
            if self._looks_like_factual_question(user_msg):
                search_context, source = get_context_for_topic(user_msg, max_chars=2000)

                if search_context:
                    system_prompt = (
                        f"{SYSTEM_PROMPT}\n\n"
                        f"=== ADDITIONAL GROUNDING CONTEXT ===\n"
                        f"Use the following real-time reference context to answer the user's question accurately. "
                        f"Prioritize accuracy and detail based on this source info. "
                        f"Source: {source}\n"
                        f"Context: {search_context}\n"
                    )
                # No context found -> fall back to the base prompt silently.

            # Keep chat responses to a reasonable, focused length - a
            # 0.5B CPU model asked for up to 32k tokens with no stop
            # sequence tends to drift/degrade the longer it runs.
            result = ask_ai(self.history, system_prompt, max_tokens=1024)
            self.history.append({"role": "assistant", "content": result})
            self.call_from_thread(self.add_message, "assistant", result)
        except Exception as e:
            self.call_from_thread(self.add_message, "error", f"Generation failed: {e}")
        finally:
            self.call_from_thread(self.set_busy, False)

    @work(thread=True, exclusive=True)
    def run_quiz_worker(self, topic, grade, count, use_web):
        self.call_from_thread(self.set_busy, True)
        try:
            quiz_content = generate_quiz(
                topic=topic,
                grade=grade,
                number_of_questions=count,
                use_web_context=use_web,
            )
            self.last_quiz_content = quiz_content
            self.last_quiz_doc_content = None  # invalidate cached doc format for the new quiz
            self.last_quiz_topic = topic
            self.last_quiz_grade = grade

            self.call_from_thread(self.add_message, "assistant", quiz_content)
            self.call_from_thread(self._increment_quiz_count)
            self.call_from_thread(
                self.add_message,
                "system",
                "Quiz ready. Use [bold]/doc[/bold] to export it as a Word document, "
                "or [bold]/doc answers[/bold] to include the answer key.",
            )
        except Exception as e:
            self.call_from_thread(self.add_message, "error", f"Quiz generation failed: {e}")
        finally:
            self.call_from_thread(self.set_busy, False)

    @work(thread=True)
    def run_thought_worker(self):
        """Generates a short 'thought for the day' in the background and
        swaps it in for the placeholder shown at startup, without blocking
        the UI or the input box (busy state is untouched here)."""
        try:
            thought = ask_ai(
                [{
                    "role": "user",
                    "content": (
                        "Write exactly one short, original, encouraging thought "
                        "for the day for a student, about learning, curiosity, or "
                        "growth. One sentence only. No quotation marks, no preamble, "
                        "no author attribution, no emoji."
                    ),
                }],
                "You are a concise, warm writer of short daily motivational thoughts for students.",
                max_tokens=60,
                temperature=0.9,
            )
            thought = thought.strip().strip('"').strip()
            # Guard against a rambling/degenerate generation from the small model.
            if not thought or len(thought) > 220:
                thought = None
        except Exception:
            thought = None

        def _update():
            if thought:
                self.thought_message.update(
                    Group(
                        "[bold #3fb950]\u25cf TutorBot[/]\n",
                        f"[italic #d2a8ff]\u201c{thought}\u201d[/]",
                    )
                )
            else:
                # Generation failed or came back unusable - drop the
                # placeholder rather than leaving "Thinking..." stuck.
                self.thought_message.remove()

        self.call_from_thread(_update)

    @work(thread=True, exclusive=True)
    def run_search_worker(self, query):
        self.call_from_thread(self.set_busy, True)
        try:
            context, source = get_context_for_topic(query)
            if context:
                preview = context[:800] + ("..." if len(context) > 800 else "")
                self.call_from_thread(
                    self.add_message,
                    "system",
                    f"[bold]Source:[/bold] {source}\n\n{preview}",
                )
            else:
                self.call_from_thread(
                    self.add_message, "system", f"No reference material found for '{query}'."
                )
        except Exception as e:
            self.call_from_thread(self.add_message, "error", f"Search failed: {e}")
        finally:
            self.call_from_thread(self.set_busy, False)

    @work(thread=True, exclusive=True)
    def run_doc_worker(self, arg: str):
        self.call_from_thread(self.set_busy, True)
        try:
            # doc_generator.parse_quiz_text expects the structured
            # TITLE:/SOURCE:/Q1:/TYPE:/OPTIONS:/ANSWER:/EXPLANATION: format
            # produced by DOC_SYSTEM_PROMPT - NOT the conversational quiz
            # text shown in chat. Reformat once and cache it, since the
            # underlying quiz content doesn't change between /doc calls.
            if self.last_quiz_doc_content is None:
                self.call_from_thread(
                    self.add_message, "system", "Preparing document..."
                )
                self.last_quiz_doc_content = reformat_quiz_for_doc(
                    self.last_quiz_content,
                    topic=self.last_quiz_topic,
                    grade=self.last_quiz_grade,
                )

            doc_content = self.last_quiz_doc_content
            safe_topic = "_".join(self.last_quiz_topic.lower().split())

            if arg == "answers":
                path = create_quiz_document(
                    doc_content,
                    output_path=f"{safe_topic}_quiz_with_answers.docx",
                    include_answers=True,
                )
                self.call_from_thread(
                    self.add_message, "system", f"Saved document with answers: [bold]{path}[/bold]"
                )

            elif arg == "split":
                quiz_path, answer_path = create_quiz_and_answer_key(
                    doc_content,
                    quiz_path=f"{safe_topic}_quiz.docx",
                    answer_key_path=f"{safe_topic}_answer_key.docx",
                )
                self.call_from_thread(
                    self.add_message,
                    "system",
                    f"Saved quiz: [bold]{quiz_path}[/bold]\nSaved answer key: [bold]{answer_path}[/bold]",
                )

            else:
                path = create_quiz_document(
                    doc_content,
                    output_path=f"{safe_topic}_quiz.docx",
                    include_answers=False,
                )
                self.call_from_thread(
                    self.add_message,
                    "system",
                    f"Saved quiz document: [bold]{path}[/bold]\n"
                    "Tip: use [bold]/doc answers[/bold] or [bold]/doc split[/bold] for answer keys.",
                )
        except Exception as e:
            self.call_from_thread(self.add_message, "error", f"Failed to create document: {e}")
        finally:
            self.call_from_thread(self.set_busy, False)

    def _increment_quiz_count(self):
        self.quiz_count += 1

    # -------------------- Actions --------------------

    def action_clear_chat(self):
        self.history.clear()
        self.last_quiz_content = None
        self.last_quiz_doc_content = None

        chat = self.query_one("#chat", VerticalScroll)
        chat.remove_children()

        self.message_count = 0
        self.quiz_count = 0

        self.add_message("system", "Conversation cleared.")

    def action_focus_input(self):
        self.query_one("#input", Input).focus()


if __name__ == "__main__":
    TutorBotApp().run()