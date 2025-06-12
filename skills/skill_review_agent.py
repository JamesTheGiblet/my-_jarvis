# skills/skill_review_agent.py
import logging
import os
import importlib.util
import sys
import traceback # For detailed error reporting
from typing import Any, Optional, List

# This is the subdirectory within 'skills' where new skills are placed.
PROPOSED_NEW_SKILLS_SUBDIR = "proposed_new_skills"

def _get_proposed_skills_dir_path() -> str:
    """Gets the absolute path to the 'proposed_new_skills' directory."""
    # This skill file (skill_review_agent.py) is in the 'skills' directory.
    # The 'proposed_new_skills' directory is a subdirectory of 'skills'.
    current_skill_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_skill_dir, PROPOSED_NEW_SKILLS_SUBDIR)

def _ensure_proposed_skills_package_init() -> None:
    """Ensures __init__.py exists in proposed_new_skills to make it a package."""
    proposed_dir = _get_proposed_skills_dir_path()
    os.makedirs(proposed_dir, exist_ok=True) # Ensure directory exists
    init_path = os.path.join(proposed_dir, "__init__.py")
    if not os.path.exists(init_path):
        try:
            with open(init_path, 'w') as f:
                f.write("# This file makes 'proposed_new_skills' a package.\n")
            logging.info(f"SkillReviewAgent: Created __init__.py in {proposed_dir}")
        except Exception as e:
            logging.warning(f"SkillReviewAgent: Could not create __init__.py in {proposed_dir}: {e}")


def list_proposed_skills(context: Any) -> None:
    """Lists the Python files in the proposed_new_skills directory."""
    proposed_dir = _get_proposed_skills_dir_path()
    if not os.path.isdir(proposed_dir):
        context.speak(f"The directory for proposed skills ('{PROPOSED_NEW_SKILLS_SUBDIR}') does not seem to exist.")
        logging.warning(f"SkillReviewAgent: Proposed skills directory not found at {proposed_dir}")
        return

    try:
        files = [f for f in os.listdir(proposed_dir) if f.endswith(".py") and not f.startswith("__")]
        if not files:
            context.speak("There are currently no new skills proposed for review.")
        else:
            context.speak("The following new skills are proposed for review:")
            for f_name in files:
                context.speak(f"- {f_name}")
            context.speak("You can ask me to 'review and test proposed skill <filename>'.")
    except Exception as e:
        context.speak(f"I encountered an error while trying to list the proposed skills: {e}")
        logging.error(f"SkillReviewAgent: Error listing proposed skills: {e}", exc_info=True)


def review_and_test_proposed_skill(context: Any, skill_filename: str) -> None:
    """
    Dynamically loads and tests a specified proposed skill.
    Args:
        context: The skill context.
        skill_filename (str): The filename of the proposed skill (e.g., 'my_new_skill_yyyymmdd_hhmmss.py').
    """
    if not skill_filename.endswith(".py"):
        context.speak("Please provide a valid Python filename for the skill to review.")
        return

    _ensure_proposed_skills_package_init() # Ensure the directory is a package

    proposed_dir = _get_proposed_skills_dir_path()
    full_skill_path = os.path.join(proposed_dir, skill_filename)

    if not os.path.isfile(full_skill_path):
        context.speak(f"I could not find the skill file '{skill_filename}' in the proposed skills directory.")
        logging.warning(f"SkillReviewAgent: Proposed skill file not found: {full_skill_path}")
        return

    context.speak(f"Attempting to review and test proposed skill: {skill_filename}")
    logging.info(f"SkillReviewAgent: Starting review for {full_skill_path}")

    # Derive a unique module name for import, making it part of the 'skills.proposed_new_skills' package
    module_name_for_import = f"skills.{PROPOSED_NEW_SKILLS_SUBDIR}.{skill_filename[:-3]}"

    # This function (review_and_test_proposed_skill) is often called from _test_skill of SkillReviewAgent itself.
    # The 'context' here is SkillReviewAgent's context.
    # We need to manage its mute state carefully.
    # 1. The proposed skill's _test_skill should run with context.is_muted = True,
    #    so its output is captured in context.spoken_messages_during_mute.
    # 2. After the proposed skill's test, we copy its output and clear the buffer.
    # 3. Then, this function (review_and_test_proposed_skill) speaks its own summary.
    #    These summary speaks should also be captured if the calling context (e.g., SkillReviewAgent._test_skill)
    #    has set context.is_muted = True.
    original_caller_mute_state = context.is_muted # Save the mute state set by the caller

    # For the duration of the proposed skill's test execution, ensure context is muted to capture its output.
    context.is_muted = True
    context.clear_spoken_messages_for_test() # Clear buffer for the proposed skill's output

    test_passed = False
    error_details = ""
    proposed_skill_module = None
    proposed_skill_test_output: List[str] = []

    try:
        spec = importlib.util.spec_from_file_location(module_name_for_import, full_skill_path)
        if spec is None or spec.loader is None:
            error_details = "Could not create module spec (is it a valid Python file or does the path exist?)."
            logging.error(f"SkillReviewAgent: Failed to create spec for {full_skill_path} with name {module_name_for_import}")
            raise ImportError(error_details)

        proposed_skill_module = importlib.util.module_from_spec(spec)
        # Add to sys.modules *before* execution to handle circular dependencies or imports within the module itself.
        sys.modules[module_name_for_import] = proposed_skill_module
        
        spec.loader.exec_module(proposed_skill_module)
        logging.info(f"SkillReviewAgent: Successfully imported module {module_name_for_import}")

        if not hasattr(proposed_skill_module, "_test_skill"):
            error_details = "The proposed skill module does not have a '_test_skill' function."
            logging.warning(f"SkillReviewAgent: _test_skill not found in {module_name_for_import}")
        else:
            test_function = getattr(proposed_skill_module, "_test_skill")
            logging.info(f"SkillReviewAgent: Found _test_skill in {module_name_for_import}. Running test...")
            test_function(context) # Pass the main skill's context
            test_passed = True 
            logging.info(f"SkillReviewAgent: _test_skill for {module_name_for_import} completed.")

    except ImportError as e_imp:
        error_details = f"ImportError: {e_imp}. This can happen if the skill has missing dependencies or syntax errors."
        logging.error(f"SkillReviewAgent: ImportError during review of {skill_filename}: {e_imp}", exc_info=True)
    except Exception as e_test:
        error_details = f"Exception during _test_skill execution: {e_test}\n{traceback.format_exc()}"
        logging.error(f"SkillReviewAgent: Exception in _test_skill for {skill_filename}: {e_test}", exc_info=True)
    finally:
        # At this point, context.spoken_messages_during_mute contains output from the proposed skill's test.
        proposed_skill_test_output = list(context.spoken_messages_during_mute) # Copy it
        context.clear_spoken_messages_for_test() # Clear the buffer

        # Restore the mute state to what it was when this function was called.
        # This ensures that speak calls made by *this function* (review_and_test_proposed_skill)
        # are correctly handled (muted/captured or spoken aloud) based on the caller's intent.
        context.is_muted = original_caller_mute_state

        if module_name_for_import in sys.modules:
            del sys.modules[module_name_for_import]

    # Now, speak the summary. These context.speak calls will adhere to original_caller_mute_state.
    if test_passed:
        context.speak(f"Review of '{skill_filename}': The _test_skill function executed successfully.")
        if proposed_skill_test_output:
            context.speak("Test output during review:")
            for line in proposed_skill_test_output: # Iterate over the clean, copied list
                context.speak(f"- {line}") # Speak each line for clarity
    else:
        context.speak(f"Review of '{skill_filename}': The _test_skill function encountered an issue.")
        if error_details:
            # Speak only the first line of the error to keep TTS concise
            context.speak(f"Details: {error_details.splitlines()[0]}")
            # Log the full error for developer review
            logging.error(f"SkillReviewAgent: Full error details for {skill_filename} review:\n{error_details}")

            # --- Trigger SkillRefinementAgent ---
            context.speak(f"I will ask the Skill Refinement Agent to attempt a fix for '{skill_filename}'.")
            if hasattr(context._praxis_core_ref, 'skill_refinement_agent_instance') and \
               context._praxis_core_ref.skill_refinement_agent_instance:
                refinement_agent = context._praxis_core_ref.skill_refinement_agent_instance
                # Call a new method in SkillRefinementAgent specifically for proposed skills
                refinement_agent.attempt_refinement_of_proposed_skill(context, full_skill_path, error_details)
            else:
                context.speak("The Skill Refinement Agent is not available, so I cannot attempt an automated fix at this time.")
            logging.error(f"SkillReviewAgent: Full error details for {skill_filename} review:\n{error_details}")

        if proposed_skill_test_output: # This was the output before/during failure of the *proposed skill*
            context.speak("Output captured from proposed skill before or during its failure:")
            for line in proposed_skill_test_output: # Iterate over the clean, copied list
                context.speak(f"- {line}")

    # The caller (e.g., SkillReviewAgent._test_skill) is responsible for clearing
    # context.spoken_messages_during_mute after this function returns, which it already does.

def _test_skill(context: Any) -> None:
    """Tests the skill review agent itself."""
    logging.info("SkillReviewAgent Test: Starting self-test...")
    
    _ensure_proposed_skills_package_init() # Ensure __init__.py is there for tests
    proposed_dir = _get_proposed_skills_dir_path()

    # Create a dummy proposed skill that passes
    passing_skill_name = "dummy_passing_skill_for_review.py"
    passing_skill_path = os.path.join(proposed_dir, passing_skill_name)
    passing_skill_content = """
import logging
def main_func(context: any, arg1: str):
    context.speak(f"Dummy skill main_func called with {arg1}")
    logging.info("Dummy skill main_func executed")
    return f"Processed: {arg1}"

def _test_skill(context: any):
    logging.info("Dummy passing skill: _test_skill running...")
    context.speak("Dummy test skill speaking: Test step 1")
    result = main_func(context, "test_arg")
    assert result == "Processed: test_arg", f"Assertion failed: Expected 'Processed: test_arg', got '{result}'"
    context.speak("Dummy test skill speaking: Test step 2 - assertion passed")
    logging.info("Dummy passing skill: _test_skill completed successfully.")
"""
    with open(passing_skill_path, "w", encoding='utf-8') as f:
        f.write(passing_skill_content)

    # Create a dummy proposed skill that fails
    failing_skill_name = "dummy_failing_skill_for_review.py"
    failing_skill_path = os.path.join(proposed_dir, failing_skill_name)
    failing_skill_content = """
import logging
def _test_skill(context: any):
    logging.info("Dummy failing skill: _test_skill running...")
    context.speak("This skill will fail intentionally.")
    raise ValueError("Intentional failure for testing SkillReviewAgent")
"""
    with open(failing_skill_path, "w", encoding='utf-8') as f:
        f.write(failing_skill_content)

    # Create a dummy skill with no _test_skill
    no_test_skill_name = "dummy_no_test_skill_for_review.py"
    no_test_skill_path = os.path.join(proposed_dir, no_test_skill_name)
    no_test_skill_content = """
import logging
def some_other_function():
    logging.info("This skill has no _test_skill")
"""
    with open(no_test_skill_path, "w", encoding='utf-8') as f:
        f.write(no_test_skill_content)

    # Test listing
    logging.info("SkillReviewAgent Test: Testing list_proposed_skills...")
    list_proposed_skills(context)
    # Check if spoken messages contain expected filenames
    spoken_after_list = " ".join(context.spoken_messages_during_mute)
    assert passing_skill_name in spoken_after_list, f"'{passing_skill_name}' not found in list output."
    assert failing_skill_name in spoken_after_list, f"'{failing_skill_name}' not found in list output."
    context.clear_spoken_messages_for_test()

    # Test reviewing the passing skill
    logging.info(f"SkillReviewAgent Test: Testing review_and_test_proposed_skill for {passing_skill_name}...")
    review_and_test_proposed_skill(context, passing_skill_name)
    spoken_after_pass = " ".join(context.spoken_messages_during_mute)
    assert "executed successfully" in spoken_after_pass, "Passing skill test did not report success."
    assert "Dummy test skill speaking: Test step 1" in spoken_after_pass, "Passing skill test output missing."
    assert "Dummy test skill speaking: Test step 2 - assertion passed" in spoken_after_pass, "Passing skill test output missing."
    context.clear_spoken_messages_for_test()

    # Test reviewing the failing skill
    logging.info(f"SkillReviewAgent Test: Testing review_and_test_proposed_skill for {failing_skill_name}...")
    review_and_test_proposed_skill(context, failing_skill_name)
    spoken_after_fail = " ".join(context.spoken_messages_during_mute)
    assert "encountered an issue" in spoken_after_fail, "Failing skill test did not report an issue."
    assert "Intentional failure for testing SkillReviewAgent" in spoken_after_fail, "Failing skill error details missing."
    context.clear_spoken_messages_for_test()

    # Test reviewing skill with no _test_skill
    logging.info(f"SkillReviewAgent Test: Testing review_and_test_proposed_skill for {no_test_skill_name}...")
    review_and_test_proposed_skill(context, no_test_skill_name)
    assert "does not have a '_test_skill' function" in " ".join(context.spoken_messages_during_mute), "Skill with no test function not handled correctly."
    context.clear_spoken_messages_for_test()
    
    # Test reviewing a non-existent skill
    logging.info("SkillReviewAgent Test: Testing review_and_test_proposed_skill for non_existent_skill.py...")
    review_and_test_proposed_skill(context, "non_existent_skill.py")
    assert "could not find the skill file" in " ".join(context.spoken_messages_during_mute), "Non-existent skill not handled correctly."
    context.clear_spoken_messages_for_test()

    # Clean up dummy files
    for p in [passing_skill_path, failing_skill_path, no_test_skill_path]:
        if os.path.exists(p):
            os.remove(p)
    
    # Do not remove __init__.py here, as _ensure_proposed_skills_package_init will manage it.
    # If the proposed_dir was created *only* for this test and is now empty, it could be removed,
    # but it's safer to leave it if other processes might use it.

    logging.info("SkillReviewAgent Test: Self-test completed.")