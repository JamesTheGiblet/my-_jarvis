# c:\Users\gilbe\Desktop\my _jarvis\skills\core_skills.py
import datetime
import logging # Import standard logging
# This import is necessary for the web_search function.
# It's better to have it at the top of the file.
from googlesearch import search
# Added imports for fetching and parsing web page content
import requests
from bs4 import BeautifulSoup

def get_time(context): # Accepts context
    """Returns the current time."""
    time_str = datetime.datetime.now().strftime("%I:%M %p")
    context.speak(f"Sir, the current time is {time_str}") # Uses context.speak

def get_date(context): # Accepts context
    """Returns the current date."""
    date_str = datetime.datetime.now().strftime("%B %d, %Y")
    context.speak(f"Today's date is {date_str}") # Uses context.speak

def web_search(context, query=""): # Accepts context
    """
    Performs a web search, speaks the title and a relevant snippet from the top result,
    and displays their URLs.
    """
    if not query:
        context.speak("Of course, what would you like me to search for?")
        return
    context.speak(f"Right away. Searching the web for '{query}'...")
    try:
        all_results = list(search(query))
        results = all_results[:1] # Process only the top 1 result

        if results:
            context.speak("Here is the top result I found:")
            for url in results:
                try:
                    # Fetch page content with a user-agent and timeout
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 CodexAssistant/1.0'}
                    page_response = requests.get(url, headers=headers, timeout=10)
                    page_response.raise_for_status() # Raise an exception for bad status codes

                    # Parse HTML and extract title
                    soup = BeautifulSoup(page_response.content, 'html.parser')
                    page_title_tag = soup.find('title')
                    page_title = page_title_tag.string.strip() if page_title_tag and page_title_tag.string else "No title found"

                    # Extract text content for snippet generation
                    extracted_text = soup.get_text(separator=' ', strip=True)
                    snippet = "Snippet not available." # Default snippet

                    if extracted_text.strip():
                        # Limit text sent to LLM for snippet generation (shorter than full page analysis)
                        max_chars_for_snippet = 7000 # Approx 1.5k-2k tokens
                        truncated_text_for_snippet = extracted_text[:max_chars_for_snippet]

                        # Modified prompt to explicitly ask for plain text and not JSON/skill
                        snippet_prompt = (
                            f"You are an assistant tasked with extracting a concise answer snippet from text. "
                            f"Based SOLELY on the following text extracted from the webpage [{url}], "
                            f"provide a very concise plain text answer (1-2 sentences, max 50 words) to the question: '{query}'. "
                            "If the answer is not clearly present in this excerpt, state 'Information not readily found in the summary.' "
                            f"Do not use any prior knowledge. Do NOT format your response as JSON. Do NOT suggest a skill. Just provide the plain text answer or the 'not found' message. Extracted text:\n---\n{truncated_text_for_snippet}\n---\nPlain text answer:"
                        )
                        try:
                            llm_snippet_response = context.chat_session.send_message(snippet_prompt)
                            snippet_text = llm_snippet_response.text.strip()
                            if snippet_text:
                                snippet = snippet_text
                        except Exception as llm_e:
                            logging.warning(f"LLM error during snippet generation for {url}: {llm_e}")
                            snippet = "Could not generate snippet due to an error."

                    # Speak the title and the generated snippet
                    context.speak(f"Title: {page_title}. Snippet: {snippet}")
                    # Display the URL in the console (without TTS)
                    print(f"Codex: URL: {url}")

                except requests.exceptions.RequestException as req_e:
                    logging.warning(f"Could not fetch content from {url}. Error: {req_e}")
                    context.speak(f"I was unable to fetch the title for one of the results.")
                    print(f"Codex: URL: {url} (fetch error)") # Still display URL
                except Exception as e_parse:
                    logging.warning(f"Error processing content from {url}: {e_parse}")
                    context.speak(f"I encountered an issue processing one of the results.")
                    print(f"Codex: URL: {url} (processing error)") # Still display URL
        else:
            context.speak("I couldn't find any results for that query.")
    except Exception as e:
        logging.error(f"Web search error for query '{query}': {e}", exc_info=True)
        context.speak(f"I'm sorry, sir. I encountered an error during the web search: {e}")


def search_within_url_content(context, url_to_search: str, search_query_within_url: str):
    """
    Fetches content from a given URL and uses the LLM to answer a specific query based on that content.
    """
    if not url_to_search or not search_query_within_url:
        context.speak("Sir, I need both a URL and a specific question to search within its content.")
        return

    context.speak(f"Understood. I will search for '{search_query_within_url}' within the content of {url_to_search}.")
    logging.info(f"[search_within_url_content] Attempting to search '{search_query_within_url}' in URL: {url_to_search}")

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 CodexAssistant/1.0'}
        page_response = requests.get(url_to_search, headers=headers, timeout=15)
        page_response.raise_for_status()

        soup = BeautifulSoup(page_response.content, 'html.parser')
        
        # Extract text content - this can be further refined
        # For now, get_text() is a broad approach.
        extracted_text = soup.get_text(separator=' ', strip=True)

        if not extracted_text.strip():
            context.speak(f"I was able to fetch the page from {url_to_search}, but I couldn't find any text content to analyze.")
            logging.warning(f"[search_within_url_content] No text content extracted from {url_to_search}")
            return

        # Limit the amount of text sent to the LLM to avoid exceeding token limits
        max_chars_for_llm = 15000 # Approx 3k-4k tokens, adjust as needed
        truncated_text = extracted_text[:max_chars_for_llm]
        if len(extracted_text) > max_chars_for_llm:
            logging.info(f"[search_within_url_content] Truncated text from {len(extracted_text)} to {max_chars_for_llm} chars for LLM.")

        context.speak("Analyzing the content. This might take a moment...")

        # Construct a prompt for the LLM to answer the question based on the extracted text
        qa_prompt = (
            f"Based SOLELY on the following text extracted from the webpage [{url_to_search}], "
            f"please answer the question: '{search_query_within_url}'. "
            "If the answer is not found in the text, please state that the information is not available in the provided content. "
            f"Do not use any prior knowledge. Extracted text:\n---\n{truncated_text}\n---"
        )
        
        llm_response = context.chat_session.send_message(qa_prompt)
        answer = llm_response.text.strip()
        context.speak(answer)
        logging.info(f"[search_within_url_content] LLM answer for '{search_query_within_url}' from {url_to_search}: {answer}")

    except requests.exceptions.RequestException as req_e:
        logging.error(f"[search_within_url_content] Could not fetch content from {url_to_search}. Error: {req_e}", exc_info=True)
        context.speak(f"I'm sorry, sir. I was unable to fetch the content from {url_to_search}. Error: {req_e}")
    except Exception as e:
        logging.error(f"[search_within_url_content] Error processing content from {url_to_search} for query '{search_query_within_url}': {e}", exc_info=True)
        context.speak(f"I encountered an unexpected issue while trying to find the answer within {url_to_search}.")


def recall_memory(context): # Accepts context
    """Summarizes recent conversation memory (last 5 messages)."""
    if not context.chat_session.history:
        context.speak("No memory data found.")
        return
    recent_history = context.chat_session.history[-5:] # Get last 5 interactions

    # Filter out the initial system prompt if it's part of the history structure
    # and only show user and model parts.
    # This depends on how genai structures history.
    # Assuming msg.role and msg.parts[0].text are valid.

    formatted_history = []
    for msg in recent_history:
        # Ensure msg has 'role' and 'parts' and parts is not empty
        if hasattr(msg, 'role') and hasattr(msg, 'parts') and msg.parts:
            # Avoid printing the long system prompt if it's stored as a 'user' role initially
            # or if it's a specific system message.
            # This part might need adjustment based on actual history content.
            if "You are Codex, a J.A.R.V.I.S.-like AI assistant." in msg.parts[0].text and msg.role == 'user':
                continue # Skip the initial system prompt if it's part of the user messages

            role_display = "You" if msg.role == "user" else "Codex"
            formatted_history.append(f"{role_display}: {msg.parts[0].text}")

    if not formatted_history:
        context.speak("No recent conversational turns to recall.")
        return

    context.speak("Here's a brief memory recall:")
    for entry in formatted_history:
        context.speak(entry) # Speak each line for better TTS flow
        print(entry) # Also print for console log
