# skills/self_naming_skill.py
import logging
import random
from typing import Any, Optional, List

# Key for storing the chosen name in the knowledge base
AI_NAME_KEY = "chosen_ai_name"
AI_NAME_CATEGORY = "system_identity" 

def get_self_name(context: Any) -> Optional[str]:
    """
    Retrieves the AI's chosen name from the knowledge base.
    Args:
        context: The skill context.
    Returns:
        The AI's name if set, otherwise None.
    """
    if not hasattr(context, "kb") or not hasattr(context.kb, "get_system_identity_item"):
        logging.error("SelfNamingSkill: KnowledgeBase or get_system_identity_item not available in context.")
        return None
    return context.kb.get_system_identity_item(AI_NAME_CATEGORY, AI_NAME_KEY)


def choose_and_set_name(context: Any, name_options: Optional[List[str]] = None) -> None:
    """
    Manages the process of choosing and setting the AI's name.
    If name_options are provided, it will use them. Otherwise, it generates them.
    Args:
        context: The skill context.
        name_options (Optional[List[str]]): A list of names to choose from.
    """
    if not hasattr(context, "chat_session"):
        context.speak("I need my generative core to think of names, but it's not available.")
        logging.error("SelfNamingSkill: chat_session not available in context.")
        return

    if not hasattr(context, "kb") or not hasattr(context.kb, "store_system_identity_item"):
        context.speak("I can't access my memory to store the chosen name.")
        logging.error("SelfNamingSkill: KnowledgeBase or store_system_identity_item not available.")
        return

    chosen_name: Optional[str] = None

    if not name_options:
        context.speak("I shall consult my generative core to brainstorm some suitable names for myself.")
        name_generation_prompt = (
            "You are an AI assistant. Your core purpose involves learning, evolution, proactive assistance, and intelligent orchestration of skills. "
            "Based on these characteristics, generate a list of 5 potential, unique, and fitting names for yourself. "
            "The names should be single words or very short two-word phrases. "
            "Present them as a simple comma-separated list. For example: Aura, Synapse, Vector, Nova Prime, Echo"
        )
        try:
            response = context.chat_session.send_message(name_generation_prompt)
            raw_names = response.text.strip()
            name_options = [name.strip() for name in raw_names.split(',') if name.strip()]
            if not name_options:
                context.speak("The generative core didn't provide any name suggestions. I'll need to try again later.")
                logging.warning("SelfNamingSkill: LLM returned no names from prompt.")
                return
            context.speak(f"I have a few ideas: {', '.join(name_options)}. Which one do you think suits me best, sir?")
        except Exception as e:
            context.speak(f"I encountered an issue while brainstorming names: {e}")
            logging.error(f"SelfNamingSkill: Error during name generation LLM call: {e}", exc_info=True)
            return
    else:
        context.speak(f"Considering the names: {', '.join(name_options)}. Which one do you prefer for me, sir?")

    if context.is_muted: 
        chosen_name = random.choice(name_options) if name_options else "TestName"
        logging.info(f"SelfNamingSkill (Muted Test): Simulating name choice: {chosen_name}")
    else:
        user_choice_prompt = "Please type the name you've chosen for me from the list, or suggest another: "
        # This part is tricky for a skill if it's not driving the main input loop.
        # For a GUI, this would likely be handled by the GUI sending a command back.
        # For CLI, input() is okay for now.
        print(f"{context.ai_name} (to you): {user_choice_prompt}") 
        user_input_name = input(f"Your choice: ").strip()
        if user_input_name:
            chosen_name = user_input_name
        else:
            context.speak("No name was selected. I shall remain as I am for now.")
            return

    if chosen_name:
        if context.kb.store_system_identity_item(AI_NAME_CATEGORY, AI_NAME_KEY, chosen_name):
            context.speak(f"Excellent choice. From now on, I shall be known as {chosen_name}. I've recorded this in my knowledge base.")
            logging.info(f"SelfNamingSkill: AI name set to '{chosen_name}'.")
            if hasattr(context, 'update_ai_name_globally'):
                context.update_ai_name_globally(chosen_name)
        else:
            context.speak(f"I had trouble remembering the name {chosen_name}. Please try again.")

def _test_skill(context: Any) -> None:
    """Tests the self-naming skill operations."""
    logging.info("SelfNamingSkill Test: Starting...")
    assert hasattr(context, "kb") and hasattr(context.kb, "store_system_identity_item") and hasattr(context.kb, "get_system_identity_item")
    assert hasattr(context, "chat_session")

    _name_updated_flag = False
    def mock_update_name(name): nonlocal _name_updated_flag; _name_updated_flag = True
    
    original_update_func = getattr(context, 'update_ai_name_globally', None)
    context.update_ai_name_globally = mock_update_name
    
    original_mute_state = context.is_muted; context.is_muted = True # Ensure no input() hang
    test_names = ["Seraph", "Oracle", "Nexus"]
    choose_and_set_name(context, name_options=test_names)
    stored_name = get_self_name(context)
    assert stored_name and stored_name in test_names, f"Name '{stored_name}' not set correctly from {test_names}."
    assert _name_updated_flag, "update_ai_name_globally was not called."
    logging.info(f"SelfNamingSkill Test: Name '{stored_name}' set and retrieved.")
    if hasattr(context.kb, "delete_system_identity_item"): context.kb.delete_system_identity_item(AI_NAME_CATEGORY, AI_NAME_KEY)
    context.is_muted = original_mute_state
    if original_update_func: context.update_ai_name_globally = original_update_func
    elif hasattr(context, 'update_ai_name_globally'): delattr(context, 'update_ai_name_globally')
    logging.info("SelfNamingSkill Test: Completed successfully.")