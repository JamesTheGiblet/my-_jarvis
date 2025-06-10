# brain.py
import json
import logging # Added logging
import re
from typing import Optional, Dict, Any, TYPE_CHECKING, Tuple

import google.generativeai as genai # For model type hint
from google.generativeai.types import generation_types # For specific exceptions

if TYPE_CHECKING: # To avoid circular import for type hinting
    from google.generativeai.generative_models import ChatSession # type: ignore
    from google.generativeai import GenerativeModel # For type hint

def strip_wake_words(command: str) -> tuple[str, bool]:
    """
    Removes wake words from the command.
    Returns the processed command and a boolean indicating if a wake word was stripped.
    """
    wake_words = ["codex", "hey codex", "okay codex", "jarvis", "praxis", "hey praxis", "okay praxis"]
    command_lower = command.lower() # For case-insensitive matching of wake word
    
    for wake in wake_words:
        if command_lower.startswith(wake):
            # Wake word found. Return the part of the *original* command after the wake word.
            actual_command_part = command[len(wake):].strip()
            return actual_command_part, True
            
    return command.strip(), False # No wake word found, return original command (stripped of outer whitespace)

def extract_json(text: str) -> Optional[Dict[str, Any]]:
    """Extracts a JSON object from a string."""
    try:
        # Use a more robust regex to find json block
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except json.JSONDecodeError:
        # Log the warning
        logging.warning("Praxis Brain Warning: Failed to decode JSON from LLM response. Text was: %s", text)
        return None
    return None

def process_command_with_llm(
    command: str, 
    chat_session: 'ChatSession', 
    available_skills_prompt_str: str,
    ai_name: str = "Praxis",
    model: Optional['GenerativeModel'] = None # Added model parameter for token counting
) -> Tuple[Optional[Dict[str, Any]], int, int]: # Return type changed to include token counts
    """Uses the Gemini LLM to understand the user's command and returns a skill dictionary."""
    # The AI's persona name in the prompt, aligning with the project name "Praxis"
    # The persona description is enriched by the project's guiding principles and vision from the README.md.
    prompt = f"""
        You are {ai_name}, a J.A.R.V.I.S.-like AI assistant.
        Your architecture is modular, built upon a set of specialized skills. Your primary function is to intelligently orchestrate these skills to assist the user effectively.
        You are designed to be adaptable, context-aware, and to learn from interactions.

        Analyze the user's latest request based on the conversation history.
        Your goal is to understand the user's intent and select the best tool (skill) to fulfill it, or to respond conversationally with the 'speak' skill if appropriate.
        If a task requires multiple steps, plan these steps. After a tool provides information,
        you can use that information from the conversation history to inform a subsequent tool call.

        {available_skills_prompt_str}

        If the request is purely conversational (e.g., a greeting, a simple question like "how are you?", or a statement like "that's interesting"), respond with skill 'speak'.
        When using the 'speak' skill, provide the conversational response in the 'text' argument.

        SPECIFIC INSTRUCTIONS FOR INPUT MODE:
        - If the user explicitly asks to "switch to text input", "use text mode", "type commands", or similar phrases indicating a desire for text-based interaction, you MUST use the "set_input_mode_text" skill.
          Example: User says "let's switch to text input" -> {{"skill": "set_input_mode_text", "args": {{}}}}
        - If the user explicitly asks to "switch to voice input", "use voice mode", "let's talk", "speech input", "listen to me", or similar phrases indicating a desire for voice-based interaction, you MUST use the "set_input_mode_voice" skill.
          Example: User says "switch to speech input" -> {{"skill": "set_input_mode_voice", "args": {{}}}}
        Do NOT use the 'speak' skill to merely announce that the mode is changing if the intent is to actually change the mode. The respective skills ("set_input_mode_text", "set_input_mode_voice") will handle the necessary announcements.

        Respond ONLY in a single, clean JSON format like:
        {{
            "skill": "web_search",
            "args": {{
                "query": "weather in London"
            }}
        }}
        Or for a conversational reply:
        {{
            "skill": "speak",
            "args": {{
                "text": "You're welcome, sir!"
            }}
        }}
        Or for asking and storing a profile item:
        {{
            "skill": "ask_and_store_profile_item",
            "args": {{
                "question_to_ask": "Understood. To confirm, you enjoy gardening. What specific aspect of gardening do you like most, or should I just note 'gardening' as a general interest?",
                "item_category": "interest",
                "item_key": "hobby_gardening"
            }}
        }}
        Or for directly recording a user profile item:
        {{
            "skill": "record_user_profile_item",
            "args": {{
                "item_category": "interest",
                "item_key": "hobby",
                "item_value": "gardening"
            }}
        }}
        
        User's latest request: "{command}"

        JSON Response:
    """

    # Note: Rate limits for the model are defined in config.py (e.g., GEMINI_1_5_FLASH_RPM, GEMINI_1_5_FLASH_TPM).
    # If client-side rate limiting is needed, logic would be added here or in the calling function (PraxisCore)
    # before sending the message.
    try:
        prompt_tokens = 0
        response_tokens = 0

        if model:
            try:
                prompt_tokens = model.count_tokens(prompt).total_tokens
            except Exception as e:
                logging.error(f"Praxis LLM Brain Error counting prompt tokens: {e}", exc_info=True)
                # Proceed, prompt_tokens will be 0. API call might still work or fail.

        response = chat_session.send_message(prompt)

        if response.prompt_feedback and response.prompt_feedback.block_reason:
            logging.error(f"Praxis LLM Brain: Prompt blocked by API. Reason: {response.prompt_feedback.block_reason}, Category: {response.prompt_feedback.safety_ratings}")
            return None, prompt_tokens, 0 # No response tokens

        if model and response.text:
            try:
                response_tokens = model.count_tokens(response.text).total_tokens
            except Exception as e:
                logging.error(f"Praxis LLM Brain Error counting response tokens: {e}", exc_info=True)
                # response_tokens remains 0

        parsed_json = extract_json(response.text)
        return parsed_json, prompt_tokens, response_tokens

    except generation_types.BlockedPromptException as bpe:
        logging.error(f"Praxis LLM Brain Error: Prompt was blocked by the API. {bpe}", exc_info=True)
        return None, prompt_tokens, 0 # We have prompt tokens (if counted), no response tokens
    except generation_types.StopCandidateException as sce:
         logging.error(f"Praxis LLM Brain Error: Generation stopped unexpectedly. {sce}", exc_info=True)
         partial_text = ""
         if sce.candidates and sce.candidates[0].content and sce.candidates[0].content.parts:
             partial_text = "".join(part.text for part in sce.candidates[0].content.parts if hasattr(part, 'text'))
         if model and partial_text:
             try:
                 response_tokens = model.count_tokens(partial_text).total_tokens
             except Exception: # nosec
                 pass # response_tokens remains 0
         return None, prompt_tokens, response_tokens
    except Exception as e:
        logging.error(f"Praxis LLM Brain Error during send_message or extract_json: {e}", exc_info=True)
        # If prompt_tokens was calculated, it's preserved. response_tokens defaults to 0 here.
        return None, prompt_tokens if 'prompt_tokens' in locals() else 0, 0
