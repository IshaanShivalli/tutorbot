

from dataclasses import dataclass 
from typing import Callable ,Optional 


@dataclass 
class Command :
    name :str 
    description :str 
    usage :str 
    handler_name :str 





COMMANDS :list [Command ]=[
Command (
name ="/quiz",
description ="Generate a quiz on a topic",
usage ="/quiz <topic>",
handler_name ="handle_quiz",
),
Command (
name ="/doc",
description ="Export the last quiz to a Word document",
usage ="/doc [answers|split]",
handler_name ="handle_doc",
),
Command (
name ="/search",
description ="Search the web for reference material",
usage ="/search <query>",
handler_name ="handle_search",
),
Command (
name ="/model",
description ="Show current model information",
usage ="/model",
handler_name ="handle_model_info",
),
Command (
name ="/login",
description ="Switch to an existing user account",
usage ="/login <username> <password>",
handler_name ="handle_login",
),
Command (
name ="/register",
description ="Create a new student account and switch to it",
usage ="/register <username> <email> <password> <confirm_password>",
handler_name ="handle_register",
),
Command (
name ="/verify",
description ="Confirm registration or login with the code shown after register/login",
usage ="/verify <username> <code> [register|login]",
handler_name ="handle_verify",
),
Command (
name ="/logout",
description ="Return to the guest account",
usage ="/logout",
handler_name ="handle_logout",
),
Command (
name ="/weaksubject",
description ="Set your weakest subject so TutorBot can focus your practice",
usage ="/weaksubject <subject>",
handler_name ="handle_weaksubject",
),
Command (
name ="/users",
description ="List all known users (admin only)",
usage ="/users",
handler_name ="handle_users",
),
Command (
name ="/setrole",
description ="Set a user's role (admin only)",
usage ="/setrole <username> <student|admin>",
handler_name ="handle_setrole",
),
Command (
name ="/clear",
description ="Clear the conversation",
usage ="/clear",
handler_name ="handle_clear",
),
Command (
name ="/stats",
description ="View your XP, level, and badges",
usage ="/stats",
handler_name ="handle_stats",
),
Command (
name ="/report",
description ="View your activity report and analytics",
usage ="/report",
handler_name ="handle_report",
),
Command (
name ="/help",
description ="Show all available commands",
usage ="/help",
handler_name ="handle_help",
),
Command (
name ="/exit",
description ="Exit TutorBot",
usage ="/exit",
handler_name ="handle_exit",
),
]


def find_command (name :str )->Optional [Command ]:
    
    name =name .lower ()
    for cmd in COMMANDS :
        if cmd .name ==name :
            return cmd 
    return None 


def suggest_commands (partial :str )->list [Command ]:
    
    partial =partial .lower ()
    return [cmd for cmd in COMMANDS if cmd .name .startswith (partial )]


def render_help_text ()->str :
    
    lines =["[bold cyan]TutorBot Commands[/bold cyan]\n"]
    for cmd in COMMANDS :
        lines .append (f"[bold]{cmd.usage}[/bold]")
        lines .append (f"  {cmd.description}\n")
    return "\n".join (lines )