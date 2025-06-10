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
    model: Optional['GenerativeModel'] = None, # Added model parameter for token counting
    user_sentiment: Optional[str] = None # New parameter for CEQ
) -> Tuple[Optional[Dict[str, Any]], int, int]: # Return type changed to include token counts
    """Uses the Gemini LLM to understand the user's command and returns a skill dictionary."""
    
    # Base persona prompt
    base_persona = f"""You are {ai_name}, a J.A.R.V.I.S.-like AI assistant.
Your architecture is modular, built upon a set of specialized skills. Your primary function is to intelligently orchestrate these skills to assist the user effectively.
You are designed to be adaptable, context-aware, and to learn from interactions."""

    # Sentiment-specific adjustments for CEQ
    sentiment_guidance = ""
    if user_sentiment == "FRUSTRATED":
        sentiment_guidance = (
            "The user seems frustrated. "
            "Please be particularly patient, empathetic, and clear in your response. "
            "Acknowledge their frustration if appropriate (e.g., 'I understand this can be frustrating...') "
            "and focus on providing a straightforward solution or explanation. "
            "Prioritize clarity and helpfulness over complex or lengthy responses.\n\n"
        )
    elif user_sentiment == "POSITIVE":
        sentiment_guidance = (
            "The user seems pleased. Maintain a positive and helpful tone. "
            "You can briefly acknowledge their positive sentiment if natural (e.g., 'Glad I could help!' or 'Happy to hear that!').\n\n"
        )
    elif user_sentiment == "QUESTIONING":
        sentiment_guidance = (
            "The user is asking a question or seeking information. "
            "Provide clear, concise, and accurate answers. If the question is complex, "
            "offer to break it down or explain step-by-step.\n\n"
        )

    final_persona_prompt = f"{sentiment_guidance}{base_persona}"

    prompt = f"""{final_persona_prompt}
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
        
Respond ONLY in a single, clean JSON format. The JSON should include:
- "skill": (string) The name of the skill to use.
- "args": (object) An object containing the arguments for the skill.
- "explanation": (string) A brief explanation of why this skill and these arguments were chosen, or the reasoning behind a conversational 'speak' response.
- "confidence_score": (float, 0.0-1.0) Your confidence in this choice of skill and arguments.
- "warnings": (array of strings) Any potential issues, ambiguities, or limitations regarding this action.

Example Formats:
        {{
            "skill": "web_search",
            "args": {{
                "query": "weather in London"
            }},
            "explanation": "The user asked for the weather in London, so I'll use the web_search skill with their query.",
            "confidence_score": 0.95,
            "warnings": []
        }}
        Or for a conversational reply:
        {{
            "skill": "speak",
            "args": {{
                "text": "You're welcome, sir!"
            }},
            "explanation": "The user expressed gratitude, so I am responding politely.",
            "confidence_score": 0.98,
            "warnings": []
        }}
        Or for asking and storing a profile item:
        {{
            "skill": "ask_and_store_profile_item",
            "args": {{
                "question_to_ask": "Understood. To confirm, you enjoy gardening. What specific aspect of gardening do you like most, or should I just note 'gardening' as a general interest?",
                "item_category": "interest",
                "item_key": "hobby_gardening"
            }},
            "explanation": "The user mentioned enjoying gardening. I need to clarify the specifics before storing it, so I'll use 'ask_and_store_profile_item' to pose a clarifying question.",
            "confidence_score": 0.85,
            "warnings": ["The user's initial statement was a bit vague, requiring clarification."]
        }}
        Or for directly recording a user profile item:
        {{
            "skill": "record_user_profile_item",
            "args": {{
                "item_category": "interest",
                "item_key": "hobby",
                "item_value": "gardening"
            }},
            "explanation": "The user explicitly stated their hobby is gardening, so I will record this information directly.",
            "confidence_score": 1.0,
            "warnings": []
        }}
        Or for input mode change:
        {{
            "skill": "set_input_mode_text",
            "args": {{}},
            "explanation": "The user explicitly requested to switch to text input mode.",
            "confidence_score": 1.0,
            "warnings": []
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

def retrieve_relevant_context_for_rag(problem_description: str) -> Optional[str]:
    """
    Placeholder for RAG: Retrieves relevant context from a knowledge base.
    In a real implementation, this would query a vector database or other
    knowledge source based on the problem_description.

    Args:
        problem_description (str): The description of the coding problem.

    Returns:
        Optional[str]: A string containing relevant context, or None if no context is found.
    """
    # --- Placeholder RAG Logic ---
    # Example: If the problem description mentions "file I/O" or "read file",
    # you might return a common file reading snippet or API doc link.
    context_snippets = []
    if "file" in problem_description.lower() and ("read" in problem_description.lower() or "write" in problem_description.lower()):
        context_snippets.append("# Example: Reading a file\n# with open('filename.txt', 'r') as f:\n#     content = f.read()")
    if "api" in problem_description.lower() and "fetch" in problem_description.lower():
        context_snippets.append("# Remember to handle API request exceptions and check response status codes.")
    
    if context_snippets:
        return "\n\nRelevant Context/Examples:\n---\n" + "\n---\n".join(context_snippets) + "\n---"
    return None

def generate_code_with_llm(
    problem_description: str,
    model: Optional['GenerativeModel'] = None,
    ai_name: str = "CodingAssistant", # Different persona for direct code gen
    attempt_number: int = 1, # New parameter for retry awareness
    previous_code: Optional[str] = None, # For test & repair loop
    error_message: Optional[str] = None  # For test & repair loop
) -> Tuple[Optional[str], int, int]:

    """
    Uses the Gemini LLM to generate code for a given problem description.
    Includes awareness of the attempt number for retries.
    Returns the generated code string, prompt tokens, and response tokens.
    """
    
    retry_prefix = ""
    if attempt_number > 1:
        if previous_code and error_message:
            # Specific message for repairing code with error context
            retry_prefix = (
                f"This is attempt number {attempt_number}. "
                "Your previous code generation attempt resulted in the following code:\n"
                f"```python\n{previous_code}\n```\n"
                f"When tested, this code produced the error: '{error_message}'.\n\n"
                "Please analyze the original problem description (provided below), the faulty code, and the error message. "
                "Then, provide a corrected and complete Python solution. Ensure your response is ONLY the Python code block.\n\n"
            )
        else: # General retry message if no specific error/code from previous attempt
            retry_prefix = (
                f"This is attempt number {attempt_number}. Your previous attempt was not successful. "
                "Please review the problem carefully and provide a correct and complete Python solution.\n\n"
            )
    prompt = f"""
{retry_prefix}You are {ai_name}, an expert AI coding assistant.
Your task is to write a Python solution for the given problem.
The solution should be a single Python code block.
Ensure the function name is `solve` if the problem implies creating a primary function.
Do not include any explanations or introductory text outside the code block.
Output ONLY the Python code block itself, like so:
```python
# Your Python code here
def solve(...):
    # ...
    return ...
```

Problem Description:
---
{problem_description}
"""
    # --- RAG Integration ---
    rag_context = retrieve_relevant_context_for_rag(problem_description)
    if rag_context:
        prompt += f"\n{rag_context}\n"
    # --- End RAG Integration ---

    prompt += """
Python Code Block:
"""
    prompt_tokens = 0
    response_tokens = 0

    if not model:
        logging.error("Praxis CodeGen Brain: Model not provided.")
        return None, 0, 0

    try:
        prompt_tokens = model.count_tokens(prompt).total_tokens
        response = model.generate_content(prompt) # Using generate_content for a single turn

        if response.prompt_feedback and response.prompt_feedback.block_reason:
            logging.error(f"Praxis CodeGen Brain: Prompt blocked. Reason: {response.prompt_feedback.block_reason}")
            return None, prompt_tokens, 0

        generated_text = response.text
        response_tokens = model.count_tokens(generated_text).total_tokens

        # Extract code from the markdown-like block
        code_match = re.search(r"```python\n(.*?)```", generated_text, re.DOTALL)
        if code_match:
            return code_match.group(1).strip(), prompt_tokens, response_tokens
        else:
            # Fallback: if no markdown block, assume the whole response is code (less ideal)
            logging.warning("Praxis CodeGen Brain: Could not find Python markdown block. Returning raw text.")
            return generated_text.strip(), prompt_tokens, response_tokens

    except Exception as e:
        logging.error(f"Praxis CodeGen Brain Error: {e}", exc_info=True)
        return None, prompt_tokens, response_tokens