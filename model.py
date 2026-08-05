<<<<<<< HEAD
import os 

from llama_cpp import Llama 
from config import MODEL_PATH 


cpu_threads =max (1 ,min (8 ,os .cpu_count ()or 4 ))
llm =Llama (
model_path =MODEL_PATH ,
n_ctx =8192 ,
n_threads =cpu_threads ,
n_batch =256 ,
n_gpu_layers =0 ,
use_mmap =True ,
use_mlock =False ,
verbose =False ,
)


def ask_ai (
history ,
system_prompt ,
max_tokens =2048 ,
temperature =0.7 ,
top_p =0.9 ,
repeat_penalty =1.15 ,
stop =None 
):
    messages =[
    {
    "role":"system",
    "content":system_prompt 
    }
    ]
    messages .extend (history )

    response =llm .create_chat_completion (
    messages =messages ,
    max_tokens =max_tokens ,
    temperature =temperature ,
    top_p =top_p ,
    repeat_penalty =repeat_penalty ,
    stop =stop 
    )

=======
import os 

from llama_cpp import Llama 
from config import MODEL_PATH 


cpu_threads =max (1 ,min (8 ,os .cpu_count ()or 4 ))
llm =Llama (
model_path =MODEL_PATH ,
n_ctx =8192 ,
n_threads =cpu_threads ,
n_batch =256 ,
n_gpu_layers =0 ,
use_mmap =True ,
use_mlock =False ,
verbose =False ,
)


def ask_ai (
history ,
system_prompt ,
max_tokens =2048 ,
temperature =0.7 ,
top_p =0.9 ,
repeat_penalty =1.15 ,
stop =None 
):
    messages =[
    {
    "role":"system",
    "content":system_prompt 
    }
    ]
    messages .extend (history )

    response =llm .create_chat_completion (
    messages =messages ,
    max_tokens =max_tokens ,
    temperature =temperature ,
    top_p =top_p ,
    repeat_penalty =repeat_penalty ,
    stop =stop 
    )

>>>>>>> 6696ff70c425dd6f93af6c93d97bcaa324f38300
    return response ["choices"][0 ]["message"]["content"].strip ()