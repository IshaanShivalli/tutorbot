<<<<<<< HEAD


import json 
from dataclasses import dataclass 
from pathlib import Path 

GAMIFICATION_FILE =Path (__file__ ).resolve ().parent /"gamification_data.json"



XP_REWARDS ={
"chat_message":5 ,
"quiz_generated":20 ,
"quiz_question":3 ,
"doc_exported":10 ,
"search":5 ,
"streak_day":10 ,
}



LEVEL_THRESHOLDS =[0 ,50 ,120 ,220 ,350 ,520 ,730 ,1000 ,1350 ,1800 ,2400 ]
LEVEL_TITLES =[
"Curious Newcomer","Eager Learner","Diligent Student","Rising Scholar",
"Knowledge Seeker","Sharp Thinker","Dedicated Scholar","Master Student",
"Wisdom Chaser","Learning Legend","TutorBot Grandmaster",
]


BADGES ={
"first_quiz":("\U0001F3AF","First Quiz","Generate your first quiz."),
"quiz_5":("\U0001F4DA","Quiz Regular","Generate 5 quizzes."),
"quiz_20":("\U0001F3C6","Quiz Master","Generate 20 quizzes."),
"first_doc":("\U0001F4C4","Paper Trail","Export your first Word document."),
"doc_5":("\U0001F5C2","Document Master","Export 5 Word documents."),
"chatty_25":("\U0001F4AC","Chatty","Send 25 chat messages."),
"chatty_100":("\U0001F5E3","Conversationalist","Send 100 chat messages."),
"explorer_5":("\U0001F9ED","Explorer","Study 5 different topics."),
"explorer_15":("\U0001F30D","World Explorer","Study 15 different topics."),
"streak_3":("\U0001F525","On a Roll","Reach a 3-day streak."),
"streak_7":("\U0001F525","Week Warrior","Reach a 7-day streak."),
"streak_30":("\U0001F525","Unstoppable","Reach a 30-day streak."),
}


def _default_state ()->dict :
    return {
    "xp":0 ,
    "quizzes_generated":0 ,
    "docs_exported":0 ,
    "messages_sent":0 ,
    "searches_run":0 ,
    "topics":[],
    "badges":[],
    }


def _load_raw ()->dict :
    if not GAMIFICATION_FILE .exists ():
        return {}
    try :
        with open (GAMIFICATION_FILE ,"r",encoding ="utf-8")as f :
            return json .load (f )
    except (json .JSONDecodeError ,OSError ):
        return {}


def _save_raw (data :dict )->None :
    try :
        with open (GAMIFICATION_FILE ,"w",encoding ="utf-8")as f :
            json .dump (data ,f ,indent =2 )
    except OSError :
        pass 


def level_for_xp (xp :int ):
    
    level =1 
    for i ,threshold in enumerate (LEVEL_THRESHOLDS ):
        if xp >=threshold :
            level =i +1 
    level =min (level ,len (LEVEL_THRESHOLDS ))
    title =LEVEL_TITLES [level -1 ]

    current_floor =LEVEL_THRESHOLDS [level -1 ]
    next_ceiling =LEVEL_THRESHOLDS [level ]if level <len (LEVEL_THRESHOLDS )else None 

    xp_into_level =xp -current_floor 
    xp_for_next =(next_ceiling -current_floor )if next_ceiling is not None else None 
    return level ,title ,xp_into_level ,xp_for_next 


@dataclass 
class ActionResult :
    xp_gained :int 
    total_xp :int 
    level :int 
    title :str 
    leveled_up :bool 
    new_badges :list 


def _check_new_badges (state :dict ,streak_count :int )->list :
    unlocked =set (state ["badges"])
    newly =[]

    def unlock (bid ):
        if bid not in unlocked :
            unlocked .add (bid )
            newly .append ((bid ,*BADGES [bid ]))

    if state ["quizzes_generated"]>=1 :
        unlock ("first_quiz")
    if state ["quizzes_generated"]>=5 :
        unlock ("quiz_5")
    if state ["quizzes_generated"]>=20 :
        unlock ("quiz_20")
    if state ["docs_exported"]>=1 :
        unlock ("first_doc")
    if state ["docs_exported"]>=5 :
        unlock ("doc_5")
    if state ["messages_sent"]>=25 :
        unlock ("chatty_25")
    if state ["messages_sent"]>=100 :
        unlock ("chatty_100")
    if len (state ["topics"])>=5 :
        unlock ("explorer_5")
    if len (state ["topics"])>=15 :
        unlock ("explorer_15")
    if streak_count >=3 :
        unlock ("streak_3")
    if streak_count >=7 :
        unlock ("streak_7")
    if streak_count >=30 :
        unlock ("streak_30")

    state ["badges"]=sorted (unlocked )
    return newly 


def record_action (action :str ,topic :str =None ,question_count :int =0 ,streak_count :int =0 )->ActionResult :
    
    state =_load_raw ()or _default_state ()
    for key ,default in _default_state ().items ():
        state .setdefault (key ,default )

    xp_gain =XP_REWARDS .get (action ,0 )
    if action =="quiz_generated":
        state ["quizzes_generated"]+=1 
        xp_gain +=XP_REWARDS ["quiz_question"]*max (0 ,question_count )
    elif action =="doc_exported":
        state ["docs_exported"]+=1 
    elif action =="chat_message":
        state ["messages_sent"]+=1 
    elif action =="search":
        state ["searches_run"]+=1 

    if topic :
        normalized =topic .strip ().lower ()
        if normalized and normalized not in state ["topics"]:
            state ["topics"].append (normalized )

    old_level ,*_ =level_for_xp (state ["xp"])
    state ["xp"]+=xp_gain 
    new_level ,title ,_ ,_ =level_for_xp (state ["xp"])

    new_badges =_check_new_badges (state ,streak_count )

    _save_raw (state )

    return ActionResult (
    xp_gained =xp_gain ,
    total_xp =state ["xp"],
    level =new_level ,
    title =title ,
    leveled_up =new_level >old_level ,
    new_badges =new_badges ,
    )


def get_profile (streak_count :int =0 )->dict :
    
    state =_load_raw ()or _default_state ()
    for key ,default in _default_state ().items ():
        state .setdefault (key ,default )

    level ,title ,xp_into ,xp_for_next =level_for_xp (state ["xp"])
    return {
    "xp":state ["xp"],
    "level":level ,
    "title":title ,
    "xp_into_level":xp_into ,
    "xp_for_next_level":xp_for_next ,
    "quizzes_generated":state ["quizzes_generated"],
    "docs_exported":state ["docs_exported"],
    "messages_sent":state ["messages_sent"],
    "searches_run":state ["searches_run"],
    "topics_studied":len (state ["topics"]),
    "badges":state ["badges"],
    "streak":streak_count ,
=======


import json 
from dataclasses import dataclass 
from pathlib import Path 

GAMIFICATION_FILE =Path (__file__ ).resolve ().parent /"gamification_data.json"



XP_REWARDS ={
"chat_message":5 ,
"quiz_generated":20 ,
"quiz_question":3 ,
"doc_exported":10 ,
"search":5 ,
"streak_day":10 ,
}



LEVEL_THRESHOLDS =[0 ,50 ,120 ,220 ,350 ,520 ,730 ,1000 ,1350 ,1800 ,2400 ]
LEVEL_TITLES =[
"Curious Newcomer","Eager Learner","Diligent Student","Rising Scholar",
"Knowledge Seeker","Sharp Thinker","Dedicated Scholar","Master Student",
"Wisdom Chaser","Learning Legend","TutorBot Grandmaster",
]


BADGES ={
"first_quiz":("\U0001F3AF","First Quiz","Generate your first quiz."),
"quiz_5":("\U0001F4DA","Quiz Regular","Generate 5 quizzes."),
"quiz_20":("\U0001F3C6","Quiz Master","Generate 20 quizzes."),
"first_doc":("\U0001F4C4","Paper Trail","Export your first Word document."),
"doc_5":("\U0001F5C2","Document Master","Export 5 Word documents."),
"chatty_25":("\U0001F4AC","Chatty","Send 25 chat messages."),
"chatty_100":("\U0001F5E3","Conversationalist","Send 100 chat messages."),
"explorer_5":("\U0001F9ED","Explorer","Study 5 different topics."),
"explorer_15":("\U0001F30D","World Explorer","Study 15 different topics."),
"streak_3":("\U0001F525","On a Roll","Reach a 3-day streak."),
"streak_7":("\U0001F525","Week Warrior","Reach a 7-day streak."),
"streak_30":("\U0001F525","Unstoppable","Reach a 30-day streak."),
}


def _default_state ()->dict :
    return {
    "xp":0 ,
    "quizzes_generated":0 ,
    "docs_exported":0 ,
    "messages_sent":0 ,
    "searches_run":0 ,
    "topics":[],
    "badges":[],
    }


def _load_raw ()->dict :
    if not GAMIFICATION_FILE .exists ():
        return {}
    try :
        with open (GAMIFICATION_FILE ,"r",encoding ="utf-8")as f :
            return json .load (f )
    except (json .JSONDecodeError ,OSError ):
        return {}


def _save_raw (data :dict )->None :
    try :
        with open (GAMIFICATION_FILE ,"w",encoding ="utf-8")as f :
            json .dump (data ,f ,indent =2 )
    except OSError :
        pass 


def level_for_xp (xp :int ):
    
    level =1 
    for i ,threshold in enumerate (LEVEL_THRESHOLDS ):
        if xp >=threshold :
            level =i +1 
    level =min (level ,len (LEVEL_THRESHOLDS ))
    title =LEVEL_TITLES [level -1 ]

    current_floor =LEVEL_THRESHOLDS [level -1 ]
    next_ceiling =LEVEL_THRESHOLDS [level ]if level <len (LEVEL_THRESHOLDS )else None 

    xp_into_level =xp -current_floor 
    xp_for_next =(next_ceiling -current_floor )if next_ceiling is not None else None 
    return level ,title ,xp_into_level ,xp_for_next 


@dataclass 
class ActionResult :
    xp_gained :int 
    total_xp :int 
    level :int 
    title :str 
    leveled_up :bool 
    new_badges :list 


def _check_new_badges (state :dict ,streak_count :int )->list :
    unlocked =set (state ["badges"])
    newly =[]

    def unlock (bid ):
        if bid not in unlocked :
            unlocked .add (bid )
            newly .append ((bid ,*BADGES [bid ]))

    if state ["quizzes_generated"]>=1 :
        unlock ("first_quiz")
    if state ["quizzes_generated"]>=5 :
        unlock ("quiz_5")
    if state ["quizzes_generated"]>=20 :
        unlock ("quiz_20")
    if state ["docs_exported"]>=1 :
        unlock ("first_doc")
    if state ["docs_exported"]>=5 :
        unlock ("doc_5")
    if state ["messages_sent"]>=25 :
        unlock ("chatty_25")
    if state ["messages_sent"]>=100 :
        unlock ("chatty_100")
    if len (state ["topics"])>=5 :
        unlock ("explorer_5")
    if len (state ["topics"])>=15 :
        unlock ("explorer_15")
    if streak_count >=3 :
        unlock ("streak_3")
    if streak_count >=7 :
        unlock ("streak_7")
    if streak_count >=30 :
        unlock ("streak_30")

    state ["badges"]=sorted (unlocked )
    return newly 


def record_action (action :str ,topic :str =None ,question_count :int =0 ,streak_count :int =0 )->ActionResult :
    
    state =_load_raw ()or _default_state ()
    for key ,default in _default_state ().items ():
        state .setdefault (key ,default )

    xp_gain =XP_REWARDS .get (action ,0 )
    if action =="quiz_generated":
        state ["quizzes_generated"]+=1 
        xp_gain +=XP_REWARDS ["quiz_question"]*max (0 ,question_count )
    elif action =="doc_exported":
        state ["docs_exported"]+=1 
    elif action =="chat_message":
        state ["messages_sent"]+=1 
    elif action =="search":
        state ["searches_run"]+=1 

    if topic :
        normalized =topic .strip ().lower ()
        if normalized and normalized not in state ["topics"]:
            state ["topics"].append (normalized )

    old_level ,*_ =level_for_xp (state ["xp"])
    state ["xp"]+=xp_gain 
    new_level ,title ,_ ,_ =level_for_xp (state ["xp"])

    new_badges =_check_new_badges (state ,streak_count )

    _save_raw (state )

    return ActionResult (
    xp_gained =xp_gain ,
    total_xp =state ["xp"],
    level =new_level ,
    title =title ,
    leveled_up =new_level >old_level ,
    new_badges =new_badges ,
    )


def get_profile (streak_count :int =0 )->dict :
    
    state =_load_raw ()or _default_state ()
    for key ,default in _default_state ().items ():
        state .setdefault (key ,default )

    level ,title ,xp_into ,xp_for_next =level_for_xp (state ["xp"])
    return {
    "xp":state ["xp"],
    "level":level ,
    "title":title ,
    "xp_into_level":xp_into ,
    "xp_for_next_level":xp_for_next ,
    "quizzes_generated":state ["quizzes_generated"],
    "docs_exported":state ["docs_exported"],
    "messages_sent":state ["messages_sent"],
    "searches_run":state ["searches_run"],
    "topics_studied":len (state ["topics"]),
    "badges":state ["badges"],
    "streak":streak_count ,
>>>>>>> 6696ff70c425dd6f93af6c93d97bcaa324f38300
    }