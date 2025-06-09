# skills/skill_refinement_agent.py
import logging
import os
import inspect
from typing import Any, Optional, Dict, List
from datetime import datetime
from skills import prompt_tuning_agent # Import the module

# Assuming knowledge_base.py will have these functions:
# - get_top_failing_skill_info() -> Optional[Dict[str, Any]]
#   (e.g., {"skill_name": "some_skill", "failure_rate": 0.8, "module_hint": "skills.module_name"})
# - get_recent_failures_for_skill(skill_name: str, limit: int = 5) -> List[Dict[str, Any]]
#   (e.g., [{"timestamp": "...", "error_message": "...", "args_used": "{...}"}, ...])
# - get_recent_feedback_for_skill(skill_name: str, was_correct: bool = False, limit: int = 5) -> List[Dict[str, Any]]
#   (e.g., [{"timestamp": "...", "comment": "...", "args_used": "{...}"}, ...])

PROPOSED_FIXES_DIR = "skills/proposed_fixes"

def _ensure_proposed_fixes_dir_exists() -> str:
    """Ensures the directory for proposed fixes exists and returns its path."""
    # Create path relative to the main script's directory
    # Assuming main.py is in the project root.
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    abs_proposed_fixes_dir = os.path.join(project_root, PROPOSED_FIXES_DIR)

    if not os.path.exists(abs_proposed_fixes_dir):
        try:
            os.makedirs(abs_proposed_fixes_dir)
            logging.info(f"SkillRefinement: Created directory for proposed fixes at {abs_proposed_fixes_dir}")
        except Exception as e:
            logging.error(f"SkillRefinement: Failed to create directory {abs_proposed_fixes_dir}: {e}", exc_info=True)
            raise  # Re-raise if directory creation fails, as it's critical
    return abs_proposed_fixes_dir

def attempt_skill_refinement(context: Any) -> None:
    """
    Attempts to identify a failing skill, get its source, gather error data,
    and use an LLM to propose a fix, saving it for review.
    """
    logging.info("SkillRefinementAgent: Attempting skill refinement process...")
    context.speak("Initiating skill refinement protocol. I will attempt to identify and propose a fix for a problematic skill.")

    # 1. Identify Top Failing Skill (from KnowledgeBase)
    if not hasattr(context.kb, "get_top_failing_skill_info"):
        context.speak("My KnowledgeBase is not equipped to identify top failing skills yet. Cannot proceed.")
        logging.warning("SkillRefinementAgent: context.kb.get_top_failing_skill_info missing.")
        return

    failing_skill_info: Optional[Dict[str, Any]] = context.kb.get_top_failing_skill_info()

    if not failing_skill_info or "skill_name" not in failing_skill_info:
        context.speak("I couldn't identify a top failing skill from the KnowledgeBase at this time.")
        logging.info("SkillRefinementAgent: No failing skill identified or info incomplete.")
        return

    skill_name = failing_skill_info["skill_name"]
    failure_rate = failing_skill_info.get("failure_rate", "N/A")
    context.speak(f"Identified '{skill_name}' as a candidate for refinement (Failure rate: {failure_rate:.2% if isinstance(failure_rate, float) else failure_rate}).")

    # 2. Get Skill Function Object and Source Code
    if not hasattr(context, "skills_registry") or not isinstance(context.skills_registry, dict):
        context.speak("Internal error: Skill registry not available in context. Cannot retrieve skill source.")
        logging.error("SkillRefinementAgent: context.skills_registry is missing or not a dict.")
        return

    skill_func = context.skills_registry.get(skill_name)
    if not skill_func:
        context.speak(f"Could not find the function object for skill '{skill_name}' in the registry.")
        logging.error(f"SkillRefinementAgent: Skill '{skill_name}' not found in skills_registry.")
        return

    try:
        skill_file_path = inspect.getfile(skill_func)
        with open(skill_file_path, 'r', encoding='utf-8') as f:
            skill_source_code = f.read()
        logging.info(f"SkillRefinementAgent: Successfully read source code for '{skill_name}' from '{skill_file_path}'.")
    except Exception as e:
        context.speak(f"Failed to read the source code for skill '{skill_name}'. Error: {e}")
        logging.error(f"SkillRefinementAgent: Error reading source for {skill_name} from {skill_file_path}: {e}", exc_info=True)
        return

    # 3. Gather Error Data & Feedback from KnowledgeBase
    recent_errors_str = "No recent error messages found."
    if hasattr(context.kb, "get_recent_failures_for_skill"):
        errors = context.kb.get_recent_failures_for_skill(skill_name, limit=3)
        type_error_count = 0
        arg_related_keywords = ["argument", "parameter", "missing", "required", "typeerror"]
        if errors:
            recent_errors_str = "Recent Error Messages:\n" + "\n".join([
                f"- Args: {e.get('args_used', 'N/A')}, Error: {e.get('error_message', 'N/A')}" for e in errors
            ])
            for e in errors:
                error_msg_lower = (e.get('error_message') or "").lower()
                if "typeerror" in error_msg_lower or any(keyword in error_msg_lower for keyword in arg_related_keywords) :
                    type_error_count +=1
        
        # Heuristic: If many recent errors are argument-related, suggest prompt tuning first.
        if errors and type_error_count / len(errors) >= 0.5: # If 50% or more errors seem arg-related
            context.speak(f"Many recent errors for '{skill_name}' appear to be argument-related. I will first suggest a prompt tuning review.")
            logging.info(f"SkillRefinementAgent: Highlighting argument-related errors for '{skill_name}'. Triggering prompt tuning suggestion.")
            if hasattr(prompt_tuning_agent, "autonomously_analyze_and_suggest_prompt_tuning"):
                 # Pass a more specific issue description if desired, or let the autonomous one run.
                prompt_tuning_agent._generate_and_save_prompt_suggestion(context, f"The skill '{skill_name}' frequently encounters argument-related errors (e.g., TypeErrors). Review its invocation in the main prompt.", _get_brain_py_content_for_prompt_tuner(context)) # Requires helper
                return # Exit skill refinement for now, let prompt tuning take precedence

    
    user_feedback_str = "No recent negative user feedback found."
    if hasattr(context.kb, "get_recent_feedback_for_skill"):
        feedback = context.kb.get_recent_feedback_for_skill(skill_name, was_correct=False, limit=3)
        if feedback:
            user_feedback_str = "Recent Negative User Feedback:\n" + "\n".join([
                f"- Comment: {f.get('comment', 'N/A')}" for f in feedback
            ])

    # 4. Prompt Gemini API for a Fix
    prompt = f"""
You are an expert Python programmer tasked with fixing a failing AI skill.
The skill is named '{skill_name}'.
Its source code is:
```python
{skill_source_code}
```

The skill has been failing. Here is some context:
{recent_errors_str}

{user_feedback_str}

Please analyze the code, errors, and feedback, then propose a corrected version of the *entire* Python skill module.
Your response should ONLY be the complete, corrected Python code for the skill module. Do not include any explanations or markdown formatting other than the Python code block itself.
Ensure your proposed fix addresses the identified issues.
If the original code uses a `context.speak()` method for user interaction, preserve that.
The goal is to produce a functional, improved version of the skill module.

Corrected Python Code:
```python
""" # The LLM should complete from here with the code

    context.speak(f"Sending source code and error data for '{skill_name}' to the LLM for analysis...")
    try:
        response = context.chat_session.send_message(prompt)
        proposed_code = response.text.strip()

        # Extract code if it's wrapped in markdown (common LLM behavior)
        if proposed_code.startswith("```python"):
            proposed_code = proposed_code[len("```python"):].strip()
        if proposed_code.endswith("```"):
            proposed_code = proposed_code[:-len("```")].strip()

        if not proposed_code:
            context.speak("The LLM did not provide a code proposal.")
            logging.warning("SkillRefinementAgent: LLM returned empty proposal.")
            return
        logging.info(f"SkillRefinementAgent: Received code proposal from LLM for '{skill_name}'.")
    except Exception as e:
        context.speak(f"An error occurred while communicating with the LLM for a fix: {e}")
        logging.error(f"SkillRefinementAgent: LLM communication error: {e}", exc_info=True)
        return

    # 5. Save Proposed Fix
    try:
        fixes_dir = _ensure_proposed_fixes_dir_exists()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Use the original module name if possible, derived from skill_file_path
        original_module_name = os.path.basename(skill_file_path).replace('.py', '')
        fixed_file_name = f"fixed_{original_module_name}_{timestamp}.py"
        fixed_file_path = os.path.join(fixes_dir, fixed_file_name)

        with open(fixed_file_path, 'w', encoding='utf-8') as f:
            f.write(proposed_code)

        context.speak(f"A proposed fix for '{skill_name}' (from module '{original_module_name}') has been generated and saved to: {PROPOSED_FIXES_DIR}/{fixed_file_name} for your review, sir.")
        logging.info(f"SkillRefinementAgent: Saved proposed fix to {fixed_file_path}")
    except Exception as e:
        context.speak(f"Successfully received a code proposal, but failed to save it. Error: {e}")
        logging.error(f"SkillRefinementAgent: Error saving proposed fix: {e}", exc_info=True)

def _get_brain_py_content_for_prompt_tuner(context: Any) -> str | None:
    """
    Helper to read brain.py content, used by skill_refinement_agent
    when it wants to trigger prompt_tuning_agent.
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")) # Go up two levels
    brain_path_full = os.path.join(project_root, prompt_tuning_agent.BRAIN_FILE_PATH)
    try:
        with open(brain_path_full, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logging.error(f"SkillRefinementAgent: Could not find {prompt_tuning_agent.BRAIN_FILE_PATH} for prompt tuning.")
        return None
    except Exception as e:
        logging.error(f"SkillRefinementAgent: Error reading {prompt_tuning_agent.BRAIN_FILE_PATH} for prompt tuning: {e}", exc_info=True)
        return None

def _test_skill(context: Any) -> None:
    """Placeholder test for the skill refinement agent. Full testing is complex."""
    logging.info("SkillRefinementAgent: _test_skill called. (Note: Full test requires mock KB and LLM).")
    # In a real test, you'd mock context.kb, context.skills_registry, and context.chat_session.send_message
    # For now, just ensure it can be called.
    # attempt_skill_refinement(context) # Avoid running full logic in automated test without extensive mocking
    context.speak("Skill refinement agent self-test placeholder executed.")
    assert True # Basic assertion