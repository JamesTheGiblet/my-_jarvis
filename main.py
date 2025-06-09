# main.py (New Orchestrator Version)
from datetime import datetime
import logging
import os
import importlib
import inspect, time # Added time
from typing import Callable, Dict, Any, Optional
import knowledge_base # Import the new module

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
    def __init__(self, speak_func, chat_session, knowledge_base_module, skills_registry: Dict[str, Callable[..., Any]], current_user_name: str):
        self._raw_speak_func = speak_func # Store the original speak function from main
        self.chat_session = chat_session
        self.is_muted = False # Initialize is_muted state
        self.skills_registry = skills_registry # Access to all loaded skills
        self.current_user_name = current_user_name # Store the active user's name
        self.spoken_messages_during_mute: list[str] = [] # To capture messages when muted
        self.kb = knowledge_base_module # Provide access to knowledge_base functions

    def speak(self, text_to_speak: str, text_to_log: Optional[str] = None) -> None:
        """Handles speaking output, capturing messages if muted."""
        # Determine the text to log/capture
        if self.is_muted:
            # If muted (e.g., during a skill test), only log the intended speech.
            self.spoken_messages_during_mute.append(text_to_log if text_to_log is not None else text_to_speak)
            logging.info(f"Muted Speak (captured for test): {text_to_log if text_to_log is not None else text_to_speak}")
            # Do not call self._raw_speak_func, so no TTS and no console print via global speak
        else:
            # If not muted, use the normal speak function
            self._raw_speak_func(text_to_speak, text_to_log)

    def clear_spoken_messages_for_test(self) -> None:
        """Clears the list of captured spoken messages. Useful for isolating test assertions."""
        self.spoken_messages_during_mute = []

    def get_last_spoken_message_for_test(self) -> Optional[str]:
        """Returns the last message captured during mute, or None if no messages were captured."""
        return self.spoken_messages_during_mute[-1] if self.spoken_messages_during_mute else None

# --- Skill Registry (populated dynamically) ---
SKILLS: Dict[str, Callable[..., Any]] = {}

def load_skills(skill_context: SkillContext, skills_directory: str = "skills") -> list[str]:
    """
    Dynamically loads skills from Python files in the specified directory.
    Skills are public functions (not starting with an underscore).
    Also runs a _test_skill function if present in the module.
    Returns a list of short module names that failed their self-tests.
    """
    global SKILLS
    failed_module_tests: list[str] = []
    if not os.path.isdir(skills_directory):
        logging.warning(f"Skills directory '{skills_directory}' not found. No custom skills loaded.")
        return failed_module_tests

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
                        failed_module_tests.append(module_name_short)
                        skill_context.speak(f"Warning: Self-test for skills in {module_name_short} module failed. Please check the logs.")
            except ImportError as e:
                logging.error(f"Failed to import module {module_name_full}: {e}")
            except Exception as e:
                logging.error(f"Error loading skill from {module_name_full}: {e}")

def generate_skills_description_for_llm(skills_from_files: Dict[str, Callable[..., Any]], global_speak_func: Callable) -> str:
    """
    Generates a formatted string describing available skills for the LLM.
    Includes skills loaded from files and the built-in speak capability.
    """
    descriptions = []

    # 1. Add built-in 'speak' skill description
    # The LLM is expected to use it as: {"skill": "speak", "args": {"text": "..."}}
    speak_doc = inspect.getdoc(global_speak_func) or "Responds with speech."
    # Taking the first line of the docstring for brevity in the prompt
    speak_doc_first_line = speak_doc.strip().split('\n')[0]
    descriptions.append(f"- speak: {speak_doc_first_line} (Args: text)")

    # 2. Add skills loaded from files
    for skill_name, skill_func in skills_from_files.items():
        docstring = inspect.getdoc(skill_func)
        if not docstring:
            docstring_first_line = "No description available."
        else:
            docstring_first_line = docstring.strip().split('\n')[0]

        arg_details = ""
        try:
            sig = inspect.signature(skill_func)
            params = []
            for name, param in sig.parameters.items():
                if name == 'context':  # Skip context parameter for LLM description
                    continue
                param_str = name
                if param.annotation != inspect.Parameter.empty and hasattr(param.annotation, '__name__'):
                    param_str += f" ({param.annotation.__name__})"
                params.append(param_str)
            
            if params:
                arg_details = f" (Args: {', '.join(params)})"
            else:
                arg_details = " (Takes no additional arguments)"
        except ValueError:  # inspect.signature might fail for some callables
            arg_details = " (Argument inspection not available)"
        descriptions.append(f"- {skill_name}: {docstring_first_line}{arg_details}")
    
    if not descriptions:
        return "No skills are currently available."
        
    return "You have access to the following skills/tools:\n" + "\n".join(descriptions)

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

# --- Configuration for Inactivity ---
INACTIVITY_THRESHOLD_SECONDS = 300 # 5 minutes, adjust as needed

def main() -> None:
    """The main function to orchestrate the AI assistant."""
    if not model:
        # Use print directly as speak() might rely on engine which could be part of the problem
        print("Praxis: AI Brain (Gemini Model) failed to initialize. Please check your API key and configuration. Exiting.")
        logging.critical("AI Brain (Gemini Model) failed to initialize. Exiting.")
        return

    # Initialize the KnowledgeBase database
    knowledge_base.init_db()

    # --- Initial User Identification ---
    current_user_name = ""
    while not current_user_name:
        # Use global speak and input for this initial setup
        speak("Welcome. I am Praxis. Who am I speaking to today?")
        # We use a direct input here as it's part of the initial setup, not a skill interaction.
        raw_name_input = input("Your Name: ").strip()
        if raw_name_input:
            current_user_name = raw_name_input
            speak(f"A pleasure to meet you, {current_user_name}.")
            logging.info(f"Main: User identified as '{current_user_name}'.")
        else:
            speak("I'm sorry, I didn't catch that. Could you please tell me your name?")

    # Initialize chat session and skill context BEFORE loading skills
    chat_session = model.start_chat(history=[])
    # Create a context object to pass to skills
    skill_context = SkillContext(speak, chat_session, knowledge_base, SKILLS, current_user_name)

    # Load skills dynamically at startup, passing the context for tests
    failed_skill_module_tests = load_skills(skill_context)
    
    # Generate the dynamic skills description for the LLM
    available_skills_prompt_str = generate_skills_description_for_llm(SKILLS, speak)

    # Initialize calendar data by calling its specific initialization skill, if present
    if "initialize_calendar_data" in SKILLS:
        logging.info("Main: Attempting to initialize calendar data...")
        try:
            # Pass the skill_context, though initialize_calendar_data might not use all of it
            SKILLS["initialize_calendar_data"](skill_context)
            logging.info("Main: Calendar data initialization skill called.")
        except Exception as e:
            logging.error(f"Main: Error calling initialize_calendar_data: {e}", exc_info=True)

    startup_message = "Praxis (Phase 2 observe and report complete). Systems nominal."
    if not failed_skill_module_tests:
        startup_message += " All skill module self-tests passed successfully."
    else:
        failed_modules_str = ", ".join(failed_skill_module_tests)
        startup_message += f" Warning: The self-test for the following skill module(s) failed: {failed_modules_str}. Please investigate the logs."
    speak(startup_message)

    last_interaction_time = datetime.now()

    while True:
        try:
            # Check for inactivity BEFORE asking for input
            current_time = datetime.now()
            if (current_time - last_interaction_time).total_seconds() > INACTIVITY_THRESHOLD_SECONDS:
                # This is a simple check. A more sophisticated system might use
                # non-blocking input or a separate thread for continuous monitoring.
                skill_context.speak("It's been a while, sir. Is there anything I can assist you with?")
                last_interaction_time = current_time # Reset timer after asking to avoid immediate re-trigger

            user_input = input("You: ").strip()
            if not user_input:
                # If user just hits Enter, we don't treat it as a full interaction for resetting the timer,
                # but we also don't want to immediately re-prompt for inactivity if they are just pausing.
                # For now, an empty input will not reset last_interaction_time, allowing the inactivity prompt
                # to trigger if they remain idle after hitting Enter.
                continue

            last_interaction_time = datetime.now() # Reset on any valid input from the user
            logging.info(f"User: {user_input}")
            if user_input.lower() in ["exit", "quit", "goodbye"]:
                speak("Goodbye, sir.")
                break

            clean_input = strip_wake_words(user_input)
            
            # 1. THINK: Get the desired action from the LLM brain
            parsed_command: Optional[Dict[str, Any]] = process_command_with_llm(
                command=clean_input, 
                chat_session=chat_session,
                available_skills_prompt_str=available_skills_prompt_str # Pass the dynamic skills list
            )

            # 2. ACT: Execute the command
            if parsed_command:
                skill_name = parsed_command.get("skill")
                args = parsed_command.get("args", {})

                if skill_name in SKILLS:
                    skill_function = SKILLS[skill_name]
                    logging.info(f"Attempting to call skill: {skill_name} with args: {args}")
                    skill_executed_successfully = False # Flag
                    error_msg_for_kb: Optional[str] = None
                    try:
                        # Pass the context and other arguments to the skill
                        skill_function(skill_context, **args)
                        logging.info(f"Successfully called skill: {skill_name}")
                        skill_executed_successfully = True
                    except TypeError as te: # Specifically catch TypeError for argument mismatches
                        error_msg_for_kb = f"Argument mismatch or skill definition error: {te}"
                        logging.error(f"Error during execution of skill '{skill_name}' due to TypeError (check arguments and skill definition): {te}", exc_info=True)
                        skill_context.speak(f"I had trouble with the arguments for the action: {skill_name}. The developer may need to check this.")
                        # skill_executed_successfully remains False
                    except Exception as skill_e: # Catch other exceptions from within the skill
                        error_msg_for_kb = str(skill_e)
                        logging.error(f"Error during execution of skill '{skill_name}' with args {args}: {skill_e}", exc_info=True)
                        skill_context.speak(f"I encountered an error while trying to perform the action: {skill_name}. Please check the logs.")
                        # skill_executed_successfully remains False
                    finally:
                        # Record skill invocation in KnowledgeBase
                        knowledge_base.record_skill_invocation(
                            skill_name=skill_name,
                            success=skill_executed_successfully,
                            args_used=args,
                            error_message=error_msg_for_kb
                        )
                elif skill_name == "speak":
                    # When LLM directly uses 'speak' skill, text_to_speak and text_to_log are the same.
                    text_for_speak_skill = args.get("text", "I'm not sure what to say, sir.")
                    # Call the global speak function directly here, or ensure SkillContext's speak is used if preferred.
                    # Using global speak for simplicity as it's a direct LLM 'speak' command.
                    speak(text_for_speak_skill)
                    knowledge_base.record_skill_invocation(
                        skill_name="speak", # Log this as a distinct action/skill
                        success=True,
                        args_used=args
                    )
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