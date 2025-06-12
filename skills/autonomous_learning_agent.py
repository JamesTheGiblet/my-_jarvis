# skills/autonomous_learning_agent.py
import logging
import os
import random
import re # Import the re module for string manipulation
from typing import Any, Optional
from datetime import datetime

PROPOSED_NEW_SKILLS_DIR = "skills/proposed_new_skills"

def _ensure_proposed_new_skills_dir_exists() -> str:
    """Ensures the directory for proposed new skills exists and returns its path."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    abs_proposed_new_skills_dir = os.path.join(project_root, PROPOSED_NEW_SKILLS_DIR)

    if not os.path.exists(abs_proposed_new_skills_dir):
        try:
            os.makedirs(abs_proposed_new_skills_dir)
            logging.info(f"AutonomousLearningAgent: Created directory for proposed new skills at {abs_proposed_new_skills_dir}")
        except Exception as e:
            logging.error(f"AutonomousLearningAgent: Failed to create directory {abs_proposed_new_skills_dir}: {e}", exc_info=True)
            raise
    return abs_proposed_new_skills_dir

def _generate_skill_name_from_description(description: str) -> str:
    """Generates a Python-friendly skill name from a task description."""
    # Remove common leading phrases
    description = re.sub(r"^(a skill to|a skill that can|a skill for|create a skill to|develop a skill that can)\s+", "", description, flags=re.IGNORECASE).strip()
    
    # Take first few words (e.g., up to 5) to form the base name
    words = description.split()[:5]
    if not words:
        return "generic_learned_skill" # Fallback if description was empty or only leading phrases
    
    # Sanitize: lowercase, replace non-alphanumeric with underscore
    name_parts = [re.sub(r'\W+', '', word).lower() for word in words]
    # Filter out empty strings that might result from sanitizing non-alphanumeric words
    name_parts = [part for part in name_parts if part]
    
    if not name_parts: # If all words were non-alphanumeric
        return "generic_learned_skill"

    skill_name = "_".join(name_parts)
    
    # Ensure it's a valid Python identifier (starts with letter or underscore)
    if not re.match(r"^[a-zA-Z_]", skill_name):
        skill_name = "skill_" + skill_name # Prepend "skill_" if it doesn't start correctly
    return skill_name

def attempt_autonomous_skill_learning(context: Any, task_description: Optional[str] = None) -> None:
    """
    Attempts to autonomously learn/generate a new skill based on a task description
    or a predefined simple task if none is provided.
    The generated skill is saved for developer review.
    """
    logging.info("AutonomousLearningAgent: Initiating new skill learning protocol...")
    context.speak("I will now attempt to conceptualize and draft a new skill. This is an experimental procedure, sir.")

    # Determine the skill name suggestion and final task description
    if not task_description:
        possible_tasks = [
            ("a skill to greet the user differently based on the time of day (morning, afternoon, evening)", "greet_by_time_of_day"),
            ("a skill that tells a very short, one-line motivational quote", "get_motivational_quote"),
            ("a skill that can reverse a given string", "reverse_string_content"),
            ("a skill to calculate the factorial of a number", "calculate_factorial"),
            ("Create a skill to set an alarm. The skill should take as input the time for the alarm (in HH:MM format), and optionally a description or label for the alarm.  It should then store the alarm information, and ideally, at the specified time, trigger a notification or other action (this latter part might require system integration beyond the scope of this immediate task).", "set_alarm")
        ]
        chosen_task = random.choice(possible_tasks)
        task_description = chosen_task[0]
        skill_name_suggestion = chosen_task[1] # Use the curated, specific name
        logging.info(f"AutonomousLearningAgent: No task provided, selected predefined task: '{task_description}' with suggested name: '{skill_name_suggestion}'")
    else:
        # A specific task_description was provided by the caller
        skill_name_suggestion = _generate_skill_name_from_description(task_description)
        logging.info(f"AutonomousLearningAgent: Task description provided. Generated skill name suggestion: '{skill_name_suggestion}' for task: '{task_description}'")

    context.speak(f"I will try to conceptualize a skill for the following task: {task_description}")

    prompt_for_llm = f"""
You are an expert Python programmer assisting an AI named Praxis. Praxis needs a new skill.
Your task is to generate the complete Python code for a new skill module.

The skill should accomplish: {task_description}

The skill module MUST:
1.  Be a single Python file.
2.  Contain one primary public function for the skill. This function:
    *   Should be named '{skill_name_suggestion}'.
    *   Must accept `context: Any` as its first argument. `context` has a method `context.speak(str)` for user interaction and `context.current_user_name` for the user's name.
    *   Should have a clear docstring explaining what it does and its arguments (if any, besides context).
    *   Should handle its own logic and use `context.speak()` to communicate results or messages to the user.
3.  The skill function can take other simple arguments (strings, numbers, booleans) if the task implies them (e.g., a string to reverse, a number for factorial). Define these clearly in the docstring.
4.  The module MUST also include a `_test_skill(context: Any)` function. This function:
    *   Should contain basic assertions or calls to the main skill function to verify its core functionality.
    *   Should use `context.speak()` for any output during the test (it will be muted and logged by Praxis).
    *   Should use `logging.info()` for test steps.
5.  The module can import standard Python libraries like `datetime`, `random`, `math`, `json`, `os`, `logging`. Do NOT rely on external libraries that aren't part of a standard Python install unless explicitly part of the task.
6.  The generated code should be self-contained within the response.

Your response should ONLY be the complete Python code for the skill module, enclosed in a single Python code block, starting with '# skills/{skill_name_suggestion}_module.py' (replace with actual name) as a comment.
```python
# skills/{skill_name_suggestion}_module.py
# (Generated by Praxis Autonomous Learning Agent)

# ... rest of the Python code for the new skill module ...
```
"""

    context.speak("Consulting the generative core to draft the new skill module...")
    try:
        response = context.chat_session.send_message(prompt_for_llm)
        proposed_code = response.text.strip()

        if proposed_code.startswith("```python"):
            proposed_code = proposed_code[len("```python"):].strip()
        if proposed_code.endswith("```"):
            proposed_code = proposed_code[:-len("```")].strip()

        if not proposed_code or not (f"def {skill_name_suggestion}(" in proposed_code and "context: Any" in proposed_code):
            context.speak("The generative core did not provide a recognizable code structure for the new skill.")
            logging.warning(f"AutonomousLearningAgent: LLM returned empty or invalid code proposal for {skill_name_suggestion}. Proposal: {proposed_code[:500]}")
            return
        logging.info(f"AutonomousLearningAgent: Received code proposal from LLM for task: {task_description}")

    except Exception as e:
        context.speak(f"An error occurred while communicating with the generative core: {e}")
        logging.error(f"AutonomousLearningAgent: LLM communication error: {e}", exc_info=True)
        return

    try:
        new_skills_dir = _ensure_proposed_new_skills_dir_exists()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_skill_file_name = f"{skill_name_suggestion}_{timestamp}.py"
        new_skill_file_path = os.path.join(new_skills_dir, new_skill_file_name)

        with open(new_skill_file_path, 'w', encoding='utf-8') as f:
            f.write(f"# Proposed new skill generated by Praxis on {datetime.now().isoformat()}\n")
            f.write(f"# Task: {task_description}\n\n")
            f.write(proposed_code)

        context.speak(f"I have drafted a new skill module for '{skill_name_suggestion}'. It has been saved to: {PROPOSED_NEW_SKILLS_DIR}/{new_skill_file_name} for your review and integration, sir.")
        logging.info(f"AutonomousLearningAgent: Saved proposed new skill to {new_skill_file_path}")

    except Exception as e:
        context.speak(f"I received a code proposal, but failed to save it. Error: {e}")
        logging.error(f"AutonomousLearningAgent: Error saving proposed new skill: {e}", exc_info=True)

def _test_skill(context: Any) -> None:
    """Placeholder test for the autonomous learning agent skill."""
    logging.info("AutonomousLearningAgent: _test_skill called. (Note: Full test requires mock LLM and file system interaction).")
    context.speak("Autonomous learning agent self-test placeholder executed.")
    assert True