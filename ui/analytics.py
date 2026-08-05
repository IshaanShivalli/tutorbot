

import json 
from collections import Counter ,defaultdict 
from datetime import datetime ,date ,timedelta 
from pathlib import Path 

ANALYTICS_FILE =Path (__file__ ).resolve ().parent /"analytics_log.jsonl"


MAX_EVENTS_READ =20000 


def log_event (event_type :str ,**meta )->None :
    
    entry ={
    "ts":datetime .now ().isoformat (timespec ="seconds"),
    "type":event_type ,
    **meta ,
    }
    try :
        with open (ANALYTICS_FILE ,"a",encoding ="utf-8")as f :
            f .write (json .dumps (entry )+"\n")
    except OSError :
        pass 


def _read_events ()->list :
    if not ANALYTICS_FILE .exists ():
        return []
    events =[]
    try :
        with open (ANALYTICS_FILE ,"r",encoding ="utf-8")as f :
            for line in f :
                line =line .strip ()
                if not line :
                    continue 
                try :
                    events .append (json .loads (line ))
                except json .JSONDecodeError :
                    continue 
                if len (events )>=MAX_EVENTS_READ :
                    break 
    except OSError :
        pass 
    return events 


def build_report (days :int =7 )->dict :
    
    events =_read_events ()

    totals =Counter (e .get ("type")for e in events )
    topic_counter =Counter (
    (e .get ("topic")or "").strip ().lower ()
    for e in events 
    if e .get ("type")=="quiz_generated"and e .get ("topic")
    )

    by_day =defaultdict (int )
    cutoff =date .today ()-timedelta (days =days -1 )
    for e in events :
        try :
            ts =datetime .fromisoformat (e ["ts"])
        except (KeyError ,ValueError ):
            continue 
        d =ts .date ()
        if d >=cutoff :
            by_day [d .isoformat ()]+=1 

    first_used =None 
    if events :
        parsed_dates =[]
        for e in events :
            try :
                parsed_dates .append (datetime .fromisoformat (e ["ts"]).date ())
            except (KeyError ,ValueError ):
                continue 
        if parsed_dates :
            first_used =min (parsed_dates ).isoformat ()

    return {
    "total_events":len (events ),
    "messages_sent":totals .get ("chat_message",0 ),
    "quizzes_generated":totals .get ("quiz_generated",0 ),
    "docs_exported":totals .get ("doc_exported",0 ),
    "searches_run":totals .get ("search",0 ),
    "app_opens":totals .get ("app_open",0 ),
    "top_topics":topic_counter .most_common (5 ),
    "activity_by_day":sorted (by_day .items ()),
    "first_used":first_used ,
    }
