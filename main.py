# main.py (New Orchestrator Version)
import logging
import pyttsx3
import os
import importlib
import inspect

# Import components from our new modules
from config import model
from brain import process_command_with_llm, strip_wake_words

# Setup basic logging
logging.basicConfig(filename='codex.log', level=logging.INFO, format='%(asctime)s - %(message)s')

# --- Global Components ---
try:
    engine = pyttsx3.init()
except Exception as e:
    print(f"Failed to initialize TTS engine: {e}")
    engine = None

def speak(text_to_speak, text_to_log=None):
    """Gives the AI a voice and prints the response."""
    tts_safe_text = str(text_to_speak)
    log_safe_text = str(text_to_log if text_to_log is not None else tts_safe_text)

    print("Codex:", log_safe_text) # This goes to console and forms part of LLM's history view
    if engine:
        try:
            engine.say(tts_safe_text) # TTS reads this
            engine.runAndWait()
        except Exception as e:
            print(f"Warning: Text-to-speech failed. {e}")

class SkillContext:
    """A class to hold shared resources that skills might need."""
    def __init__(self, speak_func, chat_session):
        self._raw_speak_func = speak_func # Store the original speak function from main
        self.chat_session = chat_session

    def speak(self, text_to_speak, text_to_log=None):
        self._raw_speak_func(text_to_speak, text_to_log)

# --- Skill Registry (populated dynamically) ---
SKILLS = {}

def load_skills(skills_directory="skills"):
    """
    Dynamically loads skills from Python files in the specified directory.
    Skills are public functions (not starting with an underscore).
    """
    global SKILLS
    if not os.path.isdir(skills_directory):
        logging.warning(f"Skills directory '{skills_directory}' not found. No custom skills loaded.")
        return

    # Ensure the skills directory is treated as a package by having __init__.py
    # For importlib.import_module to work like 'skills.module_name'
    
    for filename in os.listdir(skills_directory):
        if filename.endswith(".py") and not filename.startswith("_"):
            module_name_short = filename[:-3] # e.g., utility_skills
            module_name_full = f"{skills_directory}.{module_name_short}" # e.g., skills.utility_skills
            try:
                module = importlib.import_module(module_name_full)
                for attribute_name in dir(module):
                    attribute = getattr(module, attribute_name)
                    if inspect.isfunction(attribute) and not attribute_name.startswith("_"):
                        SKILLS[attribute_name] = attribute
                        logging.info(f"Successfully loaded skill: {attribute_name} from {module_name_full}")
            except ImportError as e:
                logging.error(f"Failed to import module {module_name_full}: {e}")
            except Exception as e:
                logging.error(f"Error loading skill from {module_name_full}: {e}")

def fallback_handler(context, original_input):
    """Handles cases where the LLM fails to select a skill."""
    context.speak("I'm not quite sure how to handle that. Should I try searching the web for you?")
    try:
        confirm = input("Search web? (y/n): ").strip().lower()
        if confirm == 'y' and "web_search" in SKILLS: # Check if web_search skill is loaded
            SKILLS["web_search"](context, query=original_input)
        elif confirm == 'y':
            context.speak("The web search skill is not available.")
    except Exception as e:
        context.speak(f"An error occurred while handling your request: {e}")

def main():
    """The main function to orchestrate the AI assistant."""
    if not model:
        speak("AI Brain failed to initialize. Please check your API key and configuration. Exiting.")
        return

    # Load skills dynamically at startup
    load_skills()
    
    speak("Codex MK5 (Modular) online. Systems nominal.")
    
    chat_session = model.start_chat(history=[])
    # Create a context object to pass to skills
    skill_context = SkillContext(speak, chat_session)

    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue

            logging.info(f"User: {user_input}")

            if user_input.lower() in ["exit", "quit", "goodbye"]:
                speak("Goodbye, sir.")
                break

            clean_input = strip_wake_words(user_input)
            
            # 1. THINK: Get the desired action from the LLM brain
            parsed_command = process_command_with_llm(clean_input, chat_session)

            # 2. ACT: Execute the command
            if parsed_command:
                skill_name = parsed_command.get("skill")
                args = parsed_command.get("args", {})

                if skill_name in SKILLS:
                    skill_function = SKILLS[skill_name]
                    logging.info(f"Attempting to call skill: {skill_name} with args: {args}")
                    try:
                        # Pass the context and other arguments to the skill
                        skill_function(skill_context, **args)
                        logging.info(f"Successfully called skill: {skill_name}")
                    except Exception as skill_e: # Catch exceptions from within the skill
                        logging.error(f"Error during execution of skill '{skill_name}' with args {args}: {skill_e}", exc_info=True)
                        skill_context.speak(f"I encountered an error while trying to perform the action: {skill_name}. Please check the logs.")
                elif skill_name == "speak":
                    # When LLM directly uses 'speak' skill, text_to_speak and text_to_log are the same.
                    text_for_speak_skill = args.get("text", "I'm not sure what to say, sir.")
                    # Call the global speak function directly here, or ensure SkillContext's speak is used if preferred.
                    # Using global speak for simplicity as it's a direct LLM 'speak' command.
                    speak(text_for_speak_skill)
                else:
                    # The LLM chose a skill that doesn't exist
                    fallback_handler(skill_context, clean_input)
            else:
                # The LLM failed to return valid JSON
                fallback_handler(skill_context, clean_input)

        except KeyboardInterrupt:
            speak("System interrupted. Shutting down.")
            break
        except Exception as e:
            error_message = f"A critical error occurred in the main loop: {e}"
            logging.error(error_message)
            speak("I've encountered a critical error, sir. Please check the logs.")

if __name__ == "__main__":
    main()