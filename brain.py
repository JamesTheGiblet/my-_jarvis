# brain.py
import json
import re
from typing import Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING: # To avoid circular import for type hinting
    from google.generativeai.generative_models import ChatSession # type: ignore

def strip_wake_words(command: str) -> str:
    """Removes wake words from the command."""
    wake_words = ["codex", "hey codex", "okay codex", "jarvis", "praxis", "hey praxis", "okay praxis"]
    processed_command = command.lower()
    for wake in wake_words:
        if processed_command.startswith(wake):
            processed_command = processed_command[len(wake):].strip()
            break  # Remove only the first occurrence of a wake word phrase
    return processed_command.strip()

def extract_json(text: str) -> Optional[Dict[str, Any]]:
    """Extracts a JSON object from a string."""
    try:
        # Use a more robust regex to find json block
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except json.JSONDecodeError:
        # Consider logging this instead of printing, or in addition to printing
        print("Praxis Brain Warning: Failed to decode JSON from LLM response.")
        return None
    return None

def process_command_with_llm(
    command: str, 
    chat_session: 'ChatSession', 
    available_skills_prompt_str: str  # New argument
) -> Optional[Dict[str, Any]]:
    """Uses the Gemini LLM to understand the user's command and returns a skill dictionary."""
    # The AI's persona name in the prompt, aligning with the project name "Praxis"
    # The persona description is enriched by the project's guiding principles and vision from the README.md.
    prompt = f"""
        You are Praxis, a J.A.R.V.I.S.-like AI assistant.
        Your architecture is modular, built upon a set of specialized skills. Your primary function is to intelligently orchestrate these skills to assist the user effectively.
        You are designed to be adaptable, context-aware, and to learn from interactions.

        Analyze the user's latest request based on the conversation history.
        Your goal is to understand the user's intent and select the best tool (skill) to fulfill it, or to respond conversationally with the 'speak' skill if appropriate.
        If a task requires multiple steps, plan these steps. After a tool provides information,
        you can use that information from the conversation history to inform a subsequent tool call.

        - calculate_multiply: Multiplies two numbers. Requires 'number1' (float) and 'number2' (float) arguments.
        {available_skills_prompt_str}

        If the request is conversational (e.g., a greeting), respond with skill 'speak'.
        When using the 'speak' skill, provide the conversational response in the 'text' argument.

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
        
        User's latest request: "{command}"

        JSON Response:
    """

    try:
        response = chat_session.send_message(prompt)
        return extract_json(response.text)
    except Exception as e:
        print(f"Praxis LLM Brain Error: {e}") # Consider logging this error as well
        return None
