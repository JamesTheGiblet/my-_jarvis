# c:\Users\gilbe\Desktop\my _jarvis\skills\api_connector.py
import requests
import json
import time
import logging # Use standard logging from your main.py setup
from typing import Dict, Any, Tuple, Optional

# --- Adapted Helper function from api_connector.py ---
MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 1

def _fetch_from_api(url: str, params: Dict = None, headers: Dict = None) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Fetches data from a given API URL with retry logic.
    Returns (json_response, error_message).
    """
    default_headers = {
        'User-Agent': 'CodexMK5/1.0' # Your assistant's User-Agent
    }
    if headers:
        default_headers.update(headers)

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.get(url, params=params, headers=default_headers, timeout=10)
            logging.debug(f"[_fetch_from_api] URL: {url}, Attempt: {attempt + 1}, Status: {response.status_code}")
            
            if response.status_code == 429: # Too Many Requests
                error_message = f"API rate limit hit for '{url}'. Status: {response.status_code}."
                if attempt < MAX_RETRIES:
                    retry_after = int(response.headers.get("Retry-After", RETRY_DELAY_SECONDS * (attempt + 2)))
                    logging.info(f"Rate limit hit for {url}. Retrying after {retry_after} seconds.")
                    time.sleep(retry_after)
                    continue
                else:
                    logging.error(error_message + " Exhausted retries.")
                    return None, error_message
            
            response.raise_for_status() # Raises HTTPError for bad responses (4XX or 5XX)
            # Attempt to parse JSON only if status is OK and content is expected
            if response.status_code == 200 and response.content:
                return response.json(), None
            elif response.status_code == 200 and not response.content: # OK but empty response
                logging.warning(f"API returned 200 OK but with empty content from '{url}'.")
                return None, f"The API at '{url.split('/')[-2]}' provided an empty response."
            # For other non-error status codes that might not have JSON, handle as appropriate or let raise_for_status catch it.
            return None, f"Received an unexpected response status ({response.status_code}) from '{url}'."
        except json.JSONDecodeError as e:
            response_text_preview = "N/A (response object not available or text attribute missing)"
            if 'response' in locals() and hasattr(response, 'text'):
                response_text_preview = response.text[:200] # Log a preview of the non-JSON response
            logging.error(f"Failed to decode JSON response from '{url}': {str(e)}. Response text preview: {response_text_preview}")
            return None, f"The API at '{url.split('/')[-2]}' returned data in an unexpected format."
        except requests.exceptions.RequestException as e: # Catches other network errors, timeouts, HTTP errors etc.
            error_message = f"API request error for '{url}' (attempt {attempt + 1}/{MAX_RETRIES + 1}): {str(e)}"
            if attempt < MAX_RETRIES:
                logging.warning(error_message + " Retrying...")
                time.sleep(RETRY_DELAY_SECONDS * (attempt + 1)) # Simple incremental backoff
            else:
                logging.error(error_message + " Exhausted retries.")
                return None, error_message
    # Fallback, though theoretically unreachable if loop logic is complete for all attempts.
    return None, f"An unexpected error occurred after all retries for API request to '{url}'."

# --- New Skill Functions ---

def get_joke(context, category_and_params: str = "Any?safe-mode"):
    """
    Fetches a random joke.
    Args:
        context: The skill context.
        category_and_params (str): Category and parameters for the joke API 
                                   (e.g., 'Any?safe-mode', 'Programming', 'Christmas?type=single'). Defaults to "Any?safe-mode".
    """
    joke_api_url_base = "https://v2.jokeapi.dev/joke/"
    # Use default if empty string is passed, ensure no leading slash
    effective_cat_params = category_and_params.lstrip('/') if category_and_params else "Any?safe-mode"
    full_joke_api_url = joke_api_url_base + effective_cat_params
    
    context.speak(f"Certainly, sir. Looking for a {effective_cat_params.split('?')[0].replace('_', ' ')} joke...")
    data, error = _fetch_from_api(full_joke_api_url)
    
    if error:
        context.speak(f"I'm sorry, sir. I couldn't fetch a joke at the moment. {error}")
        return False
    elif data:
        if data.get("error"): # JokeAPI can return error:true in a 200 OK response
             context.speak(f"It seems there was an issue with the joke service: {data.get('message', 'Unknown joke API error')}")
             logging.warning(f"JokeAPI returned error: {data}")
             return False
        elif data.get("type") == "single":
            context.speak(data.get("joke", "I found a joke, but it seems to have vanished!"))
            return True
        elif data.get("type") == "twopart":
            context.speak(data.get("setup", "I have a joke for you..."))
            context.speak(data.get("delivery", "...but I forgot the punchline!")) # pyttsx3 will queue these
            return True
        else:
            context.speak("I received something, but it's not the joke format I was expecting, sir.")
            logging.warning(f"Unexpected joke format from API: {data}")
            return False
    else:
        context.speak("My apologies, I couldn't find a joke right now.")
        return False

def get_weather(context, latitude: str, longitude: str):
    """
    Fetches current weather for a given latitude and longitude.
    Args:
        context: The skill context.
        latitude (str): The latitude.
        longitude (str): The longitude.
    """
    try:
        float(latitude) # Basic validation
        float(longitude)
    except ValueError:
        context.speak("Sir, please provide valid numerical values for latitude and longitude.")
        return

    weather_api_url = "https://api.open-meteo.com/v1/forecast"
    params = {"latitude": latitude, "longitude": longitude, "current_weather": "true"}
    
    context.speak(f"One moment, sir. Fetching current weather for coordinates {latitude}, {longitude}...")
    data, error = _fetch_from_api(weather_api_url, params=params)
    
    if error:
        context.speak(f"I regret to inform you that I couldn't fetch the weather data. {error}")
    elif data and "current_weather" in data:
        weather = data["current_weather"]
        temp = weather.get("temperature")
        windspeed = weather.get("windspeed")
        units = data.get("current_weather_units", {})
        temp_unit = units.get("temperature", "°C")
        wind_unit = units.get("windspeed", "km/h")
        context.speak(f"The current temperature is {temp}{temp_unit}, with wind speeds around {windspeed} {wind_unit}.")
    else:
        context.speak("I'm sorry, sir, I was unable to retrieve the current weather details.")
        logging.warning(f"Unexpected weather data format or missing current_weather: {data}")

def get_exchange_rate(context, base_currency: str, target_currency: str = None):
    """
    Fetches exchange rates for a base currency, optionally against a target currency.
    """
    base_currency_upper = base_currency.upper()
    target_currency_upper = target_currency.upper() if target_currency else None
    exchange_api_url = f"https://api.exchangerate-api.com/v4/latest/{base_currency_upper}"
    
    context.speak(f"Certainly, sir. Fetching exchange rates for {base_currency_upper}...")
    data, error = _fetch_from_api(exchange_api_url)
    
    if error:
        context.speak(f"My apologies, I couldn't fetch the exchange rates. {error}")
    elif data and "rates" in data:
        rates = data["rates"]
        if target_currency_upper and target_currency_upper in rates:
            context.speak(f"1 {base_currency_upper} is equal to {rates[target_currency_upper]} {target_currency_upper}.")
        elif target_currency_upper: # Target specified but not found
            context.speak(f"Sorry, I couldn't find an exchange rate for {target_currency_upper}.")
        else: # No target, give a summary
            context.speak(f"For {base_currency_upper}: 1 unit is {rates.get('USD', 'N/A')} USD, {rates.get('EUR', 'N/A')} EUR, or {rates.get('GBP', 'N/A')} GBP.")
    else:
        context.speak("I'm sorry, sir, I was unable to retrieve the exchange rate data.")
        logging.warning(f"Unexpected exchange rate data or missing 'rates': {data}")
        
def _test_skill(context):
    """
    Runs a quick self-test for the api_interaction_skills module.
    It attempts to fetch a joke to ensure basic API connectivity and skill logic.
    """
    logging.info("[api_interaction_test] Running self-test for api_interaction_skills module...")
    try:
        # Test 1: Call get_joke with default parameters.
        # This will be muted by the SkillContext during testing.
        # The purpose is to see if it executes without raising an unhandled exception.
        logging.info("[api_interaction_test] Attempting to call get_joke skill...")
        get_joke(context) # Uses default "Any?safe-mode"
        # If get_joke itself logs errors (e.g., API down), those will appear in the log.
        # The test passes if get_joke completes without throwing an exception that _test_skill doesn't handle.
        
        # If get_joke were to use context.speak for its normal output,
        # those would be logged as "Muted Speak (from skill test): ..."

        logging.info("[api_interaction_test] get_joke skill call completed (check logs for API interaction details).")
        logging.info("[api_interaction_test] All api_interaction_skills self-tests passed successfully.")
    except Exception as e:
        logging.error(f"[api_interaction_test] Self-test FAILED: {e}", exc_info=True)
        raise # Re-raise the exception to be caught by load_skills in main.py