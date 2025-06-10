# main.py (New Orchestrator Version)
from datetime import datetime, timezone, timedelta # Added timezone and timedelta
import logging
import os
import importlib
import random
import inspect, time
from typing import Callable, Dict, Any, Optional
import threading # For voice input thread
from collections import deque # For rate limiting queues
import knowledge_base # Import the new module

import pyttsx3
# Import components from our new modules
try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False
    print("Praxis Warning: SpeechRecognition library not found. Voice input will be disabled. Falling back to text input.")
    print("To enable voice input, please install SpeechRecognition and PyAudio: pip install SpeechRecognition PyAudio")
from config import model
from brain import process_command_with_llm, strip_wake_words
from config import GEMINI_1_5_FLASH_RPM, GEMINI_1_5_FLASH_TPM, GEMINI_1_5_FLASH_RPD # Import rate limit constants for reference
# Setup basic logging
logging.basicConfig(filename='codex.log', level=logging.INFO, format='%(asctime)s - %(message)s')

# --- Global Components ---
try:
    engine = pyttsx3.init()
except Exception as e:
    print(f"Failed to initialize TTS engine: {e}")
    engine = None

# --- Constants ---
INACTIVITY_THRESHOLD_SECONDS = 300 # 5 minutes, adjust as needed - Made global for GUI access
PRAXIS_VERSION_INFO = "Praxis (Phase 4 GUI Integration)"
DEFAULT_AI_NAME = "Praxis" # Default name for the AI

# --- GUI Integration: Callback for speak ---
gui_output_callback: Optional[Callable[[str], None]] = None

def set_gui_output_callback(callback_func: Callable[[str], None]) -> None:
    """Sets a callback function for the GUI to receive spoken/logged messages."""
    global gui_output_callback
    gui_output_callback = callback_func
# --- End GUI Integration ---
praxis_instance_for_speak: Optional['PraxisCore'] = None # To allow speak to access current AI name

def speak(text_to_speak: str, text_to_log: Optional[str] = None, from_skill_context: bool = False) -> None:
    """Gives the AI a voice and prints the response."""
    tts_safe_text = str(text_to_speak)
    log_safe_text = str(text_to_log if text_to_log is not None else tts_safe_text)
    # Determine AI name: if called from skill context and instance exists, use its name, else default.
    ai_console_name = praxis_instance_for_speak.ai_name if from_skill_context and praxis_instance_for_speak and hasattr(praxis_instance_for_speak, 'ai_name') else DEFAULT_AI_NAME
    console_message = f"{ai_console_name}: {log_safe_text}"

    print(console_message) # This goes to console

    # If a GUI callback is registered, send the message to the GUI
    if gui_output_callback:
        gui_output_callback(console_message) # Or just log_safe_text, depending on GUI needs

    if engine:
        try:
            engine.say(tts_safe_text) # TTS reads this
            engine.runAndWait()
        except Exception as e:
            warning_message = f"{ai_console_name} Warning: Text-to-speech failed. {e}"
            print(warning_message)
            if gui_output_callback:
                gui_output_callback(warning_message)

class SkillContext:
    """A class to hold shared resources that skills might need."""
    def __init__(self, speak_func, chat_session, knowledge_base_module, skills_registry: Dict[str, Callable[..., Any]], current_user_name: str, input_mode_config_ref: Dict[str, str], speech_recognition_available_flag: bool, praxis_core_ref: 'PraxisCore'):
        self._raw_speak_func = speak_func # Store the original speak function from main
        self.chat_session = chat_session
        self.is_muted = False # Initialize is_muted state
        self.skills_registry = skills_registry # Access to all loaded skills
        self.current_user_name = current_user_name # Store the active user's name
        self.spoken_messages_during_mute: list[str] = [] # To capture messages when muted
        self.kb = knowledge_base_module # Provide access to knowledge_base functions
        self.input_mode_config = input_mode_config_ref # Reference to main's input mode config
        self.speech_recognition_available = speech_recognition_available_flag # Flag for SR availability
        self._praxis_core_ref = praxis_core_ref # Reference to PraxisCore instance for callbacks like name update

    @property
    def ai_name(self) -> str:
        return self._praxis_core_ref.ai_name

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
            self._raw_speak_func(text_to_speak, text_to_log, from_skill_context=True)

    def clear_spoken_messages_for_test(self) -> None:
        """Clears the list of captured spoken messages. Useful for isolating test assertions."""
        self.spoken_messages_during_mute = []

    def get_last_spoken_message_for_test(self) -> Optional[str]:
        """Returns the last message captured during mute, or None if no messages were captured."""
        return self.spoken_messages_during_mute[-1] if self.spoken_messages_during_mute else None

    def update_ai_name_globally(self, new_name: str) -> None:
        """Callback for skills to update the AI's name in PraxisCore."""
        self._praxis_core_ref.update_ai_name(new_name)

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

def listen_for_command(recognizer: 'sr.Recognizer', microphone: 'sr.Microphone') -> Optional[str]:
    """
    Listens for a command from the user via microphone and returns the transcribed text.
    Returns None if speech is not understood or an error occurs.
    """
    if not SPEECH_RECOGNITION_AVAILABLE:
        return None # Should not be called if library is unavailable, but as a safeguard.

    with microphone as source:
        # Speak and print are handled by the global speak function, which will update GUI if callback is set
        speak("Listening...") # Simplified message for GUI context
        recognizer.adjust_for_ambient_noise(source, duration=0.5) # Adjust for ambient noise
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10) # Listen for up to 5s, phrase up to 10s
        except sr.WaitTimeoutError:
            # Check if a GUI callback exists to avoid TTS if GUI is primary interaction
            # However, speak itself handles GUI callback, so direct call is fine.
            speak("I didn't hear anything.")
            return None
        except Exception as e: # Catch other potential errors during listen
            logging.error(f"Error during recognizer.listen: {e}")
            speak("There was an issue with the microphone.")
            return None

    try:
        speak("Recognizing...")
        print("Praxis: Recognizing...") # Console feedback
        # Using Google Web Speech API for recognition by default
        # This requires an internet connection.
        # For offline, you'd configure Sphinx or another engine.
        command_text = recognizer.recognize_google(audio)
        print(f"You (voice): {command_text}") # Log what was heard
        return command_text.strip()
    except sr.UnknownValueError:
        speak("I'm sorry, sir, I couldn't understand what you said.")
    except sr.RequestError as e:
        speak(f"My speech recognition service seems to be unavailable. Error: {e}")
        logging.error(f"Speech recognition request error: {e}")
    return None

class PraxisCore:
    def __init__(self, gui_update_status_callback: Optional[Callable[[Dict[str, str]], None]] = None):
        global SKILLS, praxis_instance_for_speak # Allow PraxisCore to manage globals
        praxis_instance_for_speak = self # Make this instance available to the global speak function

        self.ai_name: str = DEFAULT_AI_NAME 
        self.has_been_formally_introduced: bool = False
        self.gui_update_status_callback = gui_update_status_callback
        self.is_running = True 

        if not model:
            critical_msg = "PraxisCore: AI Brain (Gemini Model) failed to initialize. Cannot start."
            logging.critical(critical_msg)
            # The global speak function will handle GUI callback if set
            speak(critical_msg)
            raise RuntimeError(critical_msg)

        self.engine = engine 
        self.recognizer = None
        self.microphone = None
        if SPEECH_RECOGNITION_AVAILABLE:
            try:
                self.recognizer = sr.Recognizer()
                self.microphone = sr.Microphone()
            except Exception as e:
                logging.error(f"Failed to initialize SpeechRecognition components: {e}")
                speak(f"Warning: Speech recognition components failed to initialize: {e}")
                # SPEECH_RECOGNITION_AVAILABLE = False # Could update global flag if needed, but skills rely on initial value
        
        knowledge_base.init_db()
        self.kb = knowledge_base

        self.input_mode_config = {'mode': 'text'}
        if SPEECH_RECOGNITION_AVAILABLE and self.recognizer and self.microphone:
            self.input_mode_config['mode'] = 'voice'
        
        self.current_user_name: str = ""
        self.chat_session = model.start_chat(history=[])
        
        # Note: Rate limits for the configured model (Gemini 1.5 Flash) are available in config.py:
        # RPM: GEMINI_1_5_FLASH_RPM, TPM: GEMINI_1_5_FLASH_TPM, RPD: GEMINI_1_5_FLASH_RPD
        # These constants can be used here or passed to SkillContext if client-side rate limiting is implemented.

        SKILLS = {} 
        self.skills_registry_ref = SKILLS

        self.skill_context: Optional[SkillContext] = None
        self.available_skills_prompt_str: str = "No skills loaded yet."
        self.last_interaction_time: datetime = datetime.now()

        # Rate Limiting / Monitoring Attributes
        self.request_timestamps_rpm = deque()  # Stores datetime objects of requests
        self.token_usage_tpm = deque()         # Stores (datetime, token_count) tuples
        self.daily_request_count = 0
        self.current_day_for_rpd = datetime.now(timezone.utc).date()

        self.pending_confirmation: Optional[Dict[str, Any]] = None
        self.failed_skill_module_tests_ref: list[str] = [] # To store results from load_skills

    # --- Rate Limiting Methods ---
    def _clean_old_metrics(self):
        """Removes outdated entries from RPM and TPM deques."""
        now = datetime.now(timezone.utc)
        one_minute_ago = now - timedelta(minutes=1)

        # Clean RPM queue
        while self.request_timestamps_rpm and self.request_timestamps_rpm[0] < one_minute_ago:
            self.request_timestamps_rpm.popleft()

        # Clean TPM queue
        while self.token_usage_tpm and self.token_usage_tpm[0][0] < one_minute_ago:
            self.token_usage_tpm.popleft()

    def _reset_daily_metrics_if_new_day(self):
        """Resets the daily request counter if a new UTC day has started."""
        today_utc = datetime.now(timezone.utc).date()
        if today_utc > self.current_day_for_rpd:
            logging.info(
                f"PraxisCore: New day detected ({today_utc}). Resetting daily request count. "
                f"Old count: {self.daily_request_count} for day {self.current_day_for_rpd}"
            )
            self.daily_request_count = 0
            self.current_day_for_rpd = today_utc
            # RPM and TPM are rolling windows, so they don't need a hard reset daily,
            # _clean_old_metrics handles their rolling nature.

    def _can_make_request(self) -> tuple[bool, str]:
        """Checks if an API request can be made based on client-side tracked RPM and RPD."""
        self._clean_old_metrics()  # Ensure metrics are up-to-date

        # RPM Check
        current_rpm = len(self.request_timestamps_rpm)
        if current_rpm >= GEMINI_1_5_FLASH_RPM:
            # Optional: Calculate time until next request is allowed
            # time_since_oldest_rpm = (datetime.now(timezone.utc) - self.request_timestamps_rpm[0]).total_seconds()
            # wait_time_seconds = 60 - time_since_oldest_rpm
            # reason = f"RPM limit ({GEMINI_1_5_FLASH_RPM}) reached. Current: {current_rpm}. Try again in {wait_time_seconds:.1f}s."
            reason = f"RPM limit ({GEMINI_1_5_FLASH_RPM}) reached. Current: {current_rpm}"
            return False, reason

        # RPD Check
        if self.daily_request_count >= GEMINI_1_5_FLASH_RPD:
            reason = f"RPD limit ({GEMINI_1_5_FLASH_RPD}) reached. Current: {self.daily_request_count}"
            return False, reason

        # TPM is primarily monitored post-call, as response tokens are unknown beforehand.
        # A very basic proactive TPM check could be added here if desired, e.g.,
        # current_tpm = self.get_current_tpm()
        # if current_tpm >= GEMINI_1_5_FLASH_TPM:
        #    return False, f"TPM limit ({GEMINI_1_5_FLASH_TPM}) reached. Current: {current_tpm}"
        # However, this is aggressive as it doesn't account for the current call's tokens yet.

        return True, "OK"

    def _record_api_usage(self, prompt_tokens: int, response_tokens: int):
        """Records an API usage attempt and its token consumption."""
        now = datetime.now(timezone.utc)

        self.request_timestamps_rpm.append(now)
        self.daily_request_count += 1

        total_tokens_for_call = prompt_tokens + response_tokens
        if total_tokens_for_call > 0:
            self.token_usage_tpm.append((now, total_tokens_for_call))

        self._clean_old_metrics() # Clean up again after adding new entries

        logging.info(
            f"PraxisCore: API usage recorded. Prompt Tokens: {prompt_tokens}, Response Tokens: {response_tokens}. "
            f"Current RPM: {self.get_current_rpm()}, Current TPM: {self.get_current_tpm()}, Today's RPD: {self.daily_request_count}"
        )
        self._update_gui_status() # Update GUI with new metrics

    def get_current_rpm(self) -> int:
        self._clean_old_metrics()
        return len(self.request_timestamps_rpm)

    def get_current_tpm(self) -> int:
        self._clean_old_metrics()
        return sum(tokens for _, tokens in self.token_usage_tpm)

    def update_ai_name(self, new_name: str):
        """Updates the AI's name and informs the user."""
        if new_name and new_name != self.ai_name:
            old_name = self.ai_name
            self.ai_name = new_name
            logging.info(f"PraxisCore: AI name updated from '{old_name}' to '{self.ai_name}'.")
            
            if self.skill_context: # Ensure skill_context is initialized
                # If it's the first time setting a non-default name AND formal intro hasn't happened,
                # _perform_formal_greeting will handle the main announcement of the new name.
                # Otherwise (e.g., changing an already set name), we need to announce the change here.
                if not (old_name == DEFAULT_AI_NAME and not self.has_been_formally_introduced):
                    self.skill_context.speak(f"Understood. My designation is now {self.ai_name}.")

                if old_name == DEFAULT_AI_NAME and not self.has_been_formally_introduced:
                    self._perform_formal_greeting() # Perform full greeting with the new name
            self._update_gui_status()

    def _update_gui_status(self, praxis_state_override: Optional[str] = None, confirmation_prompt: Optional[str] = None):
        # This method in PraxisCore should only check if the callback is set.
        # The callback itself (which is a GUI method) will handle GUI-specific checks like root window existence.
        # The previous check `if not hasattr(self, 'root')` would cause this to return early, as PraxisCore doesn't own `root`.
        if self.gui_update_status_callback:
            state_to_report = praxis_state_override if praxis_state_override else "Idle"
            status = {
                "user": self.current_user_name if self.current_user_name else "[Not Set]",
                "mode": self.input_mode_config['mode'],
                "praxis_state": state_to_report,
                # Rate limit status
                "rpm": f"{self.get_current_rpm()}/{GEMINI_1_5_FLASH_RPM}",
                "tpm": f"{self.get_current_tpm()}/{GEMINI_1_5_FLASH_TPM}",
                "rpd": f"{self.daily_request_count}/{GEMINI_1_5_FLASH_RPD}",
            }
            if confirmation_prompt:
                status["confirmation_prompt"] = confirmation_prompt
            elif self.pending_confirmation: # If a confirmation is pending, reflect it
                state_to_report = "Awaiting Confirmation" 
                status["praxis_state"] = state_to_report
                # Ensure confirmation_prompt key exists even if value is None
                status["confirmation_prompt"] = self.pending_confirmation.get("prompt") 
            self.gui_update_status_callback(status)

    def _perform_formal_greeting(self):
        """Performs the standard AI welcome and status messages."""
        if not self.skill_context or self.has_been_formally_introduced:
            return

        # This part announces the AI name and user. This should always happen once per session.
        self.skill_context.speak(f"Welcome. Initializing systems for {self.current_user_name}. I am {self.ai_name}.")
        
        existing_profile_items = self.kb.get_user_profile_items_by_category(self.current_user_name, "interest")
        if existing_profile_items:
            # Check if user has interacted before using a flag in user_data_store
            USER_INTERACTED_FLAG_KEY = "user_interaction_recorded" # Key to check/store interaction
            user_interaction_record = self.kb.get_user_data(self.current_user_name, USER_INTERACTED_FLAG_KEY)

            if user_interaction_record: # If any record exists (e.g., a timestamp string from a previous session)
                self.skill_context.speak(f"It's good to see you again, {self.current_user_name}!")
            else:
                self.skill_context.speak(f"A pleasure to meet you for the first time, {self.current_user_name}. I look forward to assisting you.")

                # Mark that this first formal interaction has occurred for this user by storing a timestamp
                self.kb.store_user_data(self.current_user_name, USER_INTERACTED_FLAG_KEY, datetime.now(timezone.utc).isoformat())
        
        # Construct version string using current AI name
        version_info_parts = PRAXIS_VERSION_INFO.split(" ", 1)
        descriptive_part_of_version = version_info_parts[1] if len(version_info_parts) > 1 else "(Version details unavailable)"
        current_version_display = f"{self.ai_name} {descriptive_part_of_version}"

        startup_message_base = f"{current_version_display}. Systems nominal for {self.current_user_name}."
        
        final_startup_message = startup_message_base
        if not self.failed_skill_module_tests_ref:
            final_startup_message += " All skill module self-tests passed"
        else:
            failed_modules_str = ", ".join(self.failed_skill_module_tests_ref)
            final_startup_message += f" Warning: Self-test(s) failed for: {failed_modules_str}."
        
        self.skill_context.speak(f"{final_startup_message}.")
        self.has_been_formally_introduced = True

    def initialize_user_session(self, user_name: str) -> None:
        if not user_name:
            speak("User name cannot be empty.")
            self._update_gui_status(praxis_state_override="Error: No user name")
            return

        self.has_been_formally_introduced = False # Reset for new user session
        self.current_user_name = user_name

        self.skill_context = SkillContext(
            speak_func=speak, 
            chat_session=self.chat_session,
            knowledge_base_module=self.kb,
            skills_registry=self.skills_registry_ref, 
            current_user_name=self.current_user_name,
            input_mode_config_ref=self.input_mode_config,
            speech_recognition_available_flag=SPEECH_RECOGNITION_AVAILABLE and bool(self.recognizer and self.microphone),
            praxis_core_ref=self 
        )

        self.failed_skill_module_tests_ref = load_skills(self.skill_context) 
        self.available_skills_prompt_str = generate_skills_description_for_llm(SKILLS, speak)

        name_is_set_or_chosen = False
        if "get_self_name" in SKILLS:
            try:
                retrieved_name = SKILLS["get_self_name"](self.skill_context)
                if retrieved_name:
                    # Name exists, update PraxisCore directly.
                    # update_ai_name will handle the greeting if it's the first time.
                    self.update_ai_name(retrieved_name)
                    logging.info(f"PraxisCore: Loaded AI name '{self.ai_name}' from knowledge base.")
                    name_is_set_or_chosen = True
            except Exception as e:
                logging.error(f"PraxisCore: Error trying to get AI name during init: {e}", exc_info=True)
                # Proceed, will likely use default name or try to choose one.

        if not name_is_set_or_chosen: # If name wasn't loaded from KB
            if "choose_and_set_name" in SKILLS:
                # Do not automatically call choose_and_set_name as it's CLI interactive.
                # Inform the user instead.
                self.skill_context.speak(
                    "I don't seem to have a chosen name yet. "
                    "You can ask me to 'choose and set name' if you'd like, sir."
                )
                logging.info(
                    "PraxisCore: No AI name in KB. Informed user they can invoke 'choose_and_set_name'."
                )
            else:
                logging.info(
                    "PraxisCore: No AI name in KB and 'choose_and_set_name' skill not available. Using default name."
                )

        # If after all attempts (loading or choosing) the formal introduction hasn't happened yet,
        # (e.g. name remained default, or naming skills were absent/cancelled), perform it now.
        if not self.has_been_formally_introduced:
            self._perform_formal_greeting()
        logging.info(f"PraxisCore: User identified as '{self.current_user_name}'. AI name is '{self.ai_name}'.")
        if "initialize_calendar_data" in SKILLS:
            logging.info("PraxisCore: Attempting to initialize calendar data...")
            try:
                SKILLS["initialize_calendar_data"](self.skill_context)
            except Exception as e:
                logging.error(f"PraxisCore: Error calling initialize_calendar_data: {e}", exc_info=True)
        
        self.last_interaction_time = datetime.now()
        self._update_gui_status()

    def process_command_text(self, user_input: str) -> None:
        if not self.skill_context or not self.current_user_name:
            speak("System not fully initialized. Please set user first.")
            logging.warning("PraxisCore: process_command_text called before full initialization.")
            self._update_gui_status(praxis_state_override="Error: Not Initialized")
            return

        if not user_input:
            self._update_gui_status()
            return

        self.last_interaction_time = datetime.now()
        logging.info(f"User ({self.current_user_name} - {self.input_mode_config['mode']}): {user_input}")
        self._update_gui_status(praxis_state_override="Thinking...")

        if user_input.lower() in ["exit", "quit", "goodbye", f"goodbye {self.ai_name.lower().strip()}"]:
            self.skill_context.speak("Goodbye.")
            self.is_running = False 
            self._update_gui_status(praxis_state_override="Shutting down")
            return

        clean_input, _ = strip_wake_words(user_input)
        
        # --- Rate Limiting Pre-check ---
        self._reset_daily_metrics_if_new_day()
        can_request, reason = self._can_make_request()
        if not can_request:
            self.skill_context.speak(f"I am currently unable to process new requests due to API rate limits: {reason}. Please try again later.")
            logging.warning(f"PraxisCore: API call blocked due to client-side rate limit: {reason}")
            self._update_gui_status(praxis_state_override=f"Rate Limited: {reason.split('.')[0]}") # Short reason for GUI
            return
        # --- End Rate Limiting Pre-check ---

        try:
            # The 'model' instance for token counting is available as config.model
            llm_model_instance = model # from config import model

            parsed_command, p_tokens, r_tokens = process_command_with_llm(
                command=clean_input,
                chat_session=self.chat_session,
                available_skills_prompt_str=self.available_skills_prompt_str,
                ai_name=self.ai_name,
                model=llm_model_instance
            )

            # Record API usage attempt, regardless of whether parsed_command is valid
            self._record_api_usage(p_tokens, r_tokens)

            if parsed_command:
                skill_name = parsed_command.get("skill")
                args = parsed_command.get("args", {})
                if skill_name in SKILLS:
                    skill_function = SKILLS[skill_name]
                    logging.info(f"PraxisCore: Attempting to call skill: {skill_name} with args: {args}")
                    skill_executed_successfully = False
                    error_msg_for_kb = None
                    try:
                        skill_function(self.skill_context, **args)
                        skill_executed_successfully = True
                    except TypeError as te:
                        error_msg_for_kb = f"Argument mismatch or skill definition error: {te}"
                        logging.error(f"PraxisCore: Error during execution of skill '{skill_name}' due to TypeError: {te}", exc_info=True)
                        self.skill_context.speak(f"I had trouble with the arguments for the action: {skill_name}.")
                    except Exception as skill_e:
                        error_msg_for_kb = str(skill_e)
                        logging.error(f"PraxisCore: Error during execution of skill '{skill_name}': {skill_e}", exc_info=True)
                        self.skill_context.speak(f"I encountered an error while trying to perform the action: {skill_name}.")
                    finally:
                        self.kb.record_skill_invocation(
                            skill_name=skill_name, success=skill_executed_successfully,
                            args_used=args, error_message=error_msg_for_kb
                        )
                elif skill_name == "speak":
                    text_for_speak_skill = args.get("text", "I'm not sure what to say.")
                    self.skill_context.speak(text_for_speak_skill) 
                    self.kb.record_skill_invocation(skill_name="speak", success=True, args_used=args)
                else:
                    # LLM returned a JSON but with an unknown skill
                    logging.warning(f"PraxisCore: LLM returned unknown skill '{skill_name}'. Args: {args}")
                    self._trigger_fallback_handler(clean_input)
            else:
                # process_command_with_llm returned None for parsed_command
                # This could be due to API error, blocked prompt, or JSON extraction failure.
                # _record_api_usage has already been called with potentially 0 response tokens.
                if p_tokens > 0 and r_tokens == 0: # Likely an API error or block after prompt was processed
                    self.skill_context.speak("I had trouble processing that request with my core systems. Please try rephrasing or try again later.")
                else: # Other parsing or unexpected issue
                    self._trigger_fallback_handler(clean_input)
        except Exception as e:
            logging.error(f"PraxisCore: Critical error in process_command_text: {e}", exc_info=True)
            speak("A critical error occurred while processing your command.")
        finally:
            self._update_gui_status() 

    def _trigger_fallback_handler(self, original_input: str):
        if not self.skill_context: return
        
        prompt_message = "I'm not quite sure how to handle that. Should I try searching the web for you?"
        self.pending_confirmation = {
            "type": "web_search_fallback",
            "original_input": original_input,
            "prompt": prompt_message
        }
        self.skill_context.speak(prompt_message) 
        self._update_gui_status(praxis_state_override="Awaiting Confirmation", confirmation_prompt=prompt_message)

    def handle_gui_confirmation(self, confirmed: bool):
        if not self.pending_confirmation or not self.skill_context:
            logging.warning("PraxisCore: handle_gui_confirmation called with no pending confirmation.")
            self._update_gui_status()
            return

        conf_type = self.pending_confirmation.get("type")
        original_input = self.pending_confirmation.get("original_input")
        
        self.pending_confirmation = None 

        if conf_type == "web_search_fallback":
            if confirmed:
                if "web_search" in SKILLS:
                    logging.info(f"PraxisCore: Web search confirmed by GUI for: {original_input}")
                    SKILLS["web_search"](self.skill_context, query=original_input)
                else:
                    self.skill_context.speak("The web search skill is not available.")
            else:
                logging.info(f"PraxisCore: Web search declined by GUI for: {original_input}")
                self.skill_context.speak("Okay, I won't search the web.")
        
        self._update_gui_status()

    def _listen_in_thread(self):
        if not self.recognizer or not self.microphone or not self.skill_context:
            speak("Voice components not ready.")
            self._update_gui_status() 
            return

        self._update_gui_status(praxis_state_override="Listening...")
        command_text = listen_for_command(self.recognizer, self.microphone) 

        if self.is_running: 
            if command_text:
                self.process_command_text(command_text)
            else:
                self._update_gui_status() 

    def start_voice_input(self) -> None:
        if not (SPEECH_RECOGNITION_AVAILABLE and self.recognizer and self.microphone):
            speak("Voice input is not available on this system.")
            self._update_gui_status()
            return
        
        if self.input_mode_config['mode'] != 'voice':
            self.toggle_input_mode_core(to_mode='voice') 
            if self.input_mode_config['mode'] != 'voice': 
                return 

        voice_thread = threading.Thread(target=self._listen_in_thread, daemon=True)
        voice_thread.start()

    def handle_inactivity(self) -> None:
        if not self.skill_context or not self.current_user_name or not self.is_running:
            return 

        current_time = datetime.now()
        if (current_time - self.last_interaction_time).total_seconds() > INACTIVITY_THRESHOLD_SECONDS:
            if self.pending_confirmation: 
                logging.info("PraxisCore: Inactivity detected, but awaiting confirmation. Skipping proactive engagement.")
                self.last_interaction_time = current_time 
                return

            logging.info("PraxisCore: Inactivity threshold reached. Triggering proactive engagement.")
            self._update_gui_status(praxis_state_override="Proactive...")
            action_choice = random.choices(
                ["offer_assistance", "suggest_topic", "attempt_learning"],
                weights=[0.55, 0.35, 0.10], k=1
            )[0]

            if action_choice == "attempt_learning" and "attempt_autonomous_skill_learning" in SKILLS:
                SKILLS["attempt_autonomous_skill_learning"](self.skill_context)
            elif action_choice == "suggest_topic" and "suggest_engagement_topic" in SKILLS:
                SKILLS["suggest_engagement_topic"](self.skill_context)
            else:
                self.skill_context.speak(f"It's been a while, {self.skill_context.current_user_name}. Is there anything I can assist you with?")
            self.last_interaction_time = current_time
            self._update_gui_status() 

    def toggle_input_mode_core(self, to_mode: Optional[str] = None) -> None:
        if not self.skill_context: return

        effective_sr_available = SPEECH_RECOGNITION_AVAILABLE and bool(self.recognizer and self.microphone)

        if to_mode:
            if to_mode == 'voice' and not effective_sr_available:
                self.skill_context.speak("Cannot switch to voice mode, speech recognition is not available/ready.")
                self._update_gui_status()
                return
            self.input_mode_config['mode'] = to_mode
        else: 
            if self.input_mode_config['mode'] == 'text':
                if effective_sr_available:
                    self.input_mode_config['mode'] = 'voice'
                else:
                    self.skill_context.speak("Voice input is not available to toggle to.")
                    self._update_gui_status()
                    return 
            else:
                self.input_mode_config['mode'] = 'text'
        
        self.skill_context.speak(f"Input mode switched to {self.input_mode_config['mode']}.")
        logging.info(f"PraxisCore: Input mode set to {self.input_mode_config['mode']}.")
        self._update_gui_status()
        
        if self.input_mode_config['mode'] == 'voice' and self.is_running:
             # Check to_mode to avoid loop if called internally for initial switch
            if to_mode == 'voice' or (to_mode is None and self.input_mode_config['mode'] == 'voice'):
                self.start_voice_input()

    def toggle_tts_mute_core(self) -> bool: 
        if not self.skill_context: return False
        self.skill_context.is_muted = not self.skill_context.is_muted
        status = "muted" if self.skill_context.is_muted else "unmuted"
        
        if not self.skill_context.is_muted: 
            speak(f"Text-to-speech is now {status}.") 
        else: 
            log_msg = f"Text-to-speech is now {status}."
            logging.info(log_msg)
            if gui_output_callback: 
                gui_output_callback(f"System: {log_msg}")
                
        logging.info(f"PraxisCore: TTS {status}.")
        self._update_gui_status() 
        return self.skill_context.is_muted

    def shutdown(self):
        if self.is_running:
            self.is_running = False # Signal threads to stop
            # Short delay to allow threads to notice the flag if they are in a loop
            time.sleep(0.1)
            # Use skill_context.speak if available to use the AI's name, else global speak
            (self.skill_context.speak if self.skill_context else speak)(f"{self.ai_name} shutting down.")
            logging.info("PraxisCore shutdown initiated.")
            self._update_gui_status(praxis_state_override="Shutdown")

if __name__ == "__main__":
    # This block is typically for running the script directly.
    # For GUI applications, gui.py will be the entry point.
    # If you want to test PraxisCore in CLI:
    print(f"{PRAXIS_VERSION_INFO} - main.py executed. To run Praxis with GUI, execute gui.py.")
    
    # Example CLI test (uncomment to use):
    # def cli_speak_callback(message: str):
    #     print(f"CLI_SPEAK: {message}")
    # def cli_status_callback(status: Dict[str, str]):
    #     print(f"CLI_STATUS: {status}")

    # set_gui_output_callback(cli_speak_callback)
    # core = None
    # try:
    #     core = PraxisCore(gui_update_status_callback=cli_status_callback)
    #     user = input("Enter username: ")
    #     core.initialize_user_session(user)
    #     while core.is_running:
    #         core.handle_inactivity() # Check inactivity periodically
    #         if core.input_mode_config['mode'] == 'text':
    #             if core.pending_confirmation:
    #                 conf_prompt = core.pending_confirmation.get("prompt", "Confirm?")
    #                 conf_resp = input(f"Praxis (Confirmation): {conf_prompt} (yes/no): ").strip().lower()
    #                 core.handle_gui_confirmation(conf_resp == 'yes')
    #             else:
    #                 cmd = input(f"{core.current_user_name} (text): ").strip()
    #                 if cmd:
    #                     core.process_command_text(cmd)
    #         elif core.input_mode_config['mode'] == 'voice':
    #             print("Voice mode active in CLI. Type 'text' to switch to text, or a command to simulate voice.")
    #             cmd = input(f"{core.current_user_name} (voice-sim): ").strip()
    #             if cmd.lower() == 'text':
    #                 core.toggle_input_mode_core('text')
    #             elif cmd:
    #                 core.process_command_text(cmd) # Simulate voice input as text
    #         
    #         time.sleep(0.1) # Brief pause to prevent tight loop in CLI
    # except KeyboardInterrupt:
    #     print("\nCLI interrupted by user.")
    # except RuntimeError as e:
    #     print(f"CLI Runtime Error: {e}")
    # except Exception as e:
    #     print(f"CLI Unexpected Error: {e}")
    #     logging.error("CLI unexpected error", exc_info=True)
    # finally:
    #     if core and core.is_running:
    #         print("Shutting down PraxisCore from CLI...")
    #         core.shutdown()
    #     print("CLI session ended.")
    pass
