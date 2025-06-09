# main.py (New Orchestrator Version)
import logging
import os
import importlib
import inspect
from typing import Callable, Dict, Any, Optional

import pyttsx3
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

def speak(text_to_speak: str, text_to_log: Optional[str] = None) -> None:
    """Gives the AI a voice and prints the response."""
    tts_safe_text = str(text_to_speak)
    log_safe_text = str(text_to_log if text_to_log is not None else tts_safe_text)

    # The AI's name for console output, aligning with the project name "Praxis"
    ai_console_name = "Praxis"
    print(f"{ai_console_name}: {log_safe_text}") # This goes to console
    if engine:
        try:
            engine.say(tts_safe_text) # TTS reads this
            engine.runAndWait()
        except Exception as e:
            print(f"{ai_console_name} Warning: Text-to-speech failed. {e}")

class SkillContext:
    """A class to hold shared resources that skills might need."""
    def __init__(self, speak_func, chat_session):
        self._raw_speak_func = speak_func # Store the original speak function from main
        self.chat_session = chat_session
        self.is_muted = False # Initialize is_muted state

    def speak(self, text_to_speak: str, text_to_log: Optional[str] = None) -> None:
        if self.is_muted:
            # If muted (e.g., during a skill test), only log the intended speech.
            log_text = str(text_to_log if text_to_log is not None else text_to_speak)
            logging.info(f"Muted Speak (from skill test): {log_text}")
            # Do not call self._raw_speak_func, so no TTS and no console print via global speak
        else:
            # If not muted, use the normal speak function
            self._raw_speak_func(text_to_speak, text_to_log)

# --- Skill Registry (populated dynamically) ---
SKILLS: Dict[str, Callable[..., Any]] = {}

def load_skills(skill_context: SkillContext, skills_directory: str = "skills") -> None:
    """
    Dynamically loads skills from Python files in the specified directory.
    Skills are public functions (not starting with an underscore).
    Also runs a _test_skill function if present in the module.
    """
    global SKILLS
    if not os.path.isdir(skills_directory):
        logging.warning(f"Skills directory '{skills_directory}' not found. No custom skills loaded.")
        return

    # Ensure the skills directory is treated as a package by having __init__.py
    for filename in os.listdir(skills_directory):
        if filename.endswith(".py") and not filename.startswith("_"):
            module_name_short = filename[:-3]
            module_name_full = f"{skills_directory}.{module_name_short}"
            try:
                module = importlib.import_module(module_name_full)
                has_test_function = hasattr(module, "_test_skill")

                for attribute_name in dir(module):
                    attribute = getattr(module, attribute_name)
                    if inspect.isfunction(attribute) and not attribute_name.startswith("_"):
                        # Exclude _test_skill itself from being registered as a callable skill
                        if attribute_name == "_test_skill":
                            continue
                        SKILLS[attribute_name] = attribute
                        logging.info(f"Successfully loaded skill: {attribute_name} from {module_name_full}")
                
                if has_test_function:
                    logging.info(f"Found _test_skill in {module_name_full}. Running test...")
                    test_function: Callable[[SkillContext], None] = getattr(module, "_test_skill")

                    original_mute_state = skill_context.is_muted  # Save current mute state
                    skill_context.is_muted = True  # Mute context for the duration of the test
                    test_passed = False
                    try:
                        # Pass the skill_context to the test function
                        test_function(skill_context) 
                        logging.info(f"SUCCESS: _test_skill for {module_name_full} passed.")
                        test_passed = True
                    except Exception as test_e:
                        logging.error(f"FAILURE: _test_skill for {module_name_full} failed: {test_e}", exc_info=True)
                        # test_passed remains False
                    finally:
                        skill_context.is_muted = original_mute_state # Restore original mute state

                    if not test_passed:
                        # Speak a warning if a self-test fails
                        # This speak call uses the restored mute state, so it will be audible.
                        skill_context.speak(f"Warning: Self-test for skills in {module_name_short} module failed. Please check the logs.")
            except ImportError as e:
                logging.error(f"Failed to import module {module_name_full}: {e}")
            except Exception as e:
                logging.error(f"Error loading skill from {module_name_full}: {e}")

def fallback_handler(context: SkillContext, original_input: str) -> None:
    """Handles cases where the LLM fails to select a skill."""
    context.speak("I'm not quite sure how to handle that. Should I try searching the web for you?")
    try:
        confirm = input("Search web? (y/n): ").strip().lower()
        if confirm == 'y' and "web_search" in SKILLS: # Check if web_search skill is loaded
            SKILLS["web_search"](context, query=original_input) # Assuming web_search takes query
        elif confirm == 'y':
            context.speak("The web search skill is not available.")
    except Exception as e:
        logging.error(f"Error in fallback_handler during web search confirmation: {e}", exc_info=True)
        context.speak("An unexpected error occurred while trying to process that.")

def main() -> None:
    """The main function to orchestrate the AI assistant."""
    if not model:
        # Use print directly as speak() might rely on engine which could be part of the problem
        print("Praxis: AI Brain (Gemini Model) failed to initialize. Please check your API key and configuration. Exiting.")
        logging.critical("AI Brain (Gemini Model) failed to initialize. Exiting.")
        return

    # Initialize chat session and skill context BEFORE loading skills
    chat_session = model.start_chat(history=[])
    # Create a context object to pass to skills
    skill_context = SkillContext(speak, chat_session)

    # Load skills dynamically at startup, passing the context for tests
    load_skills(skill_context) 
    
    speak("Praxis (Foundational Layer) online. Systems nominal.")

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
            parsed_command: Optional[Dict[str, Any]] = process_command_with_llm(clean_input, chat_session)

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