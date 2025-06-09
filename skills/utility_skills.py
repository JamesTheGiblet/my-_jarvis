# skills/utility_skills.py
import logging # Import standard logging

def set_reminder(context, reminder_text=""):
    """Sets a simple reminder."""
    if reminder_text:
        context.speak(f"Okay, I'll remind you about: {reminder_text}")
        logging.info(f"Reminder set for: {reminder_text}")
    else:
        context.speak("What would you like to be reminded about?")
        logging.info("Prompted user for reminder text as none was provided.")

def _test_skill(context):
    """
    Runs a quick self-test for the utility_skills module.
    It calls set_reminder with sample text.
    """
    logging.info("[utility_skills_test] Running self-test for utility_skills module...")
    try:
        test_reminder = "Check the oven in 10 minutes."

        # Test 1: Call set_reminder
        logging.info(f"[utility_skills_test] Testing set_reminder with text: '{test_reminder}'")
        set_reminder(context, test_reminder)

        logging.info("[utility_skills_test] All utility_skills self-tests passed successfully.")
    except Exception as e:
        logging.error(f"[utility_skills_test] Self-test FAILED: {e}", exc_info=True)
        raise # Re-raise the exception to be caught by load_skills in main.py