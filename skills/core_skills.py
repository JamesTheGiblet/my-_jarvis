# c:\Users\gilbe\Desktop\my _jarvis\skills\core_skills.py
import datetime
# This import is necessary for the web_search function.
# It's better to have it at the top of the file.
from googlesearch import search

def get_time(context): # Accepts context
    """Returns the current time."""
    time_str = datetime.datetime.now().strftime("%I:%M %p")
    context.speak(f"Sir, the current time is {time_str}") # Uses context.speak

def get_date(context): # Accepts context
    """Returns the current date."""
    date_str = datetime.datetime.now().strftime("%B %d, %Y")
    context.speak(f"Today's date is {date_str}") # Uses context.speak

def web_search(context, query=""): # Accepts context
    """Performs a web search and returns the top 3 results."""
    if not query:
        context.speak("Of course, what would you like me to search for?")
        return
    context.speak(f"Right away. Searching the web for '{query}'...")
    try:
        # FIX: Removed all extra keyword arguments.
        # The function is called with only the query.
        # The results are converted to a list, and then we take the first 3.
        all_results = list(search(query))
        results = all_results[:3]

        if results:
            context.speak("Here are the top results I found:")
            for url in results:
                context.speak(url)
        else:
            context.speak("I couldn't find any results for that query.")
    except Exception as e:
        context.speak("I'm sorry, sir. I encountered an error during the web search.")
        print(f"Error details: {e}")


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
