# skills/feedback_skill.py
import logging
from typing import Optional

# SkillContext will provide access to knowledge_base functions via context.kb

def provide_feedback_on_last_action(context, was_correct: bool, comment: Optional[str] = None):
    """
    Allows the user to provide feedback on the correctness of the last executed skill type.
    Args:
        context: The skill context, providing access to context.kb for KnowledgeBase.
        was_correct (bool): True if the last action was correct, False otherwise.
        comment (Optional[str]): An optional comment from the user.
    """
    try:
        last_skill_name = context.kb.get_most_recently_used_skill()

        if not last_skill_name:
            context.speak("I don't have a record of a recent action to apply feedback to, sir.")
            return

        context.kb.record_user_feedback(
            skill_name=last_skill_name,
            was_correct_according_to_user=was_correct,
            comment=comment
        )
        
        feedback_type = "positive" if was_correct else "corrective"
        response = f"Thank you for the {feedback_type} feedback regarding the '{last_skill_name}' skill."
        if comment:
            response += f" I've noted your comment: \"{comment}\"."
        else:
            response += " I've updated my performance logs."
        context.speak(response)
        logging.info(f"User feedback recorded for skill '{last_skill_name}': Correct={was_correct}, Comment='{comment}'")

    except Exception as e:
        logging.error(f"Error in provide_feedback_on_last_action: {e}", exc_info=True)
        context.speak("I encountered an issue while trying to process your feedback. Please check the logs.")

def _test_skill(context):
    """Runs a quick self-test for the feedback_skill module."""
    logging.info("[feedback_skill_test] Running self-test for feedback_skill module...")
    try:
        # This test primarily checks if the skill can be called without crashing.
        # Actual KB interaction verification is complex for a simple _test_skill.
        logging.info("[feedback_skill_test] Simulating a call to provide_feedback_on_last_action (positive).")
        provide_feedback_on_last_action(context, was_correct=True, comment="Test: This was great!")
        logging.info("[feedback_skill_test] Simulating a call to provide_feedback_on_last_action (corrective).")
        provide_feedback_on_last_action(context, was_correct=False, comment="Test: This was not what I expected.")
        logging.info("[feedback_skill_test] feedback_skill self-test calls completed.")
    except Exception as e:
        logging.error(f"[feedback_skill_test] Self-test FAILED: {e}", exc_info=True)
        raise # Re-raise to signal failure to the loader