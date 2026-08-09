import requests
from bs4 import BeautifulSoup
from ddgs import DDGS


def search_web(query, max_results=3):

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

        response.encoding = response.apparent_encoding

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # Strip non-content elements, including footnote markers and tables
        for element in soup([
            "script",
            "style",
            "nav",
            "header",
            "footer",
            "aside",
            "form",
            "sup",
            "table"
        ]):
            element.decompose()

        # Remove common "not part of the article" boxes by class/id
        junk_selectors = [
            {"class": "infobox"},
            {"class": "navbox"},
            {"class": "hatnote"},
            {"class": "ambox"},
            {"class": "mw-editsection"},
            {"class": "vector-page-toolbar"},
            {"class": "vector-header"},
            {"id": "mw-page-base"},
            {"id": "mw-head-base"},
        ]
        for sel in junk_selectors:
            for element in soup.find_all(attrs=sel):
                element.decompose()

        # Prefer the real article body if we can find one
        main_content = (
            soup.find("div", id="mw-content-text")   # Wikipedia
            or soup.find("article")                  # most news/blog sites
            or soup.find("main")
            or soup.find("body")
        )

        if not main_content:
            return None

        text = main_content.get_text(separator=" ", strip=True)

        # Collapse repeated whitespace left behind by stripped tags
        text = " ".join(text.split())

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

            trimmed = text[:max_chars]

            last_period = trimmed.rfind(".")

            if last_period > max_chars * 0.6:
                trimmed = trimmed[:last_period + 1]
            else:
                last_space = trimmed.rfind(" ")
                if last_space > 0:
                    trimmed = trimmed[:last_space].rstrip() + "..."

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