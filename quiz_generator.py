import re 

from model import ask_ai 
from config import QUIZ_SYSTEM_PROMPT ,DOC_SYSTEM_PROMPT 
from context_fetcher import get_context_for_topic 


def normalize_quiz_text (raw_text :str )->str :
    
    normalized =raw_text .replace ("\r\n","\n").replace ("\r","\n")
    normalized =re .sub (r"\s*(TITLE:)\s*",r"\nTITLE: ",normalized ,flags =re .IGNORECASE )
    normalized =re .sub (r"\s*(SUBTITLE:)\s*",r"\nSUBTITLE: ",normalized ,flags =re .IGNORECASE )
    normalized =re .sub (r"\s*(SOURCE:)\s*",r"\nSOURCE: ",normalized ,flags =re .IGNORECASE )
    normalized =re .sub (r"\s*(Q\d+:)\s*",r"\n\1 ",normalized ,flags =re .IGNORECASE )
    normalized =re .sub (r"\s*(TYPE:)\s*",r"\nTYPE: ",normalized ,flags =re .IGNORECASE )
    normalized =re .sub (r"\s*(OPTIONS:)\s*",r"\nOPTIONS:\n",normalized ,flags =re .IGNORECASE )
    normalized =re .sub (r"\s*A\)\s*",r"\nA) ",normalized )
    normalized =re .sub (r"\s*B\)\s*",r"\nB) ",normalized )
    normalized =re .sub (r"\s*C\)\s*",r"\nC) ",normalized )
    normalized =re .sub (r"\s*D\)\s*",r"\nD) ",normalized )
    normalized =re .sub (r"\s*(ANSWER:)\s*",r"\nANSWER: ",normalized ,flags =re .IGNORECASE )
    normalized =re .sub (r"\s*EXPLANATION:\s*",r"\nEXPLANATION: ",normalized ,flags =re .IGNORECASE )
    normalized =re .sub (r"\n{3,}","\n\n",normalized )
    return normalized .strip ()


def _count_quiz_questions (raw_text :str )->int :
    return len (re.findall (r"\bQ\d+:", raw_text ,flags =re .IGNORECASE ))


def _present_question_numbers (raw_text :str )->set [int ]:
    present =set ()
    blocks =re .split (r"\n(?=Q\d+:)",raw_text )
    for block in blocks :
        q_match =re .search (r"\bQ(\d+):",block ,flags =re .IGNORECASE )
        if not q_match :
            continue 
        required =("TYPE:","OPTIONS:","ANSWER:","EXPLANATION:")
        normalized_block =block .upper ()
        if all (field in normalized_block for field in required ):
            present .add (int (q_match .group (1 )))
    return present


def _missing_question_numbers (raw_text :str ,expected_count :int )->list [int ]:
    present =_present_question_numbers (raw_text )
    return [number for number in range (1 ,expected_count +1 )if number not in present ]


def _trim_after_expected_questions (raw_text :str ,expected_count :int )->str :
    next_question =re .search (rf"\nQ{expected_count +1}:",raw_text ,flags =re .IGNORECASE )
    if next_question :
        return raw_text [:next_question .start ()].strip ()
    return raw_text .strip ()


def generate_quiz (
topic ,
grade ="Grade 9",
number_of_questions =5 ,
quiz_type ="MCQ",
use_web_context =True ,
include_images =False ,
extra_instructions :str ="",
quiz_language ="English",
):
    
    number_of_questions =max (1 ,min (number_of_questions ,20 ))
    context =None 
    source_title =None 

    if use_web_context :
        print (f"[quiz_generator] Fetching reference material for: {topic}")
        context ,source_title =get_context_for_topic (topic ,max_chars =1200 )


    if context :
        reference_material_section =f"""**REFERENCE MATERIAL:**
Source: {source_title}

{context}
"""
    else :
        print ("[quiz_generator] No web context found.")
        reference_material_section ="**REFERENCE MATERIAL:** None provided. Generate clear conceptual questions based on the topic."

    if extra_instructions :
        extra_instructions ="\n\n" + extra_instructions



    image_instruction =""
    if include_images :
        image_instruction ="""
For questions where a visual would genuinely improve learning, add a line:
IMAGE_SUGGESTION: <short description of a useful educational image>
Only add image suggestions when a visual is highly relevant."""

    language_instruction =""
    if quiz_language and quiz_language .lower ()!="english":
        language_instruction =(
        f"- Write all student-facing quiz text in {quiz_language}. "
        "Keep field labels exactly in English: TITLE, SUBTITLE, SOURCE, Q<n>, TYPE, OPTIONS, ANSWER, EXPLANATION.\n"
        )

    prompt =f"""
Create a clean {quiz_type} quiz for a {grade} student on the topic: {topic}.

Requirements:
- Generate exactly {number_of_questions} questions.
- Use the {quiz_type} format only.
- Keep explanations short and clear.
- If reference material is provided, stay strictly within it.
- Make all answer choices distinct and plausible.
- Do not repeat the same phrasing or the same question structure.
- Do not include any introductory text, commentary, or section headers outside the quiz.
- Use a real newline after every field and option.
- Do not use any rude, offensive, slang, or inappropriate language.
- Do not stop early. The output must contain all {number_of_questions} questions and answers.
- The quiz size is capped at 20 questions.
- Every question must include Q<number>, TYPE, OPTIONS, ANSWER, and EXPLANATION.
- The final question must be Q{number_of_questions}.
{language_instruction}
{image_instruction}{extra_instructions}

Output this exact structure and nothing else. Write Q1 through Q{number_of_questions}.

TITLE: {topic} Quiz
SUBTITLE: {grade} - {topic}
SOURCE: {source_title if source_title else 'General knowledge'}

Q1: <question>
TYPE: MCQ
OPTIONS:
A) <option>
B) <option>
C) <option>
D) <option>
ANSWER: <letter>
EXPLANATION: <one-sentence explanation>

Q2: <question>
TYPE: MCQ
OPTIONS:
A) <option>
B) <option>
C) <option>
D) <option>
ANSWER: <letter>
EXPLANATION: <one-sentence explanation>

Continue numbering all questions through Q{number_of_questions}.

{reference_material_section}

Generate the quiz now.
"""




    max_tokens =min (7600 ,number_of_questions *320 +550 )
    quiz =ask_ai (
    [
    {
    "role":"user",
    "content":prompt 
    }
    ],
    QUIZ_SYSTEM_PROMPT ,
    max_tokens =max_tokens ,
    temperature =0.2 ,
    top_p =0.9 ,
    repeat_penalty =1.05 ,
    )

    quiz =normalize_quiz_text (quiz )
    for _ in range (4 ):
        missing =_missing_question_numbers (quiz ,number_of_questions )
        if not missing :
            break 

        first_missing =missing [0 ]
        print (f"[quiz_generator] Missing questions {missing}; continuing from Q{first_missing}...")
        continuation_prompt =(
        f"The quiz generated so far is incomplete. Add only the missing questions starting at Q{first_missing} "
        f"and continue through Q{number_of_questions}. "
        "Use the exact same plain-text structure. Do not include TITLE, SUBTITLE, or SOURCE again. "
        "Do not repeat earlier questions. Each added question must include TYPE, OPTIONS, ANSWER, and EXPLANATION."
        )
        continuation =ask_ai (
        [
        {
        "role":"user",
        "content":continuation_prompt +"\n\n"+quiz
        }
        ],
        QUIZ_SYSTEM_PROMPT ,
        max_tokens =min (7600 ,len (missing )*340 +550 ),
        temperature =0.2 ,
        top_p =0.9 ,
        repeat_penalty =1.05 ,
        )
        continuation =normalize_quiz_text (continuation )
        quiz =normalize_quiz_text (quiz +"\n\n"+continuation )

    return _trim_after_expected_questions (quiz ,number_of_questions )


def reformat_quiz_for_doc (
quiz_content ,
topic ,
grade ="Grade 9",
quiz_type ="MCQ"
):
    

    if "TITLE:"in quiz_content and "Q1:"in quiz_content :
        return quiz_content 

    lines =quiz_content .strip ().splitlines ()
    raw_text =" ".join (line .strip ()for line in lines if line .strip ())

    question_pattern =re .compile (
    r"(?:\d+\.?\s*)?Question:\s*(.*?)\s*A\)\s*(.*?)\s*B\)\s*(.*?)\s*C\)\s*(.*?)\s*D\)\s*(.*?)\s*Answer:\s*([A-D])\)?\s*(.*?)\s*Explanation:\s*(.*?)(?=(?:\d+\.?\s*Question:|$))",
    re .IGNORECASE |re .DOTALL ,
    )

    questions =[]
    for match in question_pattern .finditer (raw_text ):
        q_text =match .group (1 ).strip ()
        options =[
        ("A",match .group (2 ).strip ()),
        ("B",match .group (3 ).strip ()),
        ("C",match .group (4 ).strip ()),
        ("D",match .group (5 ).strip ()),
        ]
        answer =match .group (6 ).strip ().upper ()
        explanation =match .group (7 ).strip ()
        questions .append ((q_text ,options ,answer ,explanation ))

    if not questions :


        return quiz_content 

    structured =[
    f"TITLE: {topic} Quiz",
    f"SUBTITLE: {grade} - {topic}",
    "SOURCE: General knowledge",
    "",
    ]

    for idx ,(q_text ,options ,answer ,explanation )in enumerate (questions ,start =1 ):
        structured .append (f"Q{idx}: {q_text}")
        structured .append (f"TYPE: {quiz_type}")
        structured .append ("OPTIONS:")
        for label ,opt_text in options :
            structured .append (f"{label}) {opt_text}")
        structured .append (f"ANSWER: {answer}")
        structured .append (f"EXPLANATION: {explanation}")
        structured .append ("")

    return "\n".join (structured )
