# skills/utility_skills.py

def set_reminder(context, reminder_text=""):
    """Sets a simple reminder."""
    if reminder_text:
        context.speak(f"Okay, I'll remind you about: {reminder_text}")
    else:
        context.speak("What would you like to be reminded about?")