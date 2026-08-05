<<<<<<< HEAD


import requests 
from bs4 import BeautifulSoup 
from ddgs import DDGS 


def search_web (query ,max_results =3 ):
    

    try :
        with DDGS ()as ddgs :
            results =list (
            ddgs .text (
            query ,
            max_results =max_results 
            )
            )

        return results 

    except Exception as e :
        print (f"[context_fetcher] DuckDuckGo search failed: {e}")
        return []


def fetch_page_text (url ,max_chars =5000 ,timeout =10 ):
    

    headers ={
    "User-Agent":(
    "Mozilla/5.0 "
    "(Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 "
    "Chrome/120.0 Safari/537.36"
    )
    }

    try :
        response =requests .get (
        url ,
        headers =headers ,
        timeout =timeout 
        )

        response .raise_for_status ()

        soup =BeautifulSoup (
        response .text ,
        "html.parser"
        )


        for element in soup ([
        "script",
        "style",
        "nav",
        "header",
        "footer",
        "aside",
        "form"
        ]):
            element .decompose ()

        text =soup .get_text (
        separator =" ",
        strip =True 
        )

        if not text :
            return None 

        return text [:max_chars ]

    except Exception as e :
        print (
        f"[context_fetcher] Failed to fetch page "
        f"{url}: {e}"
        )

        return None 


def get_context_for_topic (topic ,max_chars =3000 ):
    

    print (
    f"[context_fetcher] Searching DuckDuckGo "
    f"for: {topic}"
    )

    results =search_web (
    topic ,
    max_results =3 
    )

    if not results :
        return None ,None 


    for result in results :

        title =result .get (
        "title",
        "Web Source"
        )

        url =result .get (
        "href"
        )

        if not url :
            continue 

        print (
        f"[context_fetcher] Reading: {title}"
        )

        text =fetch_page_text (
        url ,
        max_chars =max_chars 
        )

        if text and len (text )>200 :


            trimmed =text [:max_chars ]

            last_period =trimmed .rfind (".")

            if last_period >max_chars *0.6 :
                trimmed =trimmed [
                :last_period +1 
                ]

            return trimmed ,title 

    return None ,None 


if __name__ =="__main__":

    context ,source =get_context_for_topic (
    "Mauryan Empire"
    )

    if context :

        print (
        f"\nSource: {source}\n"
        )

        print (
        context [:1000 ],
        "..."
        )

    else :

        print (
        "No context found."
=======


import requests 
from bs4 import BeautifulSoup 
from ddgs import DDGS 


def search_web (query ,max_results =3 ):
    

    try :
        with DDGS ()as ddgs :
            results =list (
            ddgs .text (
            query ,
            max_results =max_results 
            )
            )

        return results 

    except Exception as e :
        print (f"[context_fetcher] DuckDuckGo search failed: {e}")
        return []


def fetch_page_text (url ,max_chars =5000 ,timeout =10 ):
    

    headers ={
    "User-Agent":(
    "Mozilla/5.0 "
    "(Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 "
    "Chrome/120.0 Safari/537.36"
    )
    }

    try :
        response =requests .get (
        url ,
        headers =headers ,
        timeout =timeout 
        )

        response .raise_for_status ()

        soup =BeautifulSoup (
        response .text ,
        "html.parser"
        )


        for element in soup ([
        "script",
        "style",
        "nav",
        "header",
        "footer",
        "aside",
        "form"
        ]):
            element .decompose ()

        text =soup .get_text (
        separator =" ",
        strip =True 
        )

        if not text :
            return None 

        return text [:max_chars ]

    except Exception as e :
        print (
        f"[context_fetcher] Failed to fetch page "
        f"{url}: {e}"
        )

        return None 


def get_context_for_topic (topic ,max_chars =3000 ):
    

    print (
    f"[context_fetcher] Searching DuckDuckGo "
    f"for: {topic}"
    )

    results =search_web (
    topic ,
    max_results =3 
    )

    if not results :
        return None ,None 


    for result in results :

        title =result .get (
        "title",
        "Web Source"
        )

        url =result .get (
        "href"
        )

        if not url :
            continue 

        print (
        f"[context_fetcher] Reading: {title}"
        )

        text =fetch_page_text (
        url ,
        max_chars =max_chars 
        )

        if text and len (text )>200 :


            trimmed =text [:max_chars ]

            last_period =trimmed .rfind (".")

            if last_period >max_chars *0.6 :
                trimmed =trimmed [
                :last_period +1 
                ]

            return trimmed ,title 

    return None ,None 


if __name__ =="__main__":

    context ,source =get_context_for_topic (
    "Mauryan Empire"
    )

    if context :

        print (
        f"\nSource: {source}\n"
        )

        print (
        context [:1000 ],
        "..."
        )

    else :

        print (
        "No context found."
>>>>>>> 6696ff70c425dd6f93af6c93d97bcaa324f38300
        )