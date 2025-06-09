# skills/proactive_engagement_skill.py
import logging
import random
from typing import Any, List, Dict

def suggest_engagement_topic(context: Any) -> None:
    """
    Retrieves user interests and uses the LLM to suggest a related topic
    for conversation or exploration.
    """
    if not hasattr(context, "current_user_name") or not context.current_user_name:
        context.speak("I'd love to suggest something, but I don't know who I'm speaking with.")
        logging.warning("ProactiveEngagementSkill: current_user_name not available in context.")
        return

    if not hasattr(context, "kb") or \
       not hasattr(context.kb, "get_user_profile_items_by_category"):
        context.speak("I'm having trouble accessing my knowledge about your interests right now.")
        logging.error("ProactiveEngagementSkill: KnowledgeBase or get_user_profile_items_by_category not available.")
        return

    user_name = context.current_user_name
    # Fetch items from categories like 'interest', 'hobby', 'preferred_topic'
    # For now, let's focus on a general 'interest' category
    interest_items: List[Dict[str, str]] = context.kb.get_user_profile_items_by_category(user_name, "interest")
    
    if not interest_items:
        # Fallback if no specific interests are stored yet
        context.speak(f"{user_name}, perhaps we could chat about current events, or is there a particular subject you've been pondering lately?")
        logging.info(f"ProactiveEngagementSkill: No specific interests found for {user_name}, offered general prompt.")
        return

    # Select a random interest to base the suggestion on
    selected_interest_item = random.choice(interest_items)
    interest_key = selected_interest_item.get("item_key", "a topic")
    interest_value = selected_interest_item.get("item_value", "something you enjoy")

    context.speak(f"Thinking of something for you, {user_name}...")

    prompt = f"""
You are Praxis, an AI assistant. Your user, {user_name}, has expressed an interest in '{interest_value}' (related to their {interest_key}). 
Based on this interest, please suggest one of the following:
1. A specific, interesting question to ponder about '{interest_value}'.
2. A recent development or a fascinating fact related to '{interest_value}'.
3. A related topic they might also find interesting.

Keep your suggestion concise (1-2 sentences) and engaging. Frame it as a friendly suggestion.
Example: "Since you're interested in astronomy, have you ever wondered about the possibility of life on exoplanets?"
Another Example: "I recall you enjoy history. Did you know that the Library of Alexandria might not have been destroyed in a single fire, but declined over centuries?"

Your suggestion for {user_name} based on their interest in '{interest_value}':
"""

    try:
        response = context.chat_session.send_message(prompt)
        suggestion = response.text.strip()
        if suggestion:
            context.speak(suggestion)
            logging.info(f"ProactiveEngagementSkill: Suggested '{suggestion}' to {user_name} based on interest '{interest_key}: {interest_value}'.")
        else:
            context.speak(f"I was trying to think of something related to {interest_value}, but my thoughts are a bit muddled right now, {user_name}.")
    except Exception as e:
        logging.error(f"ProactiveEngagementSkill: Error calling LLM for suggestion: {e}", exc_info=True)
        context.speak(f"My apologies, {user_name}. I had a hiccup trying to come up with a suggestion.")

def _test_skill(context: Any) -> None:
    """Placeholder test for the proactive engagement skill."""
    logging.info("ProactiveEngagementSkill: _test_skill called. (Note: Full test requires mock KB, LLM, and user context).")
    # To truly test, you'd mock context.kb to return sample interests,
    # and context.chat_session.send_message to return a sample suggestion.
    # For now, just ensure it can be called.
    # suggest_engagement_topic(context) # Avoid running full logic in automated test without extensive mocking
    context.speak("Proactive engagement skill self-test placeholder executed.")
    assert True