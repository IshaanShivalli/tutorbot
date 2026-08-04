"""
Fetches real reference material for a given topic using DuckDuckGo Search.

The quiz generator uses this context to create questions based on
actual web search results instead of relying only on the small model's
factual recall.
"""

import requests
from bs4 import BeautifulSoup
from ddgs import DDGS


def search_web(query, max_results=3):
    """
    Searches the web using DuckDuckGo.

    Returns:
        List of search result dictionaries.
    """

    try:
        with DDGS() as ddgs:
            results = list(
                ddgs.text(
                    query,
                    max_results=max_results
                )
            )

        return results

    except Exception as e:
        print(f"[context_fetcher] DuckDuckGo search failed: {e}")
        return []


def fetch_page_text(url, max_chars=5000, timeout=10):
    """
    Downloads a webpage and extracts readable text from it.
    """

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "Chrome/120.0 Safari/537.36"
        )
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=timeout
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # Remove elements that usually contain no useful article text
        for element in soup([
            "script",
            "style",
            "nav",
            "header",
            "footer",
            "aside",
            "form"
        ]):
            element.decompose()

        text = soup.get_text(
            separator=" ",
            strip=True
        )

        if not text:
            return None

        return text[:max_chars]

    except Exception as e:
        print(
            f"[context_fetcher] Failed to fetch page "
            f"{url}: {e}"
        )

        return None


def get_context_for_topic(topic, max_chars=3000):
    """
    Searches the web for a topic and returns useful reference context.

    Returns:
        (context_text, source_title)

        context_text:
            Extracted text from a relevant webpage.

        source_title:
            Title of the source page.
    """

    print(
        f"[context_fetcher] Searching DuckDuckGo "
        f"for: {topic}"
    )

    results = search_web(
        topic,
        max_results=3
    )

    if not results:
        return None, None

    # Try the search results one by one
    for result in results:

        title = result.get(
            "title",
            "Web Source"
        )

        url = result.get(
            "href"
        )

        if not url:
            continue

        print(
            f"[context_fetcher] Reading: {title}"
        )

        text = fetch_page_text(
            url,
            max_chars=max_chars
        )

        if text and len(text) > 200:

            # Avoid cutting off mid-sentence
            trimmed = text[:max_chars]

            last_period = trimmed.rfind(".")

            if last_period > max_chars * 0.6:
                trimmed = trimmed[
                    :last_period + 1
                ]

            return trimmed, title

    return None, None


if __name__ == "__main__":

    context, source = get_context_for_topic(
        "Mauryan Empire"
    )

    if context:

        print(
            f"\nSource: {source}\n"
        )

        print(
            context[:1000],
            "..."
        )

    else:

        print(
            "No context found."
        )