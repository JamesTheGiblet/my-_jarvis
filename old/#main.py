# main.py - Codex MK4 with Session Memory (Enhanced)

import datetime
import json
import os
import shlex
import re
import logging

import google.generativeai as genai
import pyttsx3
from dotenv import load_dotenv
from googlesearch import search

# Load environment variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(filename='codex.log', level=logging.INFO, format='%(asctime)s - %(message)s')

# Initialize TTS engine globally
engine = pyttsx3.init()

# -----------------------------------------------------------------------------
# ⚙️ SKILLS & CAPABILITIES
# -----------------------------------------------------------------------------

def speak(text):
    """Gives the AI a voice and prints the response."""
    print(f"Codex: {text}")
    try:
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print(f"Warning: Text-to-speech failed. {e}")

def get_time():
    """Returns the current time."""
    time_str = datetime.datetime.now().strftime("%I:%M %p")
    speak(f"Sir, the current time is {time_str}")

def get_date():
    """Returns the current date."""
    date_str = datetime.datetime.now().strftime("%B %d, %Y")
    speak(f"Today's date is {date_str}")

def web_search(query):
    """Performs a web search and returns the top 3 results."""
    if not query:
        speak("Of course, what would you like me to search for?")
        return
    speak(f"Right away. Searching the web for '{query}'...")
    try:
        results = [url for _, url in zip(range(3), search(query))]
        if results:
            speak("Here are the top results I found:")
            for url in results:
                speak(url)
        else:
            speak("I couldn't find any results for that query.")
    except Exception as e:
        speak("I'm sorry, sir. I encountered an error during the web search.")
        print(f"Error details: {e}")

# Optional memory recall skill (can be disabled if not needed)
def recall_memory():
    """Summarizes recent conversation memory (last 5 messages)."""
    if not chat_session.history:
        speak("No memory data found.")
        return
    recent = chat_session.history[-5:]
    speak("Here's a brief memory recall:")
    for msg in recent:
        print(f"{msg.role.title()}: {msg.parts[0].text}")

# -----------------------------------------------------------------------------
# SKILL REGISTRY
# -----------------------------------------------------------------------------

SKILLS = {
    "get_time": get_time,
    "get_date": get_date,
    "web_search": web_search,
    "recall_memory": recall_memory,
}

def execute_skill(skill_name, args):
    if skill_name in SKILLS:
        SKILLS[skill_name](**args)
    elif skill_name == "speak":
        speak(args.get("text", "I'm not sure what to say, sir."))
    else:
        fallback_handler(skill_name)

# -----------------------------------------------------------------------------
# 🔍 FALLBACK HANDLER
# -----------------------------------------------------------------------------

def fallback_handler(original_input):
    speak("I'm not sure how to handle that. Should I search it on the web?")
    confirm = input("Search web? (y/n): ").strip().lower()
    if confirm == "y":
        web_search(original_input)

# -----------------------------------------------------------------------------
# 📦 LLM Configuration
# -----------------------------------------------------------------------------

GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")
model = None

try:
    if not GOOGLE_API_KEY:
        raise ValueError("GEMINI_API_KEY not found in your .env file.")
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    print("AI Brain configured successfully.")
except Exception as e:
    print(f"Error configuring Google AI: {e}")

# -----------------------------------------------------------------------------
# 🧠 LLM Brain
# -----------------------------------------------------------------------------

def extract_json(text):
    try:
        json_str = re.search(r'{.*}', text, re.DOTALL)
        if json_str:
            return json.loads(json_str.group())
    except json.JSONDecodeError:
        pass
    return None

def strip_wake_words(command):
    for wake in ["codex", "hey codex", "okay codex", "jarvis"]:
        command = command.replace(wake, "")
    return command.strip()

def process_command_with_llm(command, chat_session):
    if not model:
        speak("My cognitive circuits are not configured. Please check the API key setup.")
        return

    prompt = f"""
        You are Codex, a J.A.R.V.I.S.-like AI assistant.
        Analyze the user's latest request based on the conversation history.

        Your available tools are:
        - get_time: Get the current time.
        - get_date: Get the current date.
        - web_search: Search the web. Requires a 'query' argument.

        If the request is conversational (e.g., a greeting), respond with skill 'speak'.

        Respond ONLY in JSON like:
        {{
            "skill": "web_search",
            "args": {{
                "query": "weather in London"
            }}
        }}
        
        User's latest request: "{command}"

        JSON Response:
    """

    try:
        response = chat_session.send_message(prompt)
        parsed_response = extract_json(response.text)

        if parsed_response:
            skill_name = parsed_response.get("skill")
            args = parsed_response.get("args", {})
            execute_skill(skill_name, args)
        else:
            fallback_handler(command)

    except Exception as e:
        speak("Apologies, I had trouble understanding that.")
        print(f"LLM Brain Error: {e}")

# -----------------------------------------------------------------------------
# 🪄 MAIN EVENT LOOP
# -----------------------------------------------------------------------------

def main():
    global chat_session
    if not model:
        speak("AI Brain failed to initialize. Exiting.")
        return

    speak("Codex MK3 cognitive model with session memory online. I am ready to assist.")
    chat_session = model.start_chat(history=[])

    while True:
        try:
            user_input = input("You: ").strip().lower()
            logging.info(f"User: {user_input}")

            if user_input in ["exit", "quit", "goodbye"]:
                speak("Goodbye, sir.")
                break

            clean_input = strip_wake_words(user_input)
            process_command_with_llm(clean_input, chat_session)

        except KeyboardInterrupt:
            speak("System interrupted. Shutting down.")
            break
        except Exception as e:
            logging.error(f"Critical Error: {e}")
            speak("I've encountered a critical error, sir. Please check the console.")

# -----------------------------------------------------------------------------

if __name__ == "__main__":
    main()
