# main.py (New Orchestrator Version)
from datetime import datetime, timezone, timedelta # Added timezone and timedelta
import logging
import os
import importlib
import random
import inspect, time
from typing import Callable, Dict, Any, Optional
import threading # For voice input thread
import queue # For TTS queue
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

try:
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    NLTK_VADER_AVAILABLE = True
except ImportError:
    NLTK_VADER_AVAILABLE = False
    print("Praxis Warning: NLTK or VADER lexicon not found. Sentiment analysis will be basic. Install with: pip install nltk")
from config import model
from brain import process_command_with_llm, strip_wake_words
from config import GEMINI_1_5_FLASH_RPM, GEMINI_1_5_FLASH_TPM, GEMINI_1_5_FLASH_RPD # Import rate limit constants for reference
# Setup basic logging
logging.basicConfig(filename='codex.log', level=logging.INFO, format='%(asctime)s - %(message)s')

# --- Global Components ---
try:
    engine = pyttsx3.init()
    TTS_ENGINE_AVAILABLE = True
except Exception as e:
    print(f"Failed to initialize TTS engine: {e}")
    engine = None
    TTS_ENGINE_AVAILABLE = False

# --- Constants ---
INACTIVITY_THRESHOLD_SECONDS = 300 # 5 minutes, adjust as needed - Made global for GUI access
PRAXIS_VERSION_INFO = "Praxis (Phase 5 GUI Integration)"
DEFAULT_AI_NAME = "Praxis" # Default name for the AI

# --- GUI Integration: Callback for speak ---
tts_queue = queue.Queue() # Queue for TTS requests
TTS_SHUTDOWN_SENTINEL = object() # Sentinel object to signal TTS worker to stop
tts_worker_thread_instance: Optional[threading.Thread] = None

gui_output_callback: Optional[Callable[[str], None]] = None

def set_gui_output_callback(callback_func: Callable[[str], None]) -> None:
    """Sets a callback function for the GUI to receive spoken/logged messages."""
    global gui_output_callback
    gui_output_callback = callback_func
# --- End GUI Integration ---
praxis_instance_for_speak: Optional['PraxisCore'] = None # To allow speak to access current AI name

def tts_worker():
    """Processes TTS requests from a queue in a dedicated thread."""
    logging.info("TTS worker thread started.")
    while TTS_ENGINE_AVAILABLE and engine: # Ensure engine is still valid
        try:
            item = tts_queue.get() # Blocks until an item is available
            if item is TTS_SHUTDOWN_SENTINEL:
                logging.info("TTS_SHUTDOWN_SENTINEL received. TTS worker thread stopping.")
                tts_queue.task_done()
                break
            
            tts_text = str(item) # Ensure it's a string
            current_ai_name = praxis_instance_for_speak.ai_name if praxis_instance_for_speak else DEFAULT_AI_NAME

            try:
                engine.say(tts_text)
                engine.runAndWait()
            except RuntimeError as re_tts:
                # This specific error is what we are trying to avoid.
                # If it still happens, it's a deeper issue or rapid re-initialization.
                logging.error(f"TTS Worker: pyttsx3 runtime error (e.g., loop already started) for text '{tts_text[:30]}...'. Error: {re_tts}", exc_info=True)
                # Attempting to recover by re-initializing might be risky here. Best to log and skip.
            except Exception as e_tts:
                warning_message = f"{current_ai_name} Warning: Text-to-speech failed in worker. Text: '{tts_text[:30]}...'. Error: {e_tts}"
                print(warning_message)
                if gui_output_callback: gui_output_callback(warning_message)
                logging.error(f"TTS Worker: Exception during pyttsx3 operation: {e_tts}", exc_info=True)
            finally:
                tts_queue.task_done() # Signal that this task is done
        except Exception as e_queue:
            logging.error(f"TTS Worker: Error in main loop: {e_queue}", exc_info=True)
            if isinstance(e_queue, (KeyboardInterrupt, SystemExit)): break
    logging.info("TTS worker thread finished.")

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

    if TTS_ENGINE_AVAILABLE and engine:
        tts_queue.put(tts_safe_text) # Put text onto the queue for the worker thread
    if praxis_instance_for_speak and hasattr(praxis_instance_for_speak, 'current_command_spoken_parts'):
        praxis_instance_for_speak.current_command_spoken_parts.append(tts_safe_text)
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
    SKILLS = {} # Clear existing skills before loading

    if not os.path.isdir(skills_directory):
        logging.warning(f"Skills directory '{skills_directory}' not found. No custom skills loaded.")
        return failed_module_tests

    # Walk through the skills directory and its subdirectories
    for root, _, files in os.walk(skills_directory):
        # Create the package path relative to the skills directory
        # e.g., skills/abilities -> skills.abilities
        relative_root = os.path.relpath(root, skills_directory).replace(os.sep, '.')
        package_prefix = f"{skills_directory}.{relative_root}" if relative_root != '.' else skills_directory

        for filename in files:
            if filename.endswith(".py") and not filename.startswith("_"):
                module_name_short = filename[:-3]
                module_name_full = f"{package_prefix}.{module_name_short}"
                
                try:
                    # Import the module using its full package path
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
                            test_function(skill_context) 
                            logging.info(f"SUCCESS: _test_skill for {module_name_full} passed.")
                            test_passed = True
                        except Exception as test_e:
                            logging.error(f"FAILURE: _test_skill for {module_name_full} failed: {test_e}", exc_info=True)
                        finally:
                            skill_context.is_muted = original_mute_state # Restore original mute state

                        if not test_passed:
                            failed_module_tests.append(module_name_full) # Use full name for clarity
                            skill_context.speak(f"Warning: Self-test for skills in {module_name_full} module failed. Please check the logs.")
                except ImportError as e:
                    logging.error(f"Failed to import module {module_name_full}: {e}")
                except Exception as e:
                    logging.error(f"Error loading skill from {module_name_full}: {e}")
    return failed_module_tests

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
    def __init__(self, gui_update_status_callback: Optional[Callable[[Dict[str, str], bool], None]] = None): # Added bool for feedback buttons
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

        # self.engine is global, no need to store instance variable if using global directly
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
        
        # For user feedback on last interaction
        self.last_interaction_id_for_feedback: Optional[int] = None
        self.last_ai_response_summary_for_feedback: Optional[str] = None
        self.current_command_spoken_parts: List[str] = []

        self.sentiment_analyzer = SentimentIntensityAnalyzer() if NLTK_VADER_AVAILABLE else None

        # Start the TTS worker thread if it's not already running and engine is available
        global tts_worker_thread_instance
        if TTS_ENGINE_AVAILABLE and engine and (tts_worker_thread_instance is None or not tts_worker_thread_instance.is_alive()):
            tts_worker_thread_instance = threading.Thread(target=tts_worker, daemon=True)
            tts_worker_thread_instance.start()
        elif not TTS_ENGINE_AVAILABLE:
            logging.warning("PraxisCore: TTS engine not available, TTS worker thread not started.")
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

    def _update_gui_status(self, praxis_state_override: Optional[str] = None, confirmation_prompt: Optional[str] = None, enable_feedback_buttons: bool = False):
        # This method in PraxisCore should only check if the callback is set.
        # The callback itself (which is a GUI method) will handle GUI-specific checks like root window existence.
        if self.gui_update_status_callback:
            state_to_report = praxis_state_override if praxis_state_override else "Idle"
            status = {
                "user": self.current_user_name if self.current_user_name else "[Not Set]",
                "mode": self.input_mode_config['mode'],
                "praxis_state": state_to_report,
                "rpm": f"{self.get_current_rpm()}/{GEMINI_1_5_FLASH_RPM}",
                "tpm": f"{self.get_current_tpm()}/{GEMINI_1_5_FLASH_TPM}",
                "rpd": f"{self.daily_request_count}/{GEMINI_1_5_FLASH_RPD}",
            }
            if confirmation_prompt:
                status["confirmation_prompt"] = confirmation_prompt
            elif self.pending_confirmation: 
                state_to_report = "Awaiting Confirmation" 
                status["praxis_state"] = state_to_report
                status["confirmation_prompt"] = self.pending_confirmation.get("prompt") 
            self.gui_update_status_callback(status, enable_feedback_buttons)

    def _perform_formal_greeting(self):
        """Performs the standard AI welcome and status messages."""
        if not self.skill_context or self.has_been_formally_introduced:
            return

        self.skill_context.speak(f"Welcome. Initializing systems for {self.current_user_name}. I am {self.ai_name}.")
        
        existing_profile_items = self.kb.get_user_profile_items_by_category(self.current_user_name, "interest")
        if existing_profile_items:
            USER_INTERACTED_FLAG_KEY = "user_interaction_recorded" 
            user_interaction_record = self.kb.get_user_data(self.current_user_name, USER_INTERACTED_FLAG_KEY)

            if user_interaction_record: 
                self.skill_context.speak(f"It's good to see you again, {self.current_user_name}!")
            else:
                self.skill_context.speak(f"A pleasure to meet you for the first time, {self.current_user_name}. I look forward to assisting you.")
                self.kb.store_user_data(self.current_user_name, USER_INTERACTED_FLAG_KEY, datetime.now(timezone.utc).isoformat())
        
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

        self.has_been_formally_introduced = False 
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
                    self.update_ai_name(retrieved_name)
                    logging.info(f"PraxisCore: Loaded AI name '{self.ai_name}' from knowledge base.")
                    name_is_set_or_chosen = True
            except Exception as e:
                logging.error(f"PraxisCore: Error trying to get AI name during init: {e}", exc_info=True)

        if not name_is_set_or_chosen: 
            if "choose_and_set_name" in SKILLS:
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
            self._update_gui_status(enable_feedback_buttons=(self.last_interaction_id_for_feedback is not None))
            return

        self.last_interaction_time = datetime.now()
        self.current_command_spoken_parts = [] # Reset for current command
        logging.info(f"User ({self.current_user_name} - {self.input_mode_config['mode']}): {user_input}")
        self._update_gui_status(praxis_state_override="Thinking...")

        def analyze_user_sentiment(text: str) -> str:
            if self.sentiment_analyzer:
                vs = self.sentiment_analyzer.polarity_scores(text)
                compound = vs['compound']
                if compound >= 0.05:
                    if any(phrase in text.lower() for phrase in ["stupid", "won't work", "damn", "this is frustrating", "fix it"]):
                        return "FRUSTRATED"
                    return "POSITIVE"
                elif compound <= -0.05:
                    if any(phrase in text.lower() for phrase in ["stupid", "won't work", "damn", "this is frustrating", "fix it"]):
                        return "FRUSTRATED"
                    return "NEGATIVE" 
            text_lower = text.lower() 
            if any(phrase in text_lower for phrase in ["stupid", "won't work", "damn", "this is frustrating", "fix it"]): return "FRUSTRATED"
            if any(phrase in text_lower for phrase in ["thank you", "great", "awesome", "perfect", "excellent"]): return "POSITIVE" 
            if "?" in text or any(phrase in text_lower for phrase in ["how do i", "what is", "can you explain", "could you"]): return "QUESTIONING"
            return "NEUTRAL" 

        user_sentiment = analyze_user_sentiment(user_input) 
        logging.info(f"PraxisCore: Detected user sentiment: {user_sentiment} for input: '{user_input}'")
        
        if user_input.lower() in ["exit", "quit", "goodbye", f"goodbye {self.ai_name.lower().strip()}"]:
            self.skill_context.speak("Goodbye.")
            self.is_running = False 
            self._update_gui_status(praxis_state_override="Shutting down")
            return

        clean_input, _ = strip_wake_words(user_input)
        
        self._reset_daily_metrics_if_new_day()
        can_request, reason = self._can_make_request()
        if not can_request:
            self.skill_context.speak(f"I am currently unable to process new requests due to API rate limits: {reason}. Please try again later.")
            logging.warning(f"PraxisCore: API call blocked due to client-side rate limit: {reason}")
            self._update_gui_status(praxis_state_override=f"Rate Limited: {reason.split('.')[0]}", enable_feedback_buttons=(self.last_interaction_id_for_feedback is not None)) 
            return
        
        try:
            llm_model_instance = model 

            parsed_command, p_tokens, r_tokens = process_command_with_llm(
                command=clean_input,
                chat_session=self.chat_session,
                available_skills_prompt_str=self.available_skills_prompt_str,
                ai_name=self.ai_name,
                model=llm_model_instance,
                user_sentiment=user_sentiment 
            )

            self.last_interaction_id_for_feedback = None 
            self._record_api_usage(p_tokens, r_tokens)

            if parsed_command:
                skill_name = parsed_command.get("skill")
                args = parsed_command.get("args", {})
                explanation = parsed_command.get("explanation", "No explanation provided by LLM.")
                confidence_str = parsed_command.get("confidence_score", "-1.0")
                try:
                    confidence = float(confidence_str)
                except ValueError:
                    confidence = -1.0 
                warnings_list = parsed_command.get("warnings", [])

                if skill_name in SKILLS:
                    skill_function = SKILLS[skill_name]
                    logging.info(f"PraxisCore: Attempting to call skill: {skill_name} with args: {args}")
                    skill_executed_successfully = False # Default to False
                    error_msg_for_kb = None
                    skill_return_value = None
                    try:
                        if self.skill_context:
                            self.skill_context.clear_spoken_messages_for_test() 
                        skill_return_value = skill_function(self.skill_context, **args)

                        if isinstance(skill_return_value, bool):
                            skill_executed_successfully = skill_return_value
                        elif skill_return_value is None: # No explicit return, assume success if no exception
                            skill_executed_successfully = True
                        else: # Unexpected return type, log it and assume failure for safety
                            logging.warning(f"Skill '{skill_name}' returned an unexpected type: {type(skill_return_value)}. Assuming failure.")
                            skill_executed_successfully = False # Already default, but explicit
                            error_msg_for_kb = f"Skill returned unexpected type: {type(skill_return_value)}"

                    except TypeError as te:
                        error_msg_for_kb = f"Argument mismatch or skill definition error: {te}"
                        logging.error(f"PraxisCore: Error during execution of skill '{skill_name}' due to TypeError: {te}", exc_info=True)
                        self.skill_context.speak(f"I had trouble with the arguments for the action: {skill_name}.")
                        skill_executed_successfully = False # Ensure it's false on exception
                    except Exception as skill_e:
                        error_msg_for_kb = str(skill_e)
                        logging.error(f"PraxisCore: Error during execution of skill '{skill_name}': {skill_e}", exc_info=True)
                        self.skill_context.speak(f"I encountered an error while trying to perform the action: {skill_name}.")
                        skill_executed_successfully = False # Ensure it's false on exception
                    finally:
                        self.kb.record_skill_invocation(
                            skill_name=skill_name, success=skill_executed_successfully,
                            args_used=args, error_message=error_msg_for_kb
                        )
                    self.last_ai_response_summary_for_feedback = self.skill_context.get_last_spoken_message_for_test() if self.skill_context else "N/A"
                elif skill_name == "speak":
                    text_for_speak_skill = args.get("text", "I'm not sure what to say.")
                    self.skill_context.speak(text_for_speak_skill) 
                    self.kb.record_skill_invocation(skill_name="speak", success=True, args_used=args)
                    self.last_ai_response_summary_for_feedback = text_for_speak_skill
                else:
                    logging.warning(f"PraxisCore: LLM returned unknown skill '{skill_name}'. Args: {args}")
                    self.last_ai_response_summary_for_feedback = f"Attempted unknown skill: {skill_name}"
                    self._trigger_fallback_handler(clean_input)
                
                self.last_interaction_id_for_feedback = self.kb.log_interaction_details(
                    user_name=self.current_user_name, ai_name=self.ai_name, user_input=clean_input,
                    llm_skill_choice=skill_name, llm_args_chosen=args,
                    llm_explanation=explanation, llm_confidence=confidence, llm_warnings=warnings_list,
                    ai_final_response_summary=self.last_ai_response_summary_for_feedback
                )
            else:
                if p_tokens > 0 and r_tokens == 0: 
                    self.skill_context.speak("I had trouble processing that request with my core systems. Please try rephrasing or try again later.")
                    self.last_ai_response_summary_for_feedback = "Core system processing error."
                else: 
                    self._trigger_fallback_handler(clean_input)
                    self.last_ai_response_summary_for_feedback = "Fallback triggered due to parsing issue."
                
                self.last_interaction_id_for_feedback = self.kb.log_interaction_details(
                    user_name=self.current_user_name, ai_name=self.ai_name, user_input=clean_input,
                    llm_skill_choice="N/A (LLM Parse Error)", llm_args_chosen=None,
                    llm_explanation="Failed to parse LLM response or LLM error.", 
                    llm_confidence=0.0, llm_warnings=["LLM response parsing failed"],
                    ai_final_response_summary=self.last_ai_response_summary_for_feedback
                )
        except (AttributeError, NameError, ImportError) as e_code_integrity:
            # These errors might indicate an inconsistent state, possibly due to live updates
            logging.error(f"PraxisCore: Potential code integrity issue in process_command_text: {e_code_integrity}", exc_info=True)
            speak("I've encountered a critical internal error, possibly due to a recent system update. Please check the logs. I may need to be restarted.")
            self.last_ai_response_summary_for_feedback = "Critical internal error (possible update issue)."
        except Exception as e:
            logging.error(f"PraxisCore: Critical error in process_command_text: {e}", exc_info=True)
            speak("A critical error occurred while processing your command. Please check the logs.")
            self.last_ai_response_summary_for_feedback = "Critical error in command processing (general)."
        finally:
            if self.current_command_spoken_parts:
                self.last_ai_response_summary_for_feedback = "\n".join(self.current_command_spoken_parts)
            # If last_ai_response_summary_for_feedback is still None or empty after attempting to join,
            # it means no speak calls were made or they were empty.
            # It might have been set by specific error handlers already.
            self._update_gui_status(enable_feedback_buttons=(self.last_interaction_id_for_feedback is not None))

    def _trigger_fallback_handler(self, original_input: str):
        if not self.skill_context: return
        
        prompt_message = "I'm not quite sure how to handle that. Should I try searching the web for you?"
        self.pending_confirmation = {
            "type": "web_search_fallback",
            "original_input": original_input,
            "prompt": prompt_message
        }
        self.skill_context.speak(prompt_message) 
        self.last_ai_response_summary_for_feedback = prompt_message 
        
        self.last_interaction_id_for_feedback = self.kb.log_interaction_details(
            user_name=self.current_user_name, ai_name=self.ai_name, user_input=original_input,
            llm_skill_choice="fallback_confirmation", llm_args_chosen={"original_input": original_input},
            llm_explanation="AI was unsure how to handle the request and asked for web search confirmation.", llm_confidence=0.3, llm_warnings=[],
            ai_final_response_summary=prompt_message
        )
        self._update_gui_status(praxis_state_override="Awaiting Confirmation", confirmation_prompt=prompt_message, enable_feedback_buttons=True)

    def handle_gui_confirmation(self, confirmed: bool):
        if not self.pending_confirmation or not self.skill_context:
            logging.warning("PraxisCore: handle_gui_confirmation called with no pending confirmation.")
            self._update_gui_status(enable_feedback_buttons=(self.last_interaction_id_for_feedback is not None))
            return

        conf_type = self.pending_confirmation.get("type")
        original_input = self.pending_confirmation.get("original_input")
        
        self.pending_confirmation = None 

        if conf_type == "web_search_fallback":
            if confirmed:
                if "web_search" in SKILLS:
                    logging.info(f"PraxisCore: Web search confirmed by GUI for: {original_input}")
                    SKILLS["web_search"](self.skill_context, query=original_input)
                    self.last_ai_response_summary_for_feedback = f"Web search initiated for: {original_input}" 
                else:
                    self.skill_context.speak("The web search skill is not available.")
                    self.last_ai_response_summary_for_feedback = "Web search skill unavailable."
            else:
                logging.info(f"PraxisCore: Web search declined by GUI for: {original_input}")
                self.skill_context.speak("Okay, I won't search the web.")
                self.last_ai_response_summary_for_feedback = "Web search declined."
        
        self.last_interaction_id_for_feedback = self.kb.log_interaction_details(
            user_name=self.current_user_name, ai_name=self.ai_name, user_input=f"Confirmation Response: {'Yes' if confirmed else 'No'}",
            llm_skill_choice=f"confirmation_handler_{conf_type}", llm_args_chosen={"confirmed": confirmed, "original_input": original_input},
            llm_explanation=f"User responded to confirmation prompt for {conf_type}.", llm_confidence=1.0, llm_warnings=[],
            ai_final_response_summary=self.last_ai_response_summary_for_feedback
        )
        self._update_gui_status(enable_feedback_buttons=True)

    def handle_response_feedback(self, is_positive: bool):
        if self.last_interaction_id_for_feedback is not None:
            feedback_type = "positive" if is_positive else "negative"
            self.kb.record_interaction_feedback(self.last_interaction_id_for_feedback, feedback_type)
            speak(f"Thank you for your feedback on my last response, {self.current_user_name}.", from_skill_context=True) 
            self.last_interaction_id_for_feedback = None 
            self._update_gui_status(enable_feedback_buttons=False) 

    def _listen_in_thread(self):
        if not self.recognizer or not self.microphone or not self.skill_context:
            speak("Voice components not ready.")
            self._update_gui_status(enable_feedback_buttons=(self.last_interaction_id_for_feedback is not None)) 
            return

        self._update_gui_status(praxis_state_override="Listening...")
        command_text = listen_for_command(self.recognizer, self.microphone) 

        if self.is_running: 
            if command_text:
                self.process_command_text(command_text)
            else:
                self._update_gui_status(enable_feedback_buttons=(self.last_interaction_id_for_feedback is not None)) 

    def start_voice_input(self) -> None:
        if not (SPEECH_RECOGNITION_AVAILABLE and self.recognizer and self.microphone):
            speak("Voice input is not available on this system.")
            self._update_gui_status(enable_feedback_buttons=(self.last_interaction_id_for_feedback is not None))
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
            self._update_gui_status(enable_feedback_buttons=(self.last_interaction_id_for_feedback is not None)) 

    def toggle_input_mode_core(self, to_mode: Optional[str] = None) -> None:
        if not self.skill_context: return

        effective_sr_available = SPEECH_RECOGNITION_AVAILABLE and bool(self.recognizer and self.microphone)

        if to_mode:
            if to_mode == 'voice' and not effective_sr_available:
                self.skill_context.speak("Cannot switch to voice mode, speech recognition is not available/ready.")
                self._update_gui_status(enable_feedback_buttons=(self.last_interaction_id_for_feedback is not None))
                return
            self.input_mode_config['mode'] = to_mode
        else: 
            if self.input_mode_config['mode'] == 'text':
                if effective_sr_available:
                    self.input_mode_config['mode'] = 'voice'
                else:
                    self.skill_context.speak("Voice input is not available to toggle to.")
                    self._update_gui_status(enable_feedback_buttons=(self.last_interaction_id_for_feedback is not None))
                    return 
            else:
                self.input_mode_config['mode'] = 'text'
        
        self.skill_context.speak(f"Input mode switched to {self.input_mode_config['mode']}.")
        logging.info(f"PraxisCore: Input mode set to {self.input_mode_config['mode']}.")
        self._update_gui_status(enable_feedback_buttons=(self.last_interaction_id_for_feedback is not None))
        
        if self.input_mode_config['mode'] == 'voice' and self.is_running:
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
        self._update_gui_status(enable_feedback_buttons=(self.last_interaction_id_for_feedback is not None)) 
        return self.skill_context.is_muted

    def shutdown(self):
        if self.is_running:
            self.is_running = False 
            
            shutdown_message = f"{self.ai_name} shutting down."
            # Use the global speak function to queue the message
            speak(shutdown_message, from_skill_context=bool(self.skill_context))
            logging.info(f"PraxisCore shutdown initiated. Queued: '{shutdown_message}'")
            self._update_gui_status(praxis_state_override="Shutdown")

            # Signal TTS worker to shut down and wait for it
            global tts_worker_thread_instance
            if TTS_ENGINE_AVAILABLE and engine and tts_worker_thread_instance and tts_worker_thread_instance.is_alive():
                logging.info("PraxisCore: Signaling TTS worker to shutdown...")
                tts_queue.put(TTS_SHUTDOWN_SENTINEL)
                try:
                    # Wait for all items (including the shutdown message and sentinel) to be processed
                    if not tts_queue.empty():
                        logging.info("PraxisCore: Waiting for TTS queue to empty...")
                        tts_queue.join() # This ensures task_done() called for all items
                    logging.info("PraxisCore: TTS queue processed.")
                    # Now wait for the thread to actually terminate
                    tts_worker_thread_instance.join(timeout=5) # Give it a few seconds
                    if tts_worker_thread_instance.is_alive():
                       logging.warning("PraxisCore: TTS worker thread did not terminate cleanly within timeout.")
                    else:
                       logging.info("PraxisCore: TTS worker thread terminated successfully.")
                except Exception as e:
                    logging.error(f"PraxisCore: Error during TTS worker shutdown: {e}", exc_info=True)
            tts_worker_thread_instance = None # Clear the instance

if __name__ == "__main__":
    print(f"{PRAXIS_VERSION_INFO} - main.py executed. To run Praxis with GUI, execute gui.py.")
    pass
