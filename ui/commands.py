"""
commands.py

Central registry of slash commands for the TutorBot TUI.
Keeping this separate from app.py means the App class just dispatches to
these handlers, and new commands can be added here without touching the
widget/layout code.
"""

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class Command:
    name: str                 # e.g. "/quiz"
    description: str          # shown in /help and the command palette
    usage: str                # e.g. "/quiz <topic>"
    handler_name: str         # method name on TutorBotApp to call


# The single source of truth for every supported command.
# app.py looks up `getattr(self, cmd.handler_name)` and calls it with the
# raw argument string.
COMMANDS: list[Command] = [
    Command(
        name="/quiz",
        description="Generate a quiz on a topic",
        usage="/quiz <topic>",
        handler_name="handle_quiz",
    ),
    Command(
        name="/doc",
        description="Export the last quiz to a Word document",
        usage="/doc [answers|split]",
        handler_name="handle_doc",
    ),
    Command(
        name="/search",
        description="Search the web for reference material",
        usage="/search <query>",
        handler_name="handle_search",
    ),
    Command(
        name="/model",
        description="Show current model information",
        usage="/model",
        handler_name="handle_model_info",
    ),
    Command(
        name="/clear",
        description="Clear the conversation",
        usage="/clear",
        handler_name="handle_clear",
    ),
    Command(
        name="/help",
        description="Show all available commands",
        usage="/help",
        handler_name="handle_help",
    ),
    Command(
        name="/exit",
        description="Exit TutorBot",
        usage="/exit",
        handler_name="handle_exit",
    ),
]


def find_command(name: str) -> Optional[Command]:
    """Exact match lookup, e.g. '/quiz' -> Command(...)."""
    name = name.lower()
    for cmd in COMMANDS:
        if cmd.name == name:
            return cmd
    return None


def suggest_commands(partial: str) -> list[Command]:
    """Prefix match for autocomplete, e.g. '/qu' -> [/quiz]."""
    partial = partial.lower()
    return [cmd for cmd in COMMANDS if cmd.name.startswith(partial)]


def render_help_text() -> str:
    """Builds the /help output from the registry, so it never goes stale."""
    lines = ["[bold cyan]TutorBot Commands[/bold cyan]\n"]
    for cmd in COMMANDS:
        lines.append(f"[bold]{cmd.usage}[/bold]")
        lines.append(f"  {cmd.description}\n")
    return "\n".join(lines)