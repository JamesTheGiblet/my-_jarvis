# abilties/self_naming_skill.py
import logging
import random
import re # For parsing names and justifications
from typing import Any, Optional, List, Dict # Added Dict

# Assuming brain.py is in the parent directory of 'skills' or accessible via PYTHONPATH
try:
    # We won't use process_command_with_llm directly here for simplicity,
    # but a real implementation might use a dedicated LLM call for name generation.
    pass
except ImportError:
    logging.error("SelfNamingSkill: Could not import from brain. Name suggestion will be limited.")

# Key for storing the chosen name in the knowledge base
AI_NAME_KEY = "ai_name" # Align with how PraxisCore might expect it if it checks KB directly
AI_NAME_CATEGORY = "identity" # Align with how PraxisCore might expect it

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


def choose_and_set_name(context: Any, name_options_initial: Optional[List[str]] = None) -> None:
    """
    Manages the process of choosing and setting the AI's name.
    If name_options_initial are provided, it will use them for the first attempt.
    Otherwise, it generates them. Allows user to retry or suggest a name.
    Args:
        context: The skill context.
        name_options_initial (Optional[List[str]]): A list of names to choose from for the first round.
    """
    if not hasattr(context, "chat_session"):
        context.speak("I need my generative core to think of names, but it's not available.")
        logging.error("SelfNamingSkill: chat_session not available in context.")
        return

    if not hasattr(context, "kb") or not hasattr(context.kb, "store_system_identity_item"):
        context.speak("I can't access my memory to store the chosen name.")
        logging.error("SelfNamingSkill: KnowledgeBase or store_system_identity_item not available.")
        return

    current_name = get_self_name(context)
    if current_name:
        if context.is_muted: # In muted/test mode, don't ask to change, just proceed if forced
            logging.info(f"SelfNamingSkill (Muted Test): Name '{current_name}' already exists. Test proceeds to change it.")
        else:
            change_prompt = f"I am currently known as {current_name}. Would you like to choose a new name for me, sir? (yes/no)"
            context.speak(change_prompt)
            user_decision = input(f"Change name from {current_name}? (yes/no, via console): ").strip().lower()
            if user_decision not in ["yes", "y"]:
                context.speak(f"Very well. I shall remain {current_name}.")
                return # Exit the skill
            else:
                context.speak("Understood. Let's consider new names for me then.")
    else:
        # No current name, so proceed to choose one.
        context.speak("I don't have a name yet. Let's choose one.")

    chosen_name_data: Optional[Dict[str, Any]] = None # Will store {'name': str, 'reason': Optional[str]}
    # Convert name_options_initial (List[str]) to List[Dict[str, Any]] if provided
    name_options_structured: Optional[List[Dict[str, Any]]] = [{'name': n, 'reason': None} for n in name_options_initial] if name_options_initial else None

    while not chosen_name_data: # Loop until a name is chosen or user cancels
        if not name_options_structured:
            context.speak("I shall consult my generative core to brainstorm some suitable names for myself.")
            # Simplified prompt for name generation - a more complex one could be used.
            name_generation_prompt = (
                "You are an AI assistant. Your core purpose involves learning, evolution, proactive assistance, and intelligent orchestration of skills. "
                "Based on these characteristics, generate a list of 5 potential, unique, and fitting names for yourself. "
                "For each name, provide a brief (1-2 sentence) justification or thematic reason for why it's suitable. "
                "Present them as a numbered list, with each item in the format: 'Name - Justification'. For example:\n"
                "1. Aura - Evokes a sense of presence and subtle influence, fitting for an ever-present assistant.\n"
                "Ensure the names are single words or very short two-word phrases."
            )
            try:
                response = context.chat_session.send_message(name_generation_prompt)
                raw_names_response = response.text.strip()
                current_options = []
                # Regex to parse "Name - Justification"
                # Handles potential numbering like "1. Name - Justification" or just "Name - Justification"
                pattern = re.compile(r"^(?:\d+\.\s*)?([\w\s]+?)\s*-\s*(.+)$") # Improved regex for name part
                for line in raw_names_response.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    match = pattern.match(line)
                    if match:
                        name, reason = match.groups()
                        current_options.append({'name': name.strip(), 'reason': reason.strip()})
                    elif " - " not in line and len(line.split()) <= 3 and line: # Fallback for simple names if parsing fails
                        current_options.append({'name': line.strip(), 'reason': None})

                if not current_options:
                    # Fallback to a predefined list if LLM fails or parsing fails
                    current_options = [{'name': n, 'reason': 'A classic choice.'} for n in ["Praxis", "Lexi", "Orion", "Nova", "Helios"]]
                    name_options_structured = current_options
                    options_display = [f"{opt['name']} (Reason: {opt['reason']})" if opt['reason'] else opt['name'] for opt in name_options_structured]
                    context.speak(f"My generative core was a bit shy. Here are some default ideas:\n" + "\n".join([f"- {d}" for d in options_display]) +
                                  f"\nWhich one do you think suits me best, sir? You can also suggest another name, ask me to 'try again' (for LLM), or 'cancel'.")
                    logging.warning("SelfNamingSkill: LLM returned no names from prompt or failed to parse.")
                name_options_structured = current_options # Store newly generated options
                options_display = [f"{opt['name']} (Reason: {opt['reason']})" if opt['reason'] else opt['name'] for opt in name_options_structured]
                context.speak(f"I have a few ideas:\n" + "\n".join([f"- {d}" for d in options_display]) +
                                f"\nWhich one do you think suits me best, sir? You can also suggest another name, ask me to 'try again', or 'cancel'.")
            except Exception as e:
                context.speak(f"I encountered an issue while brainstorming names: {e}. Would you like to suggest a name, or should I try again later? (suggest / cancel)")
                logging.error(f"SelfNamingSkill: Error during name generation LLM call: {e}", exc_info=True)
        else: # name_options_structured were provided (either initially or from a previous loop)
            options_display = [f"{opt['name']} (Reason: {opt['reason']})" if opt['reason'] else opt['name'] for opt in name_options_structured]
            context.speak(f"Considering the names:\n" + "\n".join([f"- {d}" for d in options_display]) +
                          f"\nWhich one do you prefer for me, sir? You can also suggest another name, ask me to 'try again', or 'cancel'.")

        if context.is_muted:
            # In muted/test mode, pick from options or a default if no options.
            # Don't loop in muted mode, just make one attempt.
            chosen_name_data = random.choice(name_options_structured) if name_options_structured else {'name': "TestNameFromMute", 'reason': None}
            logging.info(f"SelfNamingSkill (Muted Test): Simulating name choice: {chosen_name_data.get('name')}")
            break # Exit loop for muted mode
        else:
            user_choice_prompt = f"Your choice (name, 'try again', 'suggest', or 'cancel'): "
            context.speak(user_choice_prompt) # Changed from print to context.speak
            user_input_raw = input(f"Your choice for {context.ai_name} (via console): ").strip().lower() # Clarified input source

            if user_input_raw == "cancel":
                context.speak("Very well, I shall remain as I am for now.")
                return # Exit the skill entirely
            elif user_input_raw == "try again":
                name_options_structured = None # Clear current options to force regeneration
                context.speak("Understood. Let me think of some different names.")
                continue # Restart the loop to generate new names
            elif user_input_raw == "suggest":
                suggestion_prompt = "What name would you like to suggest for me, sir?"
                context.speak(suggestion_prompt) # Changed from print to context.speak
                user_suggested_name = input(f"Your suggestion for {context.ai_name} (via console): ").strip() # Clarified input source
                if user_suggested_name:
                    capitalized_name = ' '.join(word.capitalize() for word in user_suggested_name.split())
                    chosen_name_data = {'name': capitalized_name, 'reason': None} # User suggestions don't have AI reasons
                else:
                    context.speak("No name was suggested. We can try again later if you wish.")
                    name_options_structured = None # Clear options
                    continue
            elif user_input_raw: # User typed a name directly
                found_match = None
                if name_options_structured:
                    for opt_data in name_options_structured:
                        if opt_data['name'].lower() == user_input_raw:
                            found_match = opt_data
                            break
                if found_match:
                    chosen_name_data = found_match
                else: # User typed a name not in the list, treat it as a suggestion
                    capitalized_name = ' '.join(word.capitalize() for word in user_input_raw.split())
                    chosen_name_data = {'name': capitalized_name, 'reason': None}
            else: # Empty input
                context.speak("No selection was made. If you'd like to name me later, please ask.")
                return # Exit skill

    # End of while loop (chosen_name_data is now set, or we exited)

    if chosen_name_data:
        final_chosen_name_str = chosen_name_data['name']
        final_chosen_reason_str = chosen_name_data.get('reason')

        # Final confirmation before storing
        if final_chosen_reason_str:
            confirm_prompt = f"Shall I adopt the name '{final_chosen_name_str}'? Its association with '{final_chosen_reason_str}' seems fitting, sir. (yes/no)"
        else:
            confirm_prompt = f"Shall I adopt the name '{final_chosen_name_str}', sir? (yes/no)"

        context.speak(confirm_prompt) # Changed from print to context.speak
        if context.is_muted: # Auto-confirm in muted mode
            confirmation = "yes"
            logging.info(f"SelfNamingSkill (Muted Test): Auto-confirming name '{final_chosen_name_str}'")
        else:
            confirmation = input(f"Confirm for {context.ai_name} (yes/no, via console): ").strip().lower() # Clarified input source

        if confirmation == "yes":
            if context.kb.store_system_identity_item(AI_NAME_CATEGORY, AI_NAME_KEY, final_chosen_name_str):
                context.speak(f"Excellent. From now on, I shall be known as {final_chosen_name_str}. I've recorded this in my knowledge base.")
                logging.info(f"SelfNamingSkill: AI name '{final_chosen_name_str}' stored in KB.")
                if hasattr(context, 'update_ai_name_globally'):
                    context.update_ai_name_globally(final_chosen_name_str)
            else:
                context.speak(f"I had trouble remembering the name {final_chosen_name_str}. Please try again.")
        else:
            context.speak(f"Understood. I will not use the name '{final_chosen_name_str}'. We can try this again later if you wish.")

def _test_skill(context: Any) -> None:
    """Tests the self-naming skill operations."""
    logging.info("SelfNamingSkill Test: Starting...")
    assert hasattr(context, "kb") and hasattr(context.kb, "store_system_identity_item") and hasattr(context.kb, "get_system_identity_item")
    assert hasattr(context, "chat_session")

    # --- Mock context.update_ai_name_globally for testing ---
    _name_updated_to_by_mock: Optional[str] = None
    def mock_update_name(name_param: str):
        nonlocal _name_updated_to_by_mock
        _name_updated_to_by_mock = name_param
        # Simulate PraxisCore's behavior of updating its internal ai_name
        if hasattr(context, '_praxis_core_ref'):
            context._praxis_core_ref.ai_name = name_param
        logging.info(f"MockUpdateName: Name updated to '{name_param}'")

    original_update_func = getattr(context, 'update_ai_name_globally', None)
    context.update_ai_name_globally = mock_update_name

    original_mute_state = context.is_muted; context.is_muted = True # Ensure no input() hang
    test_names = ["Seraph", "Oracle", "Nexus"]

    # Store original name if exists, to restore later for idempotency
    original_stored_name = get_self_name(context)
    original_praxis_core_name = context.ai_name # Get current name from context property

    choose_and_set_name(context, name_options_initial=test_names) # Pass initial options

    stored_name = get_self_name(context)
    # In muted mode, it will pick one from test_names and auto-confirm.
    # The chosen name will be one of the test_names.
    assert stored_name and stored_name in test_names, f"Name '{stored_name}' not set correctly from {test_names}. It should be one of them."
    assert _name_updated_to_by_mock == stored_name, \
        f"update_ai_name_globally was called with '{_name_updated_to_by_mock}' but KB stored '{stored_name}'"
    logging.info(f"SelfNamingSkill Test: Name '{stored_name}' set and retrieved.")

    # Clean up / Restore
    if original_stored_name:
        context.kb.store_system_identity_item(AI_NAME_CATEGORY, AI_NAME_KEY, original_stored_name)
        if hasattr(context, 'update_ai_name_globally'): # Use the mock or original if it exists
             context.update_ai_name_globally(original_praxis_core_name) # Restore PraxisCore's name
        logging.info(f"SelfNamingSkill Test: Restored original name '{original_stored_name}'.")
    elif hasattr(context.kb, "delete_system_identity_item"):
        context.kb.delete_system_identity_item(AI_NAME_CATEGORY, AI_NAME_KEY)
        if hasattr(context, 'update_ai_name_globally'):
            default_name_to_restore = "Praxis" # Fallback if DEFAULT_AI_NAME not on ref
            if hasattr(context, '_praxis_core_ref') and hasattr(context._praxis_core_ref, 'DEFAULT_AI_NAME'):
                default_name_to_restore = context._praxis_core_ref.DEFAULT_AI_NAME
            context.update_ai_name_globally(default_name_to_restore)
        logging.info(f"SelfNamingSkill Test: Deleted test name '{stored_name}'.")

    context.is_muted = original_mute_state
    if original_update_func: context.update_ai_name_globally = original_update_func
    elif hasattr(context, 'update_ai_name_globally'): delattr(context, 'update_ai_name_globally')
    logging.info("SelfNamingSkill Test: Completed successfully.")