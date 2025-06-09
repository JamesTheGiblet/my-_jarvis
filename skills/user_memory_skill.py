# skills/user_memory_skill.py
import logging
from typing import Any, Optional

def ask_and_store_profile_item(context: Any, question_to_ask: str, item_category: str, item_key: str) -> None:
    """
    Asks the user a question and stores their answer as a profile item.
    Args:
        context: The skill context.
        question_to_ask: The question Praxis should ask the user.
        item_category: The category for the profile item (e.g., 'interest', 'preference').
        item_key: The specific key for the profile item (e.g., 'hobby', 'music_genre').
    """
    if not hasattr(context, "kb") or \
       not hasattr(context.kb, "store_user_profile_item"):
        context.speak("I'm sorry, I'm unable to access my memory storage functions at the moment.")
        logging.error("UserMemorySkill: KnowledgeBase or store_user_profile_item not available in context.")
        return

    if not hasattr(context, "current_user_name") or not context.current_user_name:
        context.speak("I'm sorry, I don't know who I'm speaking with to store this information.")
        logging.error("UserMemorySkill: current_user_name not available in context.")
        return

    context.speak(question_to_ask)
    try:
        if context.is_muted: # During tests, we can't use input()
            user_answer = f"Simulated answer for {item_category}/{item_key}"
            logging.info(f"UserMemorySkill (Muted Test): Simulating input for '{question_to_ask}' (cat: {item_category}, key: {item_key}): {user_answer}")
        else:
            # Direct input approach for simplicity in this skill.
            print(f"Praxis (to you): {question_to_ask}")
            user_answer = input(f"Your answer for {item_category} - {item_key}: ").strip()
            logging.info(f"UserMemorySkill: User answered '{user_answer}' for category '{item_category}', key '{item_key}'.")

        if context.kb.store_user_profile_item(context.current_user_name, item_category, item_key, user_answer):
            context.speak(f"Thank you. I've noted that your {item_key} ({item_category}) is '{user_answer}'.")
        else:
            context.speak(f"I had trouble remembering that. Please try again or check the logs.")

    except Exception as e:
        logging.error(f"UserMemorySkill: Error in ask_and_store_profile_item for cat '{item_category}', key '{item_key}': {e}", exc_info=True)
        context.speak("I encountered an issue while trying to ask or store that information.")

def recall_profile_item(context: Any, item_category: str, item_key: str) -> None:
    """
    Recalls a specific profile item for the current user.
    Args:
        context: The skill context.
        item_category: The category of the profile item.
        item_key: The key of the profile item.
    """
    if not hasattr(context, "kb") or \
       not hasattr(context.kb, "get_user_profile_item"):
        context.speak("I'm sorry, I'm unable to access my profile memory retrieval functions at the moment.")
        logging.error("UserMemorySkill: KnowledgeBase or get_user_profile_item not available in context.")
        return

    if not hasattr(context, "current_user_name") or not context.current_user_name:
        context.speak("I'm sorry, I don't know who I'm speaking with to recall this information.")
        logging.error("UserMemorySkill: current_user_name not available in context.")
        return

    stored_value = context.kb.get_user_profile_item(context.current_user_name, item_category, item_key)
    if stored_value is not None:
        context.speak(f"For you, {context.current_user_name}, I recall that {item_key} ({item_category}) is '{stored_value}'.")
    else:
        context.speak(f"I don't seem to have any information stored for {item_key} ({item_category}) for you, {context.current_user_name}.")

def list_user_profile_category(context: Any, item_category: str) -> None:
    """Lists all profile items for the current user within a given category."""
    if not hasattr(context, "kb") or not hasattr(context.kb, "get_user_profile_items_by_category"):
        context.speak("I'm sorry, I can't access the profile item listing function right now.")
        logging.error("UserMemorySkill: KnowledgeBase or get_user_profile_items_by_category not available.")
        return
    if not hasattr(context, "current_user_name") or not context.current_user_name:
        context.speak("I need to know who you are to list profile items.")
        return

    items = context.kb.get_user_profile_items_by_category(context.current_user_name, item_category)
    if items:
        response = f"For you, {context.current_user_name}, under the category '{item_category}', I have:\n"
        for item in items:
            response += f"- {item['item_key']}: {item['item_value']}\n"
        context.speak(response.strip())
    else:
        context.speak(f"I don't have any items stored for you under the category '{item_category}'.")

def _test_skill(context: Any) -> None:
    """Tests the user memory skill operations."""
    logging.info("UserMemorySkill Test: Starting...")
    # Ensure current_user_name is in context for testing
    if not hasattr(context, "current_user_name") or not context.current_user_name:
        logging.warning("UserMemorySkill Test: context.current_user_name not set, using a dummy test user.")
        context.current_user_name = "test_user_for_skill" # Set a dummy for test if not present

    # Test storing and recalling a profile item
    test_cat = "preference"
    test_key = "favorite_color"
    test_val = "cerulean"

    # Simulate ask_and_store_profile_item without actual input() for testing
    # Directly use store_user_profile_item for test setup
    assert context.kb.store_user_profile_item(context.current_user_name, test_cat, test_key, test_val), "Test: Failed to store profile item."
    
    recall_profile_item(context, test_cat, test_key)
    expected_recall_message_part = f"{test_key} ({test_cat}) is '{test_val}'"
    assert expected_recall_message_part in context.get_last_spoken_message_for_test(), f"Test: Recall message mismatch. Got: {context.get_last_spoken_message_for_test()}"
    context.clear_spoken_messages_for_test()

    list_user_profile_category(context, test_cat)
    assert f"- {test_key}: {test_val}" in context.get_last_spoken_message_for_test(), "Test: List category message mismatch."
    context.clear_spoken_messages_for_test()

    # Cleanup test data
    assert context.kb.delete_user_profile_item(context.current_user_name, test_cat, test_key), f"Test: Failed to delete profile item {test_cat}/{test_key}"
    logging.info(f"UserMemorySkill Test: Cleaned up test item {test_cat}/{test_key}")

    logging.info("UserMemorySkill Test: Completed successfully.")