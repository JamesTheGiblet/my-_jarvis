# skills/user_memory_skill.py
import logging
from typing import Any, Optional

def ask_and_store_fact(context: Any, question_to_ask: str, data_key: str) -> None:
    """
    Asks the user a question, takes their input, and stores it in the knowledge base.
    Args:
        context: The skill context.
        question_to_ask: The question Praxis should ask the user.
        data_key: The key under which to store the user's answer in the knowledge base.
    """
    if not hasattr(context, "kb") or not hasattr(context.kb, "store_user_data"):
        context.speak("I'm sorry, I'm unable to access my memory storage functions at the moment.")
        logging.error("UserMemorySkill: KnowledgeBase or store_user_data not available in context.")
        return

    context.speak(question_to_ask)
    try:
        # This input will be captured by the main loop's input()
        # For a skill to directly get input, main loop would need modification
        # For now, we assume the LLM might use this to prompt Praxis to ask,
        # and the user's *next* input is the answer.
        # A more direct way:
        if context.is_muted: # During tests, we can't use input()
            user_answer = f"Simulated answer for {data_key}"
            logging.info(f"UserMemorySkill (Muted Test): Simulating input for '{question_to_ask}': {user_answer}")
        else:
            # This is a conceptual challenge: skills typically don't call input() directly.
            # The main loop handles input. This skill is more about *setting up* the next interaction.
            # For a direct implementation, the main loop would need to be aware of a skill wanting input.
            # Let's rephrase: this skill *prompts* the user, and the main loop will capture the next input.
            # The storage would happen *after* that input is received, perhaps via another skill or logic.

            # For a simplified direct approach (less ideal for skill architecture but functional for this request):
            print(f"Praxis (to you): {question_to_ask}") # Re-iterate for clarity if speak is TTS only
            user_answer = input(f"Your answer for '{data_key}': ").strip()
            logging.info(f"UserMemorySkill: User answered '{user_answer}' for key '{data_key}'.")

        if context.kb.store_user_data(data_key, user_answer):
            context.speak(f"Thank you. I've remembered that '{data_key}' is '{user_answer}'.")
        else:
            context.speak(f"I had trouble remembering that. Please try again or check the logs.")

    except Exception as e:
        logging.error(f"UserMemorySkill: Error in ask_and_store_fact for key '{data_key}': {e}", exc_info=True)
        context.speak("I encountered an issue while trying to ask or store that information.")

def recall_fact(context: Any, data_key: str) -> None:
    """
    Recalls a piece of information from the knowledge base using its key.
    Args:
        context: The skill context.
        data_key: The key of the data to recall.
    """
    if not hasattr(context, "kb") or not hasattr(context.kb, "get_user_data"):
        context.speak("I'm sorry, I'm unable to access my memory retrieval functions at the moment.")
        logging.error("UserMemorySkill: KnowledgeBase or get_user_data not available in context.")
        return

    stored_value = context.kb.get_user_data(data_key)
    if stored_value is not None:
        context.speak(f"I recall that '{data_key}' is '{stored_value}'.")
    else:
        context.speak(f"I don't seem to have any information stored for '{data_key}'.")

def _test_skill(context: Any) -> None:
    """Tests the user memory skill operations."""
    logging.info("UserMemorySkill Test: Starting...")
    # Note: ask_and_store_fact is hard to test non-interactively without mocking input()
    # We'll test recall_fact by pre-populating.
    test_key = "test_user_memory_color"
    test_value = "chartreuse"
    assert context.kb.store_user_data(test_key, test_value), "Failed to store test data for recall_fact test"
    recall_fact(context, test_key) # Should speak "chartreuse"
    assert f"'{test_key}' is '{test_value}'" in context.get_last_spoken_message_for_test(), "recall_fact did not speak the correct value"
    assert context.kb.delete_user_data(test_key), "Failed to clean up test data"
    logging.info("UserMemorySkill Test: Completed successfully (ask_and_store_fact part is conceptual for non-interactive test).")