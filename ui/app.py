import random 
import re 
import sys 
from pathlib import Path 


sys .path .insert (0 ,str (Path (__file__ ).resolve ().parent .parent ))

from textual .app import App ,ComposeResult 
from textual .containers import VerticalScroll ,Horizontal 
from textual .widgets import Input ,Static 
from textual .reactive import reactive 
from textual import work 

from rich .console import Group 
from rich .markdown import Markdown 
from rich .table import Table 
from rich .text import Text 

from model import ask_ai 
from config import SYSTEM_PROMPT 
from quiz_generator import generate_quiz ,reformat_quiz_for_doc 
from doc_generator import create_quiz_document ,create_quiz_and_answer_key 
from context_fetcher import get_context_for_topic 
from vision_model import describe_image
from Server import extract_image_text
from .streak import update_streak_for_user, get_current_streak
import voice
from . import gamification ,analytics ,user_management
from .commands import COMMANDS ,find_command ,suggest_commands ,render_help_text 
from Server import google_translate, normalize_language


MAX_QUIZ_QUESTIONS =20 

MODEL_INFO ={
"Model":"Qwen2.5 0.5B Instruct",
"Format":"GGUF (Q4_K_M)",
"Context":"8192 tokens",
"Device":"CPU",
"Backend":"llama.cpp",
}






class MessageBubble (Static ):
    

    def __init__ (self ,role :str ,content :str ):
        self .role =role 
        prefix ={
        "user":"[bold #58a6ff]❯ You[/]\n",
        "assistant":"[bold #3fb950]● TutorBot[/]\n",
        "system":"[bold #d29922]ℹ System[/]\n",
        "error":"[bold #f85149]✖ Error[/]\n",
        }.get (role ,f"[bold]{role.title()}[/]\n")


        if role in ("assistant","user")and not content .startswith ("\n[bold"):






            md_content =re .sub (r"(?<!\n)\n(?!\n)","  \n",content )
            super ().__init__ (Group (prefix ,Markdown (md_content )),classes =role )
        else :
            super ().__init__ (f"{prefix}{content}"if role !="system"else content ,classes =role )


class SuggestionsBox (Static ):
    

    def update_suggestions (self ,partial :str ):
        matches =suggest_commands (partial )
        if not matches :
            self .display =False 
            self .remove_class ("visible")
            return 

        lines =["[bold cyan]Available commands[/bold cyan]"]
        for cmd in matches [:6 ]:
            lines .append (f"[cmd-name]{cmd.usage}[/cmd-name]  [dim]{cmd.description}[/dim]")
        self .update ("\n".join (lines ))
        self .add_class ("visible")
        self .display =True 

    def hide (self ):
        self .display =False 
        self .remove_class ("visible")


class ThinkingIndicator (Static ):
    

    FRAMES =["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]

    def on_mount (self )->None :
        self .frame_idx =0 
        self .update_spinner ()
        self .set_interval (0.08 ,self .update_spinner )

    def update_spinner (self )->None :
        frame =self .FRAMES [self .frame_idx ]
        self .frame_idx =(self .frame_idx +1 )%len (self .FRAMES )
        self .update (f"[bold #58a6ff]⸽[/] [bold #79c0ff]{frame}[/] [italic #8b949e]Thinking...[/]")






FLAME_ART_LINES =[
"█  ██   ",
"█ ████ █",
"  ██ █  ",
" ████ █ ",
" █ █ ██ ",
"  ████  "
]

FLAME_GRADIENT =[
"#ffe17d",
"#ffb347",
"#f0883e",
"#f85149",
"#c62828",
]

FLAME_UNLIT_COLOR ="#6e7681"


def render_flame (count :int )->str :
    
    if count <=0 :
        lines =FLAME_ART_LINES 
        art ="\n".join (f"[{FLAME_UNLIT_COLOR}]{line}[/]"for line in lines )
        label_color =FLAME_UNLIT_COLOR 
    else :
        art ="\n".join (
        f"[{color}]{line}[/]"
        for line ,color in zip (FLAME_ART_LINES ,FLAME_GRADIENT )
        )
        label_color =FLAME_GRADIENT [-2 ]

    number =f"[bold {label_color}]{count}[/]"
    label ="[dim]day streak[/]"
    return f"{art}\n{number}\n{label}"






class TutorBotApp (App ):

    TITLE ="TutorBot"
    CSS_PATH ="theme.tcss"

    BINDINGS =[
    ("ctrl+c","quit","Exit"),
    ("ctrl+l","clear_chat","Clear Chat"),
    ("ctrl+j","focus_input","Focus Input"),
    ]


    ASCII_ART ="""
[bold #58a6ff]████████╗██╗   ██╗████████╗ ██████╗ ██████╗ ██████╗  ██████╗ ████████╗[/]
[bold #58a6ff]╚══██╔══╝██║   ██║╚══██╔══╝██╔═══██╗██╔══██╗██╔══█╗╗██╔═══██╗╚══██╔══╝[/]
[bold #79c0ff]   ██║   ██║   ██║   ██║   ██║   ██║██████╔╝██████╔╝██║   ██║   ██║   [/]
[bold #79c0ff]   ██║   ██║   ██║   ██║   ██║   ██║██╔══██╗██╔══██╗██║   ██║   ██║   [/]
[bold #d2a8ff]   ██║   ╚██████╔╝   ██║   ╚██████╔╝██║  ██║██████╔╝╚██████╔╝   ██║   [/]
[bold #d2a8ff]   ╚═╝    ╚═════╝    ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚═════╝  ╚═════╝    ╚═╝   [/]
"""

    START_TIPS ="""
[bold #79c0ff]Tips for getting started:[/]
1. Ask educational questions, generate interactive quizzes, or export Word docs.
2. Use slash commands like [bold #d2a8ff]/quiz <topic>[/] or [bold #d2a8ff]/search <query>[/].
3. Press [bold #58a6ff]ctrl+l[/] to clear conversation history, [bold #58a6ff]ctrl+j[/] to refocus input.
"""
    def __init__ (self ):
        super ().__init__ ()
        self .history =[]
        self .last_quiz_content =None 
        self .last_quiz_doc_content =None 
        self .last_quiz_topic ="quiz"
        self .last_quiz_grade ="Grade 9"
        self .busy =False 
        self .message_count =0 
        self .quiz_count =0 
        self .preferred_language ="English"
        self .interface_language ="English"
        self .current_user =user_management .get_current_user ()



    def compose (self )->ComposeResult :
        yield Static ("",id ="status")
        yield VerticalScroll (id ="chat")
        yield ThinkingIndicator (id ="thinking-indicator")
        yield SuggestionsBox (id ="suggestions")

        with Horizontal (id ="input-row"):
            yield Static ("❯",id ="prompt-symbol")
            yield Input (
            id ="input",
            )

    def build_banner (self ,streak_count :int ):
        
        art_text =Text .from_markup (self .ASCII_ART .strip ("\n"))
        flame_text =Text .from_markup (render_flame (streak_count ))
        user_text =Text .from_markup (
        f"[bold #79c0ff]User:[/bold #79c0ff] {self .current_user ['username']} "
        f"([bold]{self .current_user ['role']}[/bold])"
        )

        grid =Table .grid (padding =(0 ,4 ))
        grid .add_column ()
        grid .add_column ()
        grid .add_row (art_text ,flame_text )
        grid .add_row (user_text ,Text ("") )
        return grid 

    def on_mount (self ):
        self .query_one ("#input",Input ).focus ()
        self .query_one ("#thinking-indicator",ThinkingIndicator ).display =False 
        self .query_one ("#suggestions",SuggestionsBox ).display =False 



        self .current_user =user_management .get_current_user ()
        streak =update_streak_for_user (self .current_user ['username'])
        self .streak_count =streak .count 



        self .add_message ("system",self .build_banner (streak .count ))
        self .update_status_banner ()
        self .add_message (
        "system",
        f"Logged in as [bold]{self .current_user ['username']}[/bold] ({self .current_user ['role']}).",
        )
        self .thought_message =self .add_message (
        "system",
        "[dim italic]Thinking of something inspiring...[/]",
        )
        self .add_message ("system",self .START_TIPS )


        self .run_thought_worker ()

        if streak .is_new_day and streak .count >1 :
            self .add_message (
            "system",
            f"[bold #f0883e]\U0001F525 {streak.count}-day streak![/] Keep it going.",
            )
            self ._track ("streak_day")

        self ._track ("app_open")




    def add_message (self ,role :str ,content :str ):
        chat =self .query_one ("#chat",VerticalScroll )
        bubble =MessageBubble (role ,content )
        chat .mount (bubble )
        chat .scroll_end (animate =False )

        if role in ("user","assistant"):
            self .message_count +=1 

        return bubble 

    def set_busy (self ,busy :bool ):
        self .busy =busy 
        self .query_one ("#thinking-indicator",ThinkingIndicator ).display =busy 

        input_widget =self .query_one ("#input",Input )
        input_widget .disabled =busy 
        if busy :
            input_widget .add_class ("disabled-input")
        else :
            input_widget .remove_class ("disabled-input")
            input_widget .focus ()



    def _track (self ,action :str ,topic :str =None ,question_count :int =0 ):
        try :
            streak_result =update_streak_for_user (self .current_user ['username'])
            self .streak_count =streak_result .count 
            if streak_result .is_new_day :
                try :
                    analytics .log_event ("streak_day" )
                except Exception :
                    pass 
                try :
                    result =gamification .record_action (
                    "streak_day" ,
                    streak_count =self .streak_count ,
                    )
                    self ._notify_gamification (result )
                except Exception :
                    pass 
                self .update_status_banner ()
        except Exception :
            pass 

        try :
            analytics .log_event (action ,topic =topic )
        except Exception :
            pass 

        try :
            result =gamification .record_action (
            action ,
            topic =topic ,
            question_count =question_count ,
            streak_count =getattr (self ,"streak_count",0 ),
            )
            self ._notify_gamification (result )
        except Exception :
            pass 

    def _notify_gamification (self ,result ):
        if result .leveled_up :
            self .add_message (
            "system",
            f"[bold #d29922]\u2728 Level up![/] You're now "
            f"[bold]Level {result.level} - {result.title}[/bold] "
            f"({result.total_xp} XP total).",
            )
        for _bid ,emoji ,name ,desc in result .new_badges :
            self .add_message (
            "system",
            f"[bold #79c0ff]{emoji} Badge unlocked: {name}[/] - {desc}",
            )



    def on_input_changed (self ,event :Input .Changed ):
        value =event .value 
        suggestions =self .query_one ("#suggestions",SuggestionsBox )

        if value .startswith ("/")and len (value )>=1 :
            suggestions .update_suggestions (value )
        else :
            suggestions .hide ()

    def on_input_submitted (self ,event :Input .Submitted ):
        message =event .value .strip ()
        if not message or self .busy :
            return 

        event .input .value =""
        self .query_one ("#suggestions",SuggestionsBox ).hide ()

        self .add_message ("user",message )

        if message .startswith ("/"):
            self .dispatch_command (message )
        else :
            self .history .append ({"role":"user","content":message })
            self ._track ("chat_message")
            self .run_chat_worker ()



    def dispatch_command (self ,raw :str ):
        parts =raw .split (" ",1 )
        cmd_name =parts [0 ].lower ()
        argument =parts [1 ].strip ()if len (parts )>1 else ""

        cmd =find_command (cmd_name )
        if not cmd :
            self .add_message (
            "error",
            f"Unknown command: {cmd_name}\nType [bold]/help[/bold] to see available commands.",
            )
            return 

        handler =getattr (self ,cmd .handler_name ,None )
        if handler is None :
            self .add_message ("error",f"Command '{cmd_name}' has no handler implemented.")
            return 

        handler (argument )



    def handle_help (self ,argument :str ):
        self .add_message ("system",render_help_text ())

    def handle_model_info (self ,argument :str ):
        lines =[f"[bold]{k}:[/bold] {v}"for k ,v in MODEL_INFO .items ()]
        self .add_message ("system","\n".join (lines ))

    def handle_language (self ,argument :str ):
        if not argument .strip ():
            self .add_message ("error","Usage: /language <language>")
            return 
        self .preferred_language =normalize_language (argument .strip ())
        self .add_message (
        "system",
        f"Preferred response language set to [bold]{self.preferred_language}[/bold] for this terminal session.",
        )

    def handle_clear (self ,argument :str ):
        self .action_clear_chat ()

    def handle_exit (self ,argument :str ):
        self .exit ()

    def handle_search (self ,argument :str ):
        if not argument :
            self .add_message ("error","Usage: /search <query>")
            return 
        self .run_search_worker (argument )

    def update_status_banner (self ):
        try :
            status =self .query_one ("#status",Static )
            status .update (
            f"[bold #79c0ff]Logged in as:[/bold #79c0ff] {self .current_user ['username']} "
            f"([bold]{self .current_user ['role']}[/bold])"
            )
        except Exception :
            pass 

    def handle_login (self ,argument :str ):
        tokens =argument .split ()
        if len (tokens )!=2 :
            self .add_message ("error","Usage: /login <username> <password>")
            return 
        username ,password =tokens 
        try :
            user ,verification ,sent =user_management .login (username ,password )
            self .add_message (
            "system",
            f"Password verified. Use code [bold]{verification['code']}[/bold] with [bold]/verify {username} <code>[/bold] to complete login.",
            )
        except KeyError as e :
            self .add_message ("error",str (e ))
        except ValueError as e :
            self .add_message ("error",str (e ))
        except Exception as e :
            self .add_message ("error",f"Login failed: {e}")

    def handle_register (self ,argument :str ):
        tokens =argument .split ()
        if len (tokens )!=4 :
            self .add_message (
            "error",
            "Usage: /register <username> <email> <password> <confirm_password>",
            )
            return 
        username ,email ,password ,confirm_password =tokens 
        if password !=confirm_password :
            self .add_message ("error","Password and confirmation do not match.")
            return 
        try :
            user ,verification ,sent =user_management .register (username ,email ,password )
            self .add_message (
            "system",
            f"Account created for [bold]{user['username']}[/bold]. Use code [bold]{verification['code']}[/bold] with [bold]/verify {username} <code>[/bold] to complete registration.",
            )
        except KeyError as e :
            self .add_message ("error",str (e ))
        except ValueError as e :
            self .add_message ("error",str (e ))
        except Exception as e :
            self .add_message ("error",f"Registration failed: {e}")

    def handle_logout (self ,argument :str ):
        try :
            user =user_management .logout ()
            self .current_user =user
            self .update_status_banner ()
            self .add_message (
            "system",
            f"Logged out. Current user is [bold]{user['username']}[/bold] ({user['role']}).",
            )
        except Exception as e :
            self .add_message ("error",f"Logout failed: {e}")

    def handle_verify (self ,argument :str ):
        tokens =argument .split ()
        if len (tokens )not in (2 ,3 ):
            self .add_message (
            "error",
            "Usage: /verify <username> <code> [register|login]",
            )
            return 
        username =tokens [0 ]
        code =tokens [1 ]
        purpose =tokens [2 ]if len (tokens )==3 else None 
        try :
            user =user_management .verify (username ,code ,purpose )
            self .current_user =user
            self .update_status_banner ()
            self .add_message (
            "system",
            f"Verified and logged in as [bold]{user['username']}[/bold] ({user['role']}).",
            )
        except KeyError as e :
            self .add_message ("error",str (e ))
        except ValueError as e :
            self .add_message ("error",str (e ))
        except Exception as e :
            self .add_message ("error",f"Verification failed: {e}")

    def handle_users (self ,argument :str ):
        if not user_management .is_admin (self .current_user ['username'] ):
            self .add_message ("error","Access denied. /users is admin only.")
            return 
        users =user_management .list_users ()
        lines =["[bold cyan]Known users[/bold cyan]"]
        for user in users :
            lines .append (f"- [bold]{user['username']}[/bold] ({user['role']})")
        self .add_message ("system",
        "\n".join (lines ),
        )

    def handle_setrole (self ,argument :str ):
        if not user_management .is_admin (self .current_user ['username'] ):
            self .add_message ("error","Access denied. /setrole is admin only.")
            return 
        tokens =argument .split ()
        if len (tokens )!=2 :
            self .add_message ("error","Usage: /setrole <username> <student|admin>")
            return 
        username ,role =tokens 
        try :
            user =user_management .set_user_role (username ,role )
            self .add_message (
            "system",
            f"Set [bold]{user['username']}[/bold] to role [bold]{user['role']}[/bold].",
            )
        except Exception as e :
            self .add_message ("error",f"Could not set role: {e}")

    def handle_quiz (self ,argument :str ):
        if not argument :
            self .add_message (
            "error",
            "Usage: /quiz <topic>\n\nExample:\n/quiz Photosynthesis grade=8 count=5 web=y",
            )
            return 

        topic ,grade ,count ,use_web ,requested_count =self ._parse_quiz_args (argument )
        if requested_count >MAX_QUIZ_QUESTIONS :
            self .add_message (
            "system",
            f"[bold]Note:[/bold] quizzes are capped at {MAX_QUIZ_QUESTIONS} questions "
            f"(you asked for {requested_count}) - generating {count} instead.",
            )
        self .add_message (
        "system",
        f"Generating a {count}-question quiz on [bold]{topic}[/bold] "
        f"({grade}, web reference: {'yes' if use_web else 'no'})...",
        )
        self .run_quiz_worker (topic ,grade ,count ,use_web )

    def handle_doc (self ,argument :str ):
        if not self .last_quiz_content :
            self .add_message ("error","No quiz has been generated yet. Run /quiz first.")
            return 

        arg =argument .lower ().strip ()
        self .run_doc_worker (arg )

    def handle_stats (self ,argument :str ):
        try :
            streak = get_current_streak ()
            self .streak_count = streak .count
            profile =gamification .get_profile (streak_count =self .streak_count )
            current_user = self .current_user ['username']
            weak_subject = user_management .get_user (current_user ) .get ("weak_subject") or "None"
        except Exception as e :
            self .add_message ("error",f"Couldn't load stats: {e}")
            return 

        xp_for_next =profile ["xp_for_next_level"]
        if xp_for_next :
            pct =min (100 ,int (profile ["xp_into_level"]/xp_for_next *100 ))
            filled =pct //5 
            bar ="█"*filled +"░"*(20 -filled )
            progress_line =f"{bar}  {profile['xp_into_level']}/{xp_for_next} XP to next level"
        else :
            progress_line ="[bold]Max level reached![/bold]"

        badge_lines =[]
        if profile ["badges"]:
            for bid in profile ["badges"]:
                emoji ,name ,desc =gamification .BADGES [bid ]
                badge_lines .append (f"  {emoji} [bold]{name}[/bold] - {desc}")
        else :
            badge_lines .append ("  [dim]No badges yet - keep learning to unlock some![/dim]")

        lines =[
        f"[bold #d29922]Level {profile['level']} - {profile['title']}[/bold #d29922]  "
        f"({profile['xp']} XP total)",
        progress_line ,
        "",
        f"[bold]Weak subject:[/bold] {weak_subject}",
        f"[bold]Quizzes generated:[/bold] {profile['quizzes_generated']}",
        f"[bold]Documents exported:[/bold] {profile['docs_exported']}",
        f"[bold]Messages sent:[/bold] {profile['messages_sent']}",
        f"[bold]Topics studied:[/bold] {profile['topics_studied']}",
        f"[bold]Current streak:[/bold] {profile['streak']} day(s)",
        "",
        "[bold #79c0ff]Badges:[/bold #79c0ff]",
        *badge_lines ,
        ]
        self .add_message ("system","\n".join (lines ))

    def handle_report (self ,argument :str ):
        try :
            report =analytics .build_report (days =7 )
        except Exception as e :
            self .add_message ("error",f"Couldn't build report: {e}")
            return 

        lines =[
        "[bold #79c0ff]Activity Report (last 7 days)[/bold #79c0ff]",
        "",
        f"[bold]Messages sent:[/bold] {report['messages_sent']}",
        f"[bold]Quizzes generated:[/bold] {report['quizzes_generated']}",
        f"[bold]Documents exported:[/bold] {report['docs_exported']}",
        f"[bold]Searches run:[/bold] {report['searches_run']}",
        ]

        if report ["first_used"]:
            lines .append (f"[bold]Tracking since:[/bold] {report['first_used']}")

        if report ["activity_by_day"]:
            lines .append ("")
            lines .append ("[bold]Daily activity:[/bold]")
            max_count =max (count for _ ,count in report ["activity_by_day"])or 1 
            for day ,count in report ["activity_by_day"]:
                bar_len =max (1 ,int (count /max_count *20 ))if count else 0 
                lines .append (f"  {day}  {'█' * bar_len} {count}")
        else :
            lines .append ("")
            lines .append ("[dim]No activity recorded yet.[/dim]")

        if report.get("performance_graph"):
            lines .append ("")
            lines .append ("[bold]Performance graph:[/bold]")
            lines .extend (report["performance_graph"])

        if report ["top_topics"]:
            lines .append ("")
            lines .append ("[bold]Top quiz topics:[/bold]")
            for topic ,count in report ["top_topics"]:
                lines .append (f"  - {topic.title()} ({count})")

        self .add_message ("system","\n".join (lines ))



    def handle_weaksubject (self ,argument :str ):
        subject =argument .strip ()
        if not subject :
            self .add_message ("error","Usage: /weaksubject <subject>")
            return 
        try :
            user =user_management .set_user_weak_subject (self .current_user ['username'] ,subject )
            self .add_message (
            "system",
            f"Weak subject set to [bold]{user['weak_subject']}[/bold]. TutorBot will prioritize explanations and examples for that area.",
            )
        except Exception as e :
            self .add_message ("error",f"Could not set weak subject: {e}")

    def _spell_words (self ):
        return {
        "Grade 6":["abandon","behavior","chronology","dialogue","endeavor","fantastic","geometry","horizon"],
        "Grade 7":["accommodation","beneficial","characteristic","differentiate","enthusiasm","fluctuation"],
        "Grade 8":["achievement","belligerent","conspicuous","deteriorate","exaggerate","formidable"],
        "Grade 9":["aesthetic","benevolent","cacophony","deference","ephemeral","fortuitous","gregarious"],
        "Grade 10":["acquiesce","capricious","dichotomy","equivocal","fastidious","harangue"],
        "Grade 11":["anachronism","camaraderie","deleterious","facetious","grandiloquent","mendacious"],
        "Grade 12":["chicanery","desultory","egregious","fecund","insidious","mellifluous"],
        "College":["anathema","bilious","crepuscular","diaphanous","exculpate","hegemony"],
        "Adult":["sesquipedalian","supercalifragilisticexpialidocious","tergiversation"],
        }

    def _current_grade (self ):
        user =user_management .get_user (self .current_user ["username"])or {}
        return user .get ("grade")or "Grade 9"

    def handle_spell (self ,argument :str ):
        word =argument .strip ()
        if not word :
            words =self ._spell_words ()
            word =random .choice (words .get (self ._current_grade (),words ["Grade 8"]))
        try :
            user =user_management .update_user_profile (
            self .current_user ["username"],
            last_spell_word =word ,
            spelling_sessions =(user_management .get_user (self .current_user ["username"])or {}).get ("spelling_sessions",0 )+1 ,
            )
            self .current_user =user
        except Exception :
            pass
        try :
            voice .say_text (word)
            spoken_message = "Pronouncing the word now."
        except Exception :
            spoken_message = "Could not play pronunciation locally; please read the word aloud."
        self .add_message (
        "system",
        f"[bold #79c0ff]Spelling practice[/bold #79c0ff]\n"
        f"Word: [bold]{word}[/bold]\n"
        f"{spoken_message}",
        )
        self ._track ("spell_practice",topic =word )

    def handle_dictate (self ,argument :str ):
        words =self ._spell_words ()
        word =argument .strip ()or random .choice (words .get (self ._current_grade (),words ["Grade 9"]))
        try :
            user =user_management .update_user_profile (
            self .current_user ["username"],
            last_dictation_word =word ,
            dictation_sessions =(user_management .get_user (self .current_user ["username"])or {}).get ("dictation_sessions",0 )+1 ,
            )
            self .current_user =user
        except Exception :
            pass
        self .add_message (
        "system",
        f"[bold #79c0ff]Dictation[/bold #79c0ff]\n"
        f"Dictate this word to the student: [bold]{word}[/bold]\n"
        "Then have them type it in the CLI input or use the timed web Dictation button.",
        )
        self ._track ("dictation_practice",topic =word )

    def handle_theme (self ,argument :str ):
        tokens =argument .split ()
        if not tokens :
            self .add_message ("error","Usage: /theme <dark|light|custom> [ink] [panel] [accent] [text]")
            return
        mode =tokens [0 ].lower ()
        if mode not in ("dark","light","custom"):
            self .add_message ("error","Theme must be dark, light, or custom.")
            return
        theme ={"mode":mode}
        if mode =="custom":
            labels =("ink","panel","accent","text")
            for label ,value in zip (labels ,tokens [1:]):
                if not re .match (r"^#[0-9a-fA-F]{6}$",value ):
                    self .add_message ("error",f"{label} must be a hex color like #58a6ff.")
                    return
                theme [label]=value
        try :
            user =user_management .update_user_profile (self .current_user ["username"],theme =theme )
            self .current_user =user
        except Exception as e :
            self .add_message ("error",f"Could not save theme: {e}")
            return
        self .add_message ("system",f"Saved theme preference: [bold]{mode}[/bold]. The web app can use matching custom colors from Settings.")

    def handle_survey (self ,argument :str ):
        tokens =argument .split ("|")
        if len (tokens )>=3:
            grade ,subject ,weak_subject =[part .strip ()for part in tokens [:3]]
            try :
                user =user_management .update_user_profile (
                self .current_user ["username"],
                grade =grade or "Grade 9",
                subject =subject or "General",
                weak_subject =weak_subject or "None",
                survey_filled =True ,
                )
                self .current_user =user
                self .add_message ("system",f"Survey saved: [bold]{user.get('grade')}[/bold] - [bold]{user.get('subject')}[/bold].")
            except Exception as e :
                self .add_message ("error",f"Could not save survey: {e}")
            return
        questions =user_management .get_survey_questions ()
        lines =["[bold #79c0ff]Student survey[/bold #79c0ff]","Use: [bold]/survey Grade 9 | Science | Algebra[/bold]",""]
        lines .extend (f"- {q.get('label',q.get('key'))}"for q in questions )
        self .add_message ("system","\n".join (lines ))

    def handle_history (self ,argument :str ):
        if argument .strip ().lower ()in ("clear","delete"):
            self .history .clear ()
            self .add_message ("system","CLI chat history deleted for this session.")
            return
        user =user_management .get_user (self .current_user ["username"])or {}
        streak = get_current_streak ()
        self .streak_count = streak .count
        profile =gamification .get_profile (streak_count =self .streak_count )
        recent =self .history [-8 :]
        lines =[
        "[bold #79c0ff]Account History & Analysis[/bold #79c0ff]",
        f"[bold]User:[/bold] {self.current_user['username']}",
        f"[bold]Grade:[/bold] {user.get('grade','Grade 9')}",
        f"[bold]Preferred subject:[/bold] {user.get('subject','General')}",
        f"[bold]Weak subject:[/bold] {user.get('weak_subject','None')}",
        f"[bold]Level:[/bold] {profile['level']} - {profile['title']} ({profile['xp']} XP)",
        f"[bold]Current streak:[/bold] {profile['streak']} day(s)",
        f"[bold]Spelling sessions:[/bold] {user.get('spelling_sessions',0)}",
        f"[bold]Dictation sessions:[/bold] {user.get('dictation_sessions',0)}",
        "",
        "[bold]Recent chat:[/bold]",
        ]
        if recent :
            for item in recent :
                lines .append (f"- {item['role']}: {item['content'][:90]}")
        else :
            lines .append ("[dim]No chat history in this CLI session yet.[/dim]")
        self .add_message ("system","\n".join (lines ))

    def handle_image (self ,argument :str ):
        image_path =Path (argument .strip ().strip ('"'))
        if not argument .strip ():
            self .add_message ("error","Usage: /image <path>")
            return
        if not image_path .exists ()or not image_path .is_file ():
            self .add_message ("error",f"Image file not found: {image_path}")
            return
        self .run_image_worker (image_path )

    def _parse_quiz_args (self ,argument :str ):
        
        tokens =argument .split ()
        topic_tokens =[]
        grade ="Grade 9"
        count =5 
        requested_count =count 
        use_web =True 

        for token in tokens :
            if "="in token :
                key ,_ ,value =token .partition ("=")
                key =key .lower ().lstrip ("-")


                if key =="grade":
                    if value .isdigit ():
                        grade =f"Grade {value}"
                    elif value :
                        grade =value 
                elif key in ("count","questions","question","num"):
                    if value :
                        try :
                            requested_count =int (value )
                            count =requested_count 
                            if count <1 :
                                count =5 
                                requested_count =count 
                            elif count >MAX_QUIZ_QUESTIONS :
                                count =MAX_QUIZ_QUESTIONS 
                        except ValueError :
                            pass 
                elif key =="web":
                    use_web =value .lower ()in ("y","yes","true","1")
            else :
                topic_tokens .append (token )


        topic =" ".join (topic_tokens ).strip ()
        if not topic :


            topic =argument 

        return topic ,grade ,count ,use_web ,requested_count 



    @staticmethod 
    def _looks_like_factual_question (text :str )->bool :
        
        stripped =text .strip ()
        if len (stripped )<8 :
            return False 

        lowered =stripped .lower ()

        casual_starters =(
        "hi","hello","hey","thanks","thank you","ok","okay",
        "cool","nice","yes","no","sure","i like","i feel",
        "i think","i want to say","i'm","im ",
        )
        if lowered .startswith (casual_starters ):
            return False 

        has_question_mark ="?"in stripped 
        interrogative_starters =(
        "what","why","how","when","where","who","which",
        "explain","define","describe","tell me about",
        )
        starts_interrogative =lowered .startswith (interrogative_starters )

        return (has_question_mark or starts_interrogative )and len (stripped .split ())>=3 

    @work (thread =True ,exclusive =True )
    def run_chat_worker (self ):
        self .call_from_thread (self .set_busy ,True )
        try :
            user_msg =self .history [-1 ]["content"]
            force_english =(
            getattr (self ,"preferred_language","English").lower ()!="english"
            and getattr (self ,"preferred_language","English").lower ()==getattr (self ,"interface_language","English").lower ()
            )
            model_user_msg =user_msg
            if getattr (self ,"preferred_language","English").lower ()!="english":
                model_user_msg =google_translate (user_msg ,"English",source_language =self .preferred_language)
                self .history [-1 ]["content"]=model_user_msg

            language_prompt =""
            language_prompt ="\n\n=== RESPONSE LANGUAGE ===\nAlways answer in English. Do not translate your own output.\n"
            system_prompt =SYSTEM_PROMPT +language_prompt 





            weak_subject = user_management .get_user (self .current_user ['username'] ) .get ("weak_subject")
            subject_prompt =""
            if weak_subject :
                subject_prompt =(
                f"\n\n=== WEAK SUBJECT FOCUS ===\n"
                f"The user has identified {weak_subject} as a weak subject. "
                f"When answering, prioritize clearer explanations, examples, and practice in that area when it is relevant to the question.\n"
                )
            if self ._looks_like_factual_question (model_user_msg ):
                search_context ,source =get_context_for_topic (model_user_msg ,max_chars =2000 )

                if search_context :
                    system_prompt =(
                    f"{SYSTEM_PROMPT}\n\n"
                    f"=== ADDITIONAL GROUNDING CONTEXT ===\n"
                    f"Use the following real-time reference context to answer the user's question accurately. "
                    f"Prioritize accuracy and detail based on this source info. "
                    f"Source: {source}\n"
                    f"Context: {search_context}\n"
                    f"{subject_prompt}"
                    f"{language_prompt}"
                    )
                else :
                    system_prompt = SYSTEM_PROMPT + subject_prompt +language_prompt
            else :
                system_prompt = SYSTEM_PROMPT + subject_prompt +language_prompt





            result =ask_ai (self .history ,system_prompt ,max_tokens =1024 )
            if getattr (self ,"preferred_language","English").lower ()!="english"and not force_english:
                result =google_translate (result ,self .preferred_language,source_language ="English")
            self .history .append ({"role":"assistant","content":result })
            self .call_from_thread (self .add_message ,"assistant",result )
        except Exception as e :
            self .call_from_thread (self .add_message ,"error",f"Generation failed: {e}")
        finally :
            self .call_from_thread (self .set_busy ,False )

    @work (thread =True ,exclusive =True )
    def run_quiz_worker (self ,topic ,grade ,count ,use_web ):
        self .call_from_thread (self .set_busy ,True )
        try :
            weak_subject = user_management .get_user (self .current_user ['username'] ) .get ("weak_subject")
            extra_focus =""
            if weak_subject :
                extra_focus =(
                f"\nWhen the topic allows, weave in explanations or examples that help the user with {weak_subject}. "
                f"Prioritize clarity in that area while still staying on topic."
                )
            quiz_content =generate_quiz (
            topic =topic ,
            grade =grade ,
            number_of_questions =count ,
            use_web_context =use_web ,
            extra_instructions =extra_focus ,
            quiz_language =getattr (self ,"preferred_language","English"),
            )
            self .last_quiz_content =quiz_content 
            self .last_quiz_doc_content =None 
            self .last_quiz_topic =topic 
            self .last_quiz_grade =grade 

            self .call_from_thread (self .add_message ,"assistant",quiz_content )
            self .call_from_thread (self ._increment_quiz_count )
            self .call_from_thread (
            self ._track ,"quiz_generated",topic =topic ,question_count =count 
            )
            self .call_from_thread (
            self .add_message ,
            "system",
            "Quiz ready. Use [bold]/doc[/bold] to export it as a Word document, "
            "or [bold]/doc answers[/bold] to include the answer key.",
            )
        except Exception as e :
            self .call_from_thread (self .add_message ,"error",f"Quiz generation failed: {e}")
        finally :
            self .call_from_thread (self .set_busy ,False )

    @work (thread =True )
    def run_thought_worker (self ):
        
        try :
            seed_word =random .choice ([
            "curiosity",
            "growth",
            "learning",
            "confidence",
            "focus",
            "persistence",
            "creativity",
            "exploration",
            "progress",
            "resilience",
            ])
            thought =ask_ai (
            [{
            "role":"user",
            "content":(
            "Write exactly one short, original, encouraging thought "
            "for the day for a student. One sentence only."
            f" Use the word '{seed_word}'."
            " No quotation marks, no preamble, no author attribution, no emoji."
            ),
            }],
            "You are a concise, warm writer of short daily motivational thoughts for students."
            " Generate a new, unique thought each time.",
            max_tokens =40 ,
            temperature =1.0 ,
            top_p =0.9 ,
            )
            thought =thought .strip ().strip ('"').strip ()

            if not thought or len (thought )>220 :
                thought =None 
        except Exception :
            thought =None 

        if not thought :
            fallback_thoughts =[
            "Every step you take to learn makes tomorrow easier.",
            "Curiosity is the spark that turns questions into growth.",
            "A small bit of focus today builds confidence for tomorrow.",
            "Learning something new is a win, no matter how small.",
            "Persistence today creates strength for tomorrow's challenges.",
            ]
            thought =random .choice (fallback_thoughts )

        def _update ():
            self .thought_message .update (
            Group (
            "[bold #3fb950]\u25cf TutorBot[/]\n",
            f"[italic #d2a8ff]\u201c{thought}\u201d[/]",
            )
            )

        self .call_from_thread (_update )

    @work (thread =True ,exclusive =True )
    def run_search_worker (self ,query ):
        self .call_from_thread (self .set_busy ,True )
        try :
            context ,source =get_context_for_topic (query )
            if context :
                preview =context [:800 ]+("..."if len (context )>800 else "")
                self .call_from_thread (
                self .add_message ,
                "system",
                f"[bold]Source:[/bold] {source}\n\n{preview}",
                )
            else :
                self .call_from_thread (
                self .add_message ,"system",f"No reference material found for '{query}'."
                )
            self .call_from_thread (self ._track ,"search",topic =query )
        except Exception as e :
            self .call_from_thread (self .add_message ,"error",f"Search failed: {e}")
        finally :
            self .call_from_thread (self .set_busy ,False )

    @work (thread =True ,exclusive =True )
    def run_image_worker (self ,image_path ):
        self .call_from_thread (self .set_busy ,True )
        try :
            ocr_text =extract_image_text (image_path )or "No readable text was detected in the image."
            image_description =describe_image (image_path )
            prompt =(
            "I processed an image using OCR and layout analysis. "
            "Report only what is visible in the image and what text was extracted. "
            "Do not infer missing words or guess the meaning of the question. "
            "Do not solve anything unless it is explicitly shown in the image.\n\n"
            f"Image description:\n{image_description}\n\n"
            f"OCR text:\n{ocr_text}"
            )
            self .history .append ({"role":"user","content":prompt })
            response =ask_ai (
            self .history ,
            SYSTEM_PROMPT +"\n\nAlways answer in English. Do not translate your own output.",
            max_tokens =1024 ,
            )
            if getattr (self ,"preferred_language","English").lower ()!="english":
                response =google_translate (response ,self .preferred_language,source_language ="English")
            self .history .append ({"role":"assistant","content":response })
            self .call_from_thread (self .add_message ,"assistant",response )
            self .call_from_thread (self ._track ,"image_analysis",topic =str (image_path .name ))
        except Exception as e :
            self .call_from_thread (self .add_message ,"error",f"Image analysis failed: {e}")
        finally :
            self .call_from_thread (self .set_busy ,False )

    @work (thread =True ,exclusive =True )
    def run_doc_worker (self ,arg :str ):
        self .call_from_thread (self .set_busy ,True )
        try :





            if self .last_quiz_doc_content is None :
                self .call_from_thread (
                self .add_message ,"system","Preparing document..."
                )
                self .last_quiz_doc_content =reformat_quiz_for_doc (
                self .last_quiz_content ,
                topic =self .last_quiz_topic ,
                grade =self .last_quiz_grade ,
                )

            doc_content =self .last_quiz_doc_content 
            safe_topic ="_".join (self .last_quiz_topic .lower ().split ())

            if arg =="answers":
                path =create_quiz_document (
                doc_content ,
                output_path =f"{safe_topic}_quiz_with_answers.docx",
                include_answers =True ,
                )
                self .call_from_thread (
                self .add_message ,"system",f"Saved document with answers: [bold]{path}[/bold]"
                )

            elif arg =="split":
                quiz_path ,answer_path =create_quiz_and_answer_key (
                doc_content ,
                quiz_path =f"{safe_topic}_quiz.docx",
                answer_key_path =f"{safe_topic}_answer_key.docx",
                )
                self .call_from_thread (
                self .add_message ,
                "system",
                f"Saved quiz: [bold]{quiz_path}[/bold]\nSaved answer key: [bold]{answer_path}[/bold]",
                )

            else :
                path =create_quiz_document (
                doc_content ,
                output_path =f"{safe_topic}_quiz.docx",
                include_answers =False ,
                )
                self .call_from_thread (
                self .add_message ,
                "system",
                f"Saved quiz document: [bold]{path}[/bold]\n"
                "Tip: use [bold]/doc answers[/bold] or [bold]/doc split[/bold] for answer keys.",
                )

            self .call_from_thread (self ._track ,"doc_exported",topic =self .last_quiz_topic )
        except Exception as e :
            self .call_from_thread (self .add_message ,"error",f"Failed to create document: {e}")
        finally :
            self .call_from_thread (self .set_busy ,False )

    def _increment_quiz_count (self ):
        self .quiz_count +=1 



    def action_clear_chat (self ):
        self .history .clear ()
        self .last_quiz_content =None 
        self .last_quiz_doc_content =None 

        chat =self .query_one ("#chat",VerticalScroll )
        chat .remove_children ()

        self .message_count =0 
        self .quiz_count =0 

        self .add_message ("system","Conversation cleared.")

    def action_focus_input (self ):
        self .query_one ("#input",Input ).focus ()


if __name__ =="__main__":
    TutorBotApp ().run ()
