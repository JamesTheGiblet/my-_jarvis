# skills/calendar.py
import datetime
import json
import logging
from typing import Dict, List, Optional # Added List and Optional

# In-module storage for calendar events.
# Note: This data will be lost if the assistant restarts.
# For persistence, consider file storage (JSON, CSV) or a simple database.
_calendar_data: Dict[str, List[Dict[str, str]]] = {}

def _get_current_date() -> str:
    """Returns the current date as a string in YYYY-MM-DD format."""
    return datetime.date.today().isoformat()

def _is_valid_date(date_str: str) -> bool:
    """Check if the date string is a valid YYYY-MM-DD date."""
    try:
        datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def get_calendar_current_date(context):
    """Gets and speaks the current date."""
    current_date = _get_current_date()
    context.speak(f"Sir, today's date is {current_date}.")

def add_calendar_event(context, event_name: str, event_date: str, event_details: Optional[str] = None):
    """
    Adds an event to the calendar for a specific date.
    Args:
        context: The skill context.
        event_name (str): The name of the event.
        event_date (str): The date of the event in YYYY-MM-DD format.
        event_details (Optional[str]): Optional details for the event.
    """
    if not _is_valid_date(event_date):
        context.speak(f"I'm sorry, sir, but '{event_date}' is not a valid date format. Please use YYYY-MM-DD.")
        return

    date_events = _calendar_data.setdefault(event_date, [])
    
    for event in date_events:
        if event.get("name") == event_name:
            context.speak(f"Sir, an event named '{event_name}' already exists on {event_date}.")
            return
            
    new_event = {"name": event_name, "details": event_details if event_details else "No details provided"}
    date_events.append(new_event)
    _calendar_data[event_date] = date_events # Ensure update if setdefault created a new list
    context.speak(f"Very good, sir. I've scheduled '{event_name}' for {event_date}.")
    logging.info(f"Calendar event added: {event_name} on {event_date} with details: {new_event['details']}")

def list_calendar_events(context, event_date: str):
    """
    Lists all events scheduled for a specific date.
    Args:
        context: The skill context.
        event_date (str): The date to list events for, in YYYY-MM-DD format.
    """
    if not _is_valid_date(event_date):
        context.speak(f"Apologies, sir, but '{event_date}' is not a valid date format. Please use YYYY-MM-DD.")
        return

    events_on_date = _calendar_data.get(event_date, [])
    if not events_on_date:
        context.speak(f"Sir, there are no events scheduled for {event_date}.")
    else:
        context.speak(f"For {event_date}, you have the following events scheduled:")
        for i, event in enumerate(events_on_date):
            context.speak(f"{i+1}. {event.get('name')} (Details: {event.get('details', 'N/A')})")

def list_all_calendar_events(context):
    """Lists all scheduled events, grouped by date."""
    if not _calendar_data:
        context.speak("Sir, your calendar is currently empty.")
        return

    context.speak("Here are all the events in your calendar, sir:")
    sorted_dates = sorted(_calendar_data.keys())
    for date in sorted_dates:
        events_on_date = _calendar_data[date]
        if events_on_date: # Should always be true if date is a key, but good practice
            context.speak(f"On {date}:")
            for i, event in enumerate(events_on_date):
                context.speak(f"  {i+1}. {event.get('name')} (Details: {event.get('details', 'N/A')})")

def remove_calendar_event(context, event_name: str, event_date: str):
    """
    Removes a specific event from a given date.
    Args:
        context: The skill context.
        event_name (str): The name of the event to remove.
        event_date (str): The date of the event in YYYY-MM-DD format.
    """
    if not _is_valid_date(event_date):
        context.speak(f"I'm unable to process that date, sir. '{event_date}' is not valid. Please use YYYY-MM-DD.")
        return

    if event_date not in _calendar_data:
        context.speak(f"Sir, I could not find any events scheduled for {event_date} to remove '{event_name}'.")
        return

    date_events = _calendar_data[event_date]
    original_length = len(date_events)
    
    # Filter out the event to remove
    _calendar_data[event_date] = [event for event in date_events if event.get("name") != event_name]
    
    if len(_calendar_data[event_date]) < original_length:
        context.speak(f"Understood, sir. I have removed '{event_name}' from your calendar on {event_date}.")
        logging.info(f"Calendar event removed: {event_name} from {event_date}")
        # If the date now has no events, remove the date key itself
        if not _calendar_data[event_date]:
            del _calendar_data[event_date]
    else:
        context.speak(f"Sir, I could not find an event named '{event_name}' on {event_date} to remove.")

def clear_all_calendar_events(context):
    """Removes all events from the calendar."""
    global _calendar_data
    if not _calendar_data:
        context.speak("Sir, your calendar is already empty.")
        return
    
    # Confirmation step might be good here for a real application
    # For now, we'll proceed directly.
    _calendar_data.clear()
    context.speak("As you wish, sir. I have cleared all events from your calendar.")
    logging.info("All calendar events cleared.")

# Example of how you might want to load/save for persistence (not implemented in speak calls)
def _save_calendar_to_file(filepath="calendar_data.json"):
    try:
        with open(filepath, 'w') as f:
            json.dump(_calendar_data, f, indent=4)
        logging.info(f"Calendar data saved to {filepath}")
    except IOError as e:
        logging.error(f"Could not save calendar data to {filepath}: {e}")

def _load_calendar_from_file(filepath="calendar_data.json"):
    global _calendar_data
    try:
        with open(filepath, 'r') as f:
            _calendar_data = json.load(f)
        logging.info(f"Calendar data loaded from {filepath}")
    except FileNotFoundError:
        logging.info(f"Calendar data file {filepath} not found. Starting with an empty calendar.")
        _calendar_data = {}
    except (IOError, json.JSONDecodeError) as e:
        logging.error(f"Could not load calendar data from {filepath}: {e}. Starting with an empty calendar.")
        _calendar_data = {}

# To automatically load at startup, you could call _load_calendar_from_file() here.
# However, skills are typically stateless and main.py handles initialization.
# For now, it remains an in-memory dictionary.
# _load_calendar_from_file() # Example: uncomment to load on module import

def _test_skill(context):
    """
    Runs a quick self-test for the calendar module.
    It adds an event, lists it, removes it, and clears the calendar.
    """
    logging.info("[calendar_test] Running self-test for calendar module...")
    try:
        test_date = _get_current_date() # Use today's date for the test
        test_event_name = "Automated Test Event"
        test_event_details = "This is a temporary event for testing purposes."

        # Ensure calendar is clean before starting specific tests
        logging.info(f"[calendar_test] Clearing calendar before test operations.")
        clear_all_calendar_events(context)

        # Test 1: Add an event
        logging.info(f"[calendar_test] Attempting to add event: '{test_event_name}' on {test_date}")
        add_calendar_event(context, test_event_name, test_date, test_event_details)
        logging.info(f"[calendar_test] add_calendar_event called.")

        # Test 2: List events for the date (should include the test event)
        logging.info(f"[calendar_test] Attempting to list events for {test_date}")
        list_calendar_events(context, test_date)
        logging.info(f"[calendar_test] list_calendar_events called.")

        # Test 3: Remove the event
        logging.info(f"[calendar_test] Attempting to remove event: '{test_event_name}' from {test_date}")
        remove_calendar_event(context, test_event_name, test_date)
        logging.info(f"[calendar_test] remove_calendar_event called.")

        # Test 4: Clear all events (to ensure cleanup)
        logging.info(f"[calendar_test] Attempting to clear all calendar events.")
        clear_all_calendar_events(context)
        logging.info(f"[calendar_test] clear_all_calendar_events called.")

        logging.info("[calendar_test] All calendar self-tests passed successfully.")
    except Exception as e:
        logging.error(f"[calendar_test] Self-test FAILED: {e}", exc_info=True)
        raise # Re-raise the exception to be caught by load_skills in main.py