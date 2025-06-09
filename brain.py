# brain.py
import json
import re
from typing import Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING: # To avoid circular import for type hinting
    from google.generativeai.generative_models import ChatSession # type: ignore

def strip_wake_words(command: str) -> str:
    """Removes wake words from the command."""
    wake_words = ["codex", "hey codex", "okay codex", "jarvis", "praxis", "hey praxis", "okay praxis"]
    processed_command = command.lower()
    for wake in wake_words:
        if processed_command.startswith(wake):
            processed_command = processed_command[len(wake):].strip()
            break  # Remove only the first occurrence of a wake word phrase
    return processed_command.strip()

def extract_json(text: str) -> Optional[Dict[str, Any]]:
    """Extracts a JSON object from a string."""
    try:
        # Use a more robust regex to find json block
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except json.JSONDecodeError:
        # Consider logging this instead of printing, or in addition to printing
        print("Praxis Brain Warning: Failed to decode JSON from LLM response.")
        return None
    return None

def process_command_with_llm(command: str, chat_session: 'ChatSession') -> Optional[Dict[str, Any]]:
    """Uses the Gemini LLM to understand the user's command and returns a skill dictionary."""
    # The AI's persona name in the prompt, aligning with the project name "Praxis"
    prompt = f"""
        You are Praxis, a J.A.R.V.I.S.-like AI assistant.
        Analyze the user's latest request based on the conversation history.
        Your goal is to understand the user's intent and select the best tool (skill) to fulfill it.
        If a question requires multiple steps (e.g., searching the web, then searching within a specific page for details),
        you should plan these steps. After a tool provides information (like URLs from a web_search),
        you can use that information from the conversation history to inform a subsequent tool call (like search_within_url_content).

        Your available tools are:
        - get_time: Get the current time.
        - get_date: Get the current date.
        - web_search: Search the web. Requires a 'query' argument.
        - search_within_url_content: Fetches content from a given URL and answers a specific query based on that content. Requires 'url_to_search' (string) and 'search_query_within_url' (string, the user's question about the page content) arguments. Use this for follow-up questions about a URL provided by web_search.
        - recall_memory: Recall the recent conversation history. Takes no arguments.
        - set_reminder: Set a reminder. Requires a 'reminder_text' argument (string).
        - get_joke: Fetches a random joke. Optional 'category_and_params' argument (string, e.g., "Programming?safe-mode", default is "Any?safe-mode").
        - get_weather: Fetches current weather. Requires 'latitude' (string/float) and 'longitude' (string/float) arguments.
        - get_exchange_rate: Fetches exchange rates. Requires 'base_currency' (string, e.g., "USD") argument. Optional 'target_currency' (string, e.g., "EUR") argument.

        - get_calendar_current_date: Gets the current date for calendar context. Takes no arguments.
        - add_calendar_event: Adds an event to the calendar. Requires 'event_name' (string) and 'event_date' (string, 'YYYY-MM-DD'). Optional 'event_details' (string).
        - list_calendar_events: Lists events for a specific date. Requires 'event_date' (string, 'YYYY-MM-DD').
        - list_all_calendar_events: Lists all events in the calendar. Takes no arguments.
        - remove_calendar_event: Removes an event from the calendar. Requires 'event_name' (string) and 'event_date' (string, 'YYYY-MM-DD').
        - clear_all_calendar_events: Removes all events from the calendar. Takes no arguments.
        - summarize_creatively: Generates a creative summary for the provided text. Requires 'text_to_summarize' (string) argument.
        - echo_text: Echoes the provided text back. Requires 'text_to_echo' (string) argument.
        - get_text_stats: Provides basic statistics for given text. Requires 'text_for_stats' (string) argument.
        - analyze_log_summary: Generates a summary of log data. Requires 'log_entries' (list of dictionaries, e.g., [{{"level": "INFO", "message": "..."}}]).
        - analyze_data_complexity: Analyzes complexity of data. Requires 'data_items' (list of any type).
        - analyze_basic_statistics: Calculates basic stats for numbers. Requires 'numbers' (list of numbers).
        - analyze_advanced_statistics: Calculates advanced stats for numbers. Requires 'numbers' (list of numbers).
        - search_keywords_in_text: Searches for keywords in texts. Requires 'texts' (list of strings) and 'keywords' (list of strings).
        - match_regex_in_text: Matches a regex pattern in texts. Requires 'texts' (list of strings) and 'regex_pattern' (string).
        - analyze_correlation: Calculates correlation between two numerical series. Requires 'series_data' (dictionary of series name to list of numbers, e.g., {{"series_a": [1,2,3], "series_b": [2,4,6]}}).

        - list_directory_contents: Lists files and subdirectories in a specified directory. Requires 'path' (string) argument.
        - read_file_content: Reads the content of a specified file. Requires 'path' (string) argument.
        - write_content_to_file: Writes content to a specified file. Overwrites if file exists, creates if not. Requires 'path' (string) and 'content' (string) arguments.

        - get_github_repo_info: Fetches information about a GitHub repository. Requires 'repo_full_name' (string, e.g., "owner/repo_name") argument.
        - get_github_user_info: Fetches information about a GitHub user. Requires 'username' (string) argument.

        - calculate_add: Adds two numbers. Requires 'number1' (float) and 'number2' (float) arguments.
        - calculate_subtract: Subtracts the second number from the first. Requires 'number1' (float) and 'number2' (float) arguments.
        - calculate_multiply: Multiplies two numbers. Requires 'number1' (float) and 'number2' (float) arguments.
        - calculate_divide: Divides the first number by the second. Requires 'number1' (float) and 'number2' (float) arguments.
        - calculate_power: Raises a base to an exponent. Requires 'base' (float) and 'exponent' (float) arguments.
        - calculate_log: Calculates logarithm. Requires 'number' (float). Optional 'log_base' (float, defaults to natural log e).
        - calculate_sine: Calculates sine of an angle. Requires 'angle_degrees' (float) argument.
        - calculate_cosine: Calculates cosine of an angle. Requires 'angle_degrees' (float) argument.
 
        If the request is conversational (e.g., a greeting), respond with skill 'speak'.
        When using the 'speak' skill, provide the conversational response in the 'text' argument.

        Respond ONLY in a single, clean JSON format like:
        {{
            "skill": "web_search",
            "args": {{
                "query": "weather in London"
            }}
        }}
        Or for a conversational reply:
        {{
            "skill": "speak",
            "args": {{
                "text": "You're welcome, sir!"
            }}
        }}
        
        User's latest request: "{command}"

        JSON Response:
    """

    try:
        response = chat_session.send_message(prompt)
        return extract_json(response.text)
    except Exception as e:
        print(f"Praxis LLM Brain Error: {e}") # Consider logging this error as well
        return None
