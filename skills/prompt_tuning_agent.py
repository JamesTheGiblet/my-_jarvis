# skills/prompt_tuning_agent.py
import logging
import os
from typing import Any
import json # Added for parsing LLM's structured response
from datetime import datetime

PROPOSED_PROMPT_CHANGES_DIR = "skills/proposed_prompt_changes"
BRAIN_FILE_PATH = "brain.py" # Relative to the project root

def _ensure_proposed_prompt_changes_dir_exists() -> str:
    """Ensures the directory for proposed prompt changes exists and returns its path."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    abs_proposed_changes_dir = os.path.join(project_root, PROPOSED_PROMPT_CHANGES_DIR)

    if not os.path.exists(abs_proposed_changes_dir):
        try:
            os.makedirs(abs_proposed_changes_dir)
            logging.info(f"PromptTuningAgent: Created directory for proposed prompt changes at {abs_proposed_changes_dir}")
        except Exception as e:
            logging.error(f"PromptTuningAgent: Failed to create directory {abs_proposed_changes_dir}: {e}", exc_info=True)
            raise
    return abs_proposed_changes_dir

def _get_brain_py_content(context: Any) -> str | None:
    """
    Reads and returns the content of brain.py.
    Returns None if there's an error.
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    brain_path_full = os.path.join(project_root, BRAIN_FILE_PATH)
    try:
        with open(brain_path_full, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        context.speak(f"I'm sorry, I couldn't find my core logic file ({BRAIN_FILE_PATH}) to analyze.")
        logging.error(f"PromptTuningAgent: {BRAIN_FILE_PATH} not found at {brain_path_full}.")
        return None
    except Exception as e:
        context.speak(f"I encountered an error trying to read my core logic file: {e}")
        logging.error(f"PromptTuningAgent: Error reading {BRAIN_FILE_PATH}: {e}", exc_info=True)
        return None

def _generate_and_save_prompt_suggestion(context: Any, issue_description: str, brain_py_content: str) -> None:
    """
    Uses the LLM to generate granular prompt suggestions based on an issue
    and saves them for developer review.
    """
    if context.is_muted: # Cannot get real input during muted test
        logging.info(f"PromptTuningAgent (Muted Test): Generating suggestion for issue: {issue_description}")

    prompt_for_llm = f"""
You are an expert in prompt engineering for AI assistants.
The AI assistant, Praxis, uses the Python code below in its `brain.py` file.
The key part for command processing is the `prompt` variable inside the `process_command_with_llm` function.

Current `brain.py` content:
```python
{brain_py_content}
```

The user has observed the following issue with how Praxis processes commands:
"{issue_description}"

Your task is to analyze the `prompt` variable within the `process_command_with_llm` function in the provided `brain.py` code.
Then, suggest modifications ONLY to the static text portions of this `prompt` variable to address the described issue.
Do NOT modify the f-string variable placeholders like `{{available_skills_prompt_str}}` or `{{command}}` themselves, but you can change the text that introduces or explains them to the LLM.

Your response should be the *complete, modified content of the brain.py file*, with your suggested changes integrated into the `prompt` string.
Enclose your entire response in a single Python code block.
"""

    context.speak("Consulting the generative core for prompt refinement suggestions...")
    try:
        response = context.chat_session.send_message(prompt_for_llm)
        proposed_brain_py_content = response.text.strip()

        if proposed_brain_py_content.startswith("```python"):
            proposed_brain_py_content = proposed_brain_py_content[len("```python"):].strip()
        if proposed_brain_py_content.endswith("```"):
            proposed_brain_py_content = proposed_brain_py_content[:-len("```")].strip()

        if not proposed_brain_py_content or "def process_command_with_llm(" not in proposed_brain_py_content:
            context.speak("The generative core did not provide a recognizable `brain.py` structure. No changes suggested.")
            logging.warning(f"PromptTuningAgent: LLM returned empty or invalid brain.py proposal. Start of proposal: {proposed_brain_py_content[:200]}")
            return

        changes_dir = _ensure_proposed_prompt_changes_dir_exists()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suggestion_file_name = f"brain_prompt_suggestion_{timestamp}.py"
        suggestion_file_path = os.path.join(changes_dir, suggestion_file_name)

        with open(suggestion_file_path, 'w', encoding='utf-8') as f:
            f.write(f"# Proposed brain.py prompt changes by Praxis on {datetime.now().isoformat()}\n")
            f.write(f"# User-described issue: {issue_description}\n\n")
            f.write(proposed_brain_py_content)

        context.speak(f"I have drafted a suggestion for improving the `brain.py` prompt. It has been saved to: {PROPOSED_PROMPT_CHANGES_DIR}/{suggestion_file_name} for your review, sir.")
        logging.info(f"PromptTuningAgent: Saved proposed `brain.py` changes to {suggestion_file_path}")

    except Exception as e:
        context.speak(f"An error occurred while generating or saving prompt improvement suggestions: {e}")
        logging.error(f"PromptTuningAgent: Error during LLM interaction or file saving: {e}", exc_info=True)

def _test_skill(context: Any) -> None:
    """Placeholder test for the prompt tuning agent skill."""
    logging.info("PromptTuningAgent: _test_skill called. (Note: Full test requires mock LLM, user input, and file system interaction).")
    context.speak("Prompt tuning agent self-test placeholder executed.")
    assert True