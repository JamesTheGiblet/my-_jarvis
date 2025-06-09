# skills/advanced_web_research.py
import logging
from typing import Any, Dict, Optional

# For perform_web_search
from googlesearch import search

# For search_content_in_specific_url
import requests
from bs4 import BeautifulSoup
import re


def perform_web_search(context, query: str =""):
    """
    Performs a general web search and speaks the top 3 results (URLs).
    Args:
        context: The skill context.
        query (str): The search query.
    """
    if not query:
        context.speak("Of course, what would you like me to search for?")
        return
    context.speak(f"Right away. Searching the web for '{query}'...")
    try:
        all_results = list(search(query)) # Removed tld and other unsupported args
        results = all_results[:3]

        if results:
            context.speak("Here are the top results I found, sir:")
            for url in results:
                try:
                    # Fetch page title
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }
                    page_response = requests.get(url, headers=headers, timeout=5)
                    page_response.raise_for_status()
                    soup = BeautifulSoup(page_response.text, 'html.parser')
                    title = soup.title.string.strip() if soup.title and soup.title.string else "No title found"
                    
                    # TTS will only say the title (or a message about it)
                    text_for_tts = f"Title: {title}"
                    # Console log (and thus LLM history) will contain both title and URL
                    text_for_log = f"Title: {title} - URL: {url}"
                    context.speak(text_to_speak=text_for_tts, text_to_log=text_for_log)

                except requests.exceptions.RequestException as req_e:
                    logging.warning(f"Could not fetch title for {url}: {req_e}")
                    context.speak(text_to_speak=f"Could not fetch title for one of the results.", text_to_log=f"URL: {url} (Could not fetch title: {req_e})")
                except Exception as e_title:
                    logging.warning(f"Error processing title for {url}: {e_title}")
                    context.speak(text_to_speak="Error fetching title for one of the results.", text_to_log=f"URL: {url} (Error fetching title: {e_title})")
        else:
            context.speak(f"I couldn't find any results for '{query}'.")
    except Exception as e:
        context.speak("I'm sorry, sir. I encountered an error during the web search.")
        logging.error(f"Error in perform_web_search for query '{query}': {e}", exc_info=True)
        # It's good to also print the error to console if context.speak might fail or for immediate visibility
        print(f"Error details (perform_web_search): {e}")


def _fetch_and_search_page_content(url: str, search_query: str) -> Dict[str, Any]:
    """ 
    Helper: Fetches content from a URL, parses it, and searches for a query, returning snippets.
    """
    SNIPPET_RADIUS = 70 # Number of characters before and after the found term for the snippet
    logging.debug(f"Attempting to scrape URL: {url} and search for: '{search_query}'")
    findings = []
    content_preview = "Could not fetch content."
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        for script_or_style in soup(["script", "style"]):
            script_or_style.decompose()
        page_text = soup.body.get_text(separator=' ', strip=True) if soup.body else ""
        content_preview = page_text[:500] + "..." if page_text else "No text content found in body."

        if not page_text:
            findings.append(f"No visible text content was extracted from {url}.")
        else:
            matches_found = 0
            for match in re.finditer(re.escape(search_query), page_text, re.IGNORECASE):
                matches_found += 1
                start, end = match.span()
                snippet_start = max(0, start - SNIPPET_RADIUS)
                snippet_end = min(len(page_text), end + SNIPPET_RADIUS)
                prefix = "..." if snippet_start > 0 else ""
                suffix = "..." if snippet_end < len(page_text) else ""
                snippet = page_text[snippet_start:snippet_end]
                findings.append(f"Snippet {matches_found}: {prefix}{snippet}{suffix}")
            
            if matches_found > 0:
                findings.insert(0, f"The term '{search_query}' was found {matches_found} time(s) in the content of {url}.")
            else:
                findings.append(f"The term '{search_query}' was NOT found in the content of {url}.")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching {url}: {e}")
        findings.append(f"Error: Could not fetch content from {url}. {str(e)}")
    except Exception as e:
        logging.error(f"Unexpected error during scraping or searching {url}: {e}", exc_info=True)
        findings.append(f"Error: An unexpected error occurred while processing {url}.")
        
    return {"url": url, "search_query": search_query, "findings": findings, "content_preview": content_preview}

def search_content_in_specific_url(context, url: str, search_query: str):
    """
    Fetches content from a given URL and searches for a specific query within that content.
    """
    if not url or not search_query:
        context.speak("Sir, please provide both a URL and a search query for me to look into.")
        return

    context.speak(f"Attempting to fetch content from {url} and search for '{search_query}'...")
    try:
        result = _fetch_and_search_page_content(url, search_query)
        context.speak(f"Regarding your search for '{result['search_query']}' within {result['url']}:")
        for finding in result.get("findings", ["No specific findings."]):
            context.speak(f"- {finding}")
        logging.info(f"Searched within URL '{url}' for '{search_query}'. Findings: {result.get('findings')}")
    except Exception as e:
        context.speak(f"I'm sorry, sir. An error occurred while trying to process {url}: {str(e)}")
        logging.error(f"Error in search_content_in_specific_url for '{url}', query '{search_query}': {e}", exc_info=True)