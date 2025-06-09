# skills/calendar.py
import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

# --- Calendar Data Store ---
# This will hold the calendar events in memory.
# Structure: {"YYYY-MM-DD": [{"name": "Event Name", "details": "Optional Details"}, ...]}
CALENDAR_EVENTS: Dict[str, List[Dict[str, str]]] = {}
CALENDAR_FILE_NAME = "praxis_calendar_data.json"  # Name of the file to store calendar data

# --- Persistence Helper Functions ---
def _load_calendar_data_from_file() -> None:
    """Loads calendar events from the JSON file into CALENDAR_EVENTS."""
    global CALENDAR_EVENTS
    if os.path.exists(CALENDAR_FILE_NAME):
        try:
            with open(CALENDAR_FILE_NAME, 'r') as f:
                CALENDAR_EVENTS = json.load(f)
            logging.info(f"Calendar: Successfully loaded events from {CALENDAR_FILE_NAME}")
        except json.JSONDecodeError:
            logging.error(f"Calendar: Error decoding JSON from {CALENDAR_FILE_NAME}. Starting with an empty calendar.", exc_info=True)
            CALENDAR_EVENTS = {}  # Reset to empty if file is corrupt
        except Exception as e:
            logging.error(f"Calendar: Failed to load calendar events from {CALENDAR_FILE_NAME}: {e}", exc_info=True)
            CALENDAR_EVENTS = {}  # Reset on other errors
    else:
        logging.info(f"Calendar: {CALENDAR_FILE_NAME} not found. Starting with an empty calendar.")
        CALENDAR_EVENTS = {}

def _save_calendar_data_to_file() -> None:
    """Saves the current CALENDAR_EVENTS to the JSON file."""
    try:
        with open(CALENDAR_FILE_NAME, 'w') as f:
            json.dump(CALENDAR_EVENTS, f, indent=4)
        logging.info(f"Calendar: Successfully saved events to {CALENDAR_FILE_NAME}")
    except Exception as e:
        logging.error(f"Calendar: Failed to save calendar events to {CALENDAR_FILE_NAME}: {e}", exc_info=True)

# --- Initialization Skill ---
def initialize_calendar_data(context: Any) -> None:
    """
    Initializes calendar data by loading from file.
    This skill is intended for internal startup use.
    """
    _load_calendar_data_from_file()
    logging.info("Calendar: Data initialization process complete.")
    # context.speak("Calendar data initialized.", text_to_log="Calendar data initialized.") # Optional: if you want audible feedback

# --- Calendar Skill Functions ---
def get_calendar_current_date(context: Any) -> None:
    """Gets the current date in YYYY-MM-DD format."""
    current_date = datetime.now().strftime("%Y-%m-%d")
    context.speak(f"Today's date is {current_date}.")

def add_calendar_event(context: Any, event_name: str, event_date: str, event_details: Optional[str] = None) -> None:
    """Adds an event to the calendar for a specific date (YYYY-MM-DD)."""
    try:
        datetime.strptime(event_date, "%Y-%m-%d")  # Validate date format
    except ValueError:
        context.speak("Invalid date format. Please use YYYY-MM-DD.")
        return

    if event_date not in CALENDAR_EVENTS:
        CALENDAR_EVENTS[event_date] = []

    # Check for duplicate event names on the same day
    if any(event['name'] == event_name for event in CALENDAR_EVENTS[event_date]):
        context.speak(f"An event named '{event_name}' already exists on {event_date}.")
        return

    CALENDAR_EVENTS[event_date].append({"name": event_name, "details": event_details or ""})
    _save_calendar_data_to_file()
    context.speak(f"Event '{event_name}' added for {event_date}.")

def list_calendar_events(context: Any, event_date: str) -> None:
    """Lists all events for a specific date (YYYY-MM-DD)."""
    try:
        datetime.strptime(event_date, "%Y-%m-%d")  # Validate date format
    except ValueError:
        context.speak("Invalid date format. Please use YYYY-MM-DD.")
        return

    if event_date in CALENDAR_EVENTS and CALENDAR_EVENTS[event_date]:
        response = f"Events for {event_date}:\n"
        for event in CALENDAR_EVENTS[event_date]:
            response += f"- {event['name']}"
            if event['details']:
                response += f" (Details: {event['details']})"
            response += "\n"
        context.speak(response.strip())
    else:
        context.speak(f"No events found for {event_date}.")

def list_all_calendar_events(context: Any) -> None:
    """Lists all events currently in the calendar."""
    if not CALENDAR_EVENTS:
        context.speak("The calendar is currently empty.")
        return

    response = "All calendar events:\n"
    sorted_dates = sorted(CALENDAR_EVENTS.keys())
    for event_date in sorted_dates:
        if CALENDAR_EVENTS[event_date]: # Ensure there are events for this date
            response += f"\nDate: {event_date}\n"
            for event in CALENDAR_EVENTS[event_date]:
                response += f"  - {event['name']}"
                if event['details']:
                    response += f" (Details: {event['details']})"
                response += "\n"
    context.speak(response.strip())

def remove_calendar_event(context: Any, event_name: str, event_date: str) -> None:
    """Removes a specific event from the calendar by name and date (YYYY-MM-DD)."""
    try:
        datetime.strptime(event_date, "%Y-%m-%d")  # Validate date format
    except ValueError:
        context.speak("Invalid date format. Please use YYYY-MM-DD.")
        return

    if event_date in CALENDAR_EVENTS:
        original_length = len(CALENDAR_EVENTS[event_date])
        CALENDAR_EVENTS[event_date] = [event for event in CALENDAR_EVENTS[event_date] if event['name'] != event_name]
        
        if len(CALENDAR_EVENTS[event_date]) < original_length:
            context.speak(f"Event '{event_name}' on {event_date} removed.")
            if not CALENDAR_EVENTS[event_date]:  # Remove date key if no events left
                del CALENDAR_EVENTS[event_date]
            _save_calendar_data_to_file()
        else:
            context.speak(f"Event '{event_name}' not found on {event_date}.")
    else:
        context.speak(f"No events found for {event_date} to remove '{event_name}' from.")

def clear_all_calendar_events(context: Any) -> None:
    """Removes all events from the calendar."""
    global CALENDAR_EVENTS
    if not CALENDAR_EVENTS:
        context.speak("The calendar is already empty.")
        return
    CALENDAR_EVENTS.clear()
    _save_calendar_data_to_file()
    context.speak("All calendar events have been cleared.")

def _test_skill(context: Any) -> None:
    """Tests the calendar skill operations. Called by main.py during skill loading."""
    logging.info("Calendar Skill Test: Starting...")
    # Use unique names/dates for testing to avoid clashes if file exists
    test_date = "2099-12-31"
    test_event_name = "Calendar Test Event"
    
    # Ensure clean state for this specific test event
    if test_date in CALENDAR_EVENTS:
        CALENDAR_EVENTS[test_date] = [e for e in CALENDAR_EVENTS[test_date] if e['name'] != test_event_name]
        if not CALENDAR_EVENTS[test_date]:
            del CALENDAR_EVENTS[test_date]
    _save_calendar_data_to_file() # Save this potentially cleaned state

    add_calendar_event(context, test_event_name, test_date, "Test details")
    assert any(e['name'] == test_event_name for e in CALENDAR_EVENTS.get(test_date, [])), "Test event not added"
    # list_calendar_events(context, test_date) # This call is for visual confirmation via muted log, not strictly needed for assertion
    assert f"Event '{test_event_name}' added for {test_date}." in context.get_last_spoken_message_for_test()
    remove_calendar_event(context, test_event_name, test_date)
    assert not any(e['name'] == test_event_name for e in CALENDAR_EVENTS.get(test_date, [])), "Test event not removed"
    logging.info("Calendar Skill Test: Completed successfully.")


# Note: _load_calendar_data_from_file() is NOT called here directly.
# It will be called via the `initialize_calendar_data` skill from main.py.