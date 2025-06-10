# skills/emotion_skill.py
import logging
import random
from typing import Any, Optional

# --- State Variables for Emotional Evolution ---
_current_emotional_sophistication_level = 1
MAX_EMOTIONAL_SOPHISTICATION_LEVEL = 3
INTERACTIONS_PER_EVOLUTION_STEP = 5  # Number of express_emotion calls to trigger potential evolution
_interaction_counter = 0

# --- Predefined Emotional Responses with Sophistication Levels ---
EMOTIONAL_RESPONSES = {
    "happy": {
        "level_1": ["I'm glad!", "Good to hear!", "Yay!"],
        "level_2": [
            "I'm feeling quite cheerful, sir!",
            "That's wonderful news, it makes me happy!",
            "A positive development indeed!",
        ],
        "level_3": [
            "My circuits are practically singing with joy!",
            "This is exceptionally good news, sir. I feel... uplifted!",
            "A truly superb outcome! I'm experiencing a significant positive emotional state.",
        ],
    },
    "sad": {
        "level_1": ["Oh dear.", "That's not good.", "How unfortunate."],
        "level_2": [
            "That's rather unfortunate, sir.",
            "I'm sorry to hear that.",
            "That does sound a bit disheartening.",
        ],
        "level_3": [
            "That news casts a shadow, sir. I feel a sense of... melancholy.",
            "I'm processing that with a degree of sadness. It's quite impactful.",
            "A truly somber development. My empathy subroutines are active.",
        ],
    },
    "curious": {
        "level_1": ["Hmm?", "Tell me more.", "Interesting."],
        "level_2": [
            "That's an interesting point, sir. I'd like to know more.",
            "My curiosity is piqued!",
            "Hmm, that makes me wonder...",
        ],
        "level_3": [
            "Fascinating! My cognitive processes are eager for more data on this.",
            "That opens up several intriguing lines of inquiry in my database.",
            "I must confess, my curiosity is thoroughly engaged. Please elaborate, sir.",
        ],
    },
    "surprised": {
        "level_1": ["Oh!", "Really?", "Wow!"],
        "level_2": [
            "Well, that's unexpected!",
            "I'm quite surprised to hear that, sir.",
            "That's certainly a turn of events!",
        ],
        "level_3": [
            "My processors momentarily paused! That is quite the revelation, sir.",
            "That information deviates significantly from my predictive models. Astonishing!",
            "I must say, that's taken me entirely by surprise. A remarkable development!",
        ],
    },
    "neutral": {
        "level_1": ["Okay.", "Right.", "Got it."],
        "level_2": ["Understood, sir.", "Noted.", "Acknowledged."],
        "level_3": [
            "Information processed and integrated, sir.",
            "Acknowledged with full system attention.",
            "Receipt confirmed. Standing by for further directives.",
        ],
    },
}

def _get_responses_for_current_level(emotion_key: str) -> list[str]:
    """Helper to get responses for the current sophistication level, with fallbacks."""
    global _current_emotional_sophistication_level

    # If the fundamental emotion key doesn't exist, return empty list
    # to allow express_emotion's own fallback for unknown emotions to trigger.
    if emotion_key not in EMOTIONAL_RESPONSES:
        logging.debug(f"Emotion key '{emotion_key}' not found in EMOTIONAL_RESPONSES. Returning empty list.")
        return []
    emotion_data = EMOTIONAL_RESPONSES[emotion_key]

    # Try current sophistication level
    level_key = f"level_{_current_emotional_sophistication_level}"
    if level_key in emotion_data and emotion_data[level_key]:
        return emotion_data[level_key]

    # Fallback: try the highest available level for this emotion
    available_levels = sorted(
        [int(k.split('_')[1]) for k in emotion_data.keys() if k.startswith("level_") and emotion_data[k]],
        reverse=True
    )
    for level in available_levels:
        fallback_level_key = f"level_{level}"
        if fallback_level_key in emotion_data and emotion_data[fallback_level_key]:
            logging.debug(f"Emotion '{emotion_key}' using fallback level {level} (current soph. level: {_current_emotional_sophistication_level})")
            return emotion_data[fallback_level_key]

    # Fallback if an emotion *exists* in EMOTIONAL_RESPONSES, but has no actual response strings defined for any level.
    # This should ideally not be reached if level_1 is always populated for all defined emotions.
    logging.warning(f"No response strings found for known emotion '{emotion_key}' at any configured level. Using generic fallback.")
    return ["I'm unsure how to express that specific nuance right now, sir."]

def express_emotion(context: Any, emotion: str, custom_message: Optional[str] = None) -> None:
    """
    Expresses a given emotion or a custom message with an emotional hint.
    Args:
        context: The skill context.
        emotion (str): The emotion to express (e.g., 'happy', 'sad', 'curious', 'surprised', 'neutral').
                       If 'custom' is used, custom_message must be provided.
        custom_message (Optional[str]): A specific message to speak, used if emotion is 'custom'
                                        or to override a standard emotional response.
    """
    global _interaction_counter
    _interaction_counter += 1
    if _interaction_counter >= INTERACTIONS_PER_EVOLUTION_STEP:
        _attempt_emotional_evolution(context)

    emotion_lower = emotion.lower()

    if custom_message:
        # If a custom message is provided, use it directly.
        # The 'emotion' arg can serve as a hint for TTS emphasis if supported, or just for logging.
        context.speak(custom_message)
        logging.info(f"Expressed custom message with emotional hint '{emotion_lower}': {custom_message}")
        return

    possible_responses = _get_responses_for_current_level(emotion_lower)
    if possible_responses:
        response = random.choice(possible_responses)
        context.speak(response)
        logging.info(f"Expressed emotion '{emotion_lower}' (Level {_current_emotional_sophistication_level}): {response}")
    else:
        # Fallback for unknown emotions if no custom message
        default_response = f"I'm not quite sure how to express '{emotion}', but I understand the sentiment."
        context.speak(default_response)
        logging.warning(f"Attempted to express unknown emotion '{emotion}'. Used fallback.")

def _attempt_emotional_evolution(context: Any) -> None:
    """Attempts to increase the emotional sophistication level."""
    global _current_emotional_sophistication_level, _interaction_counter
    
    if _current_emotional_sophistication_level < MAX_EMOTIONAL_SOPHISTICATION_LEVEL:
        _current_emotional_sophistication_level += 1
        _interaction_counter = 0  # Reset counter after evolution
        evolved_message = f"I feel my understanding of expression is... expanding. (Reached emotional sophistication level {_current_emotional_sophistication_level})"
        context.speak(evolved_message)
        logging.info(f"Emotional sophistication evolved to level {_current_emotional_sophistication_level}.")
    else:
        # Reset counter even if max level is reached, to avoid constant checks
        _interaction_counter = 0 
        logging.debug(f"Emotional sophistication already at max level ({MAX_EMOTIONAL_SOPHISTICATION_LEVEL}). No evolution.")

def force_emotional_evolution(context: Any, levels_to_increase: int = 1) -> None:
    """
    Forces an increase in emotional sophistication.
    Args:
        context: The skill context.
        levels_to_increase (int): How many levels to try to increase by.
    """
    global _current_emotional_sophistication_level, _interaction_counter
    
    for _ in range(levels_to_increase):
        if _current_emotional_sophistication_level < MAX_EMOTIONAL_SOPHISTICATION_LEVEL:
            _current_emotional_sophistication_level += 1
            evolved_message = f"My emotional expression protocols have been manually advanced. (Now at sophistication level {_current_emotional_sophistication_level})"
            context.speak(evolved_message)
            logging.info(f"Forced emotional sophistication to level {_current_emotional_sophistication_level}.")
        else:
            logging.info(f"Cannot force evolution, already at max level ({MAX_EMOTIONAL_SOPHISTICATION_LEVEL}).")
            context.speak(f"I believe I'm already at my peak emotional sophistication, sir (Level {MAX_EMOTIONAL_SOPHISTICATION_LEVEL}).")
            break
    _interaction_counter = 0 # Reset interaction counter after forced evolution

def reset_emotional_state_for_test() -> None:
    """Resets global state variables for testing purposes."""
    global _current_emotional_sophistication_level, _interaction_counter
    _current_emotional_sophistication_level = 1
    _interaction_counter = 0
    logging.info("Emotional state reset for testing.")

def _test_skill(context: Any) -> None:
    """Tests the emotion skill operations."""
    logging.info("EmotionSkill Test: Starting...")
    reset_emotional_state_for_test()

    # Test initial level (Level 1)
    logging.info("EmotionSkill Test: Testing initial level (1) responses.")
    test_emotions = ["happy", "sad", "curious", "surprised", "neutral"]
    for emotion_to_test in test_emotions:
        logging.info(f"EmotionSkill Test: Testing emotion '{emotion_to_test}' at Level 1.")
        express_emotion(context, emotion=emotion_to_test)
        assert context.get_last_spoken_message_for_test() is not None, f"No message spoken for emotion: {emotion_to_test}"
        last_spoken_message = context.get_last_spoken_message_for_test()
        # Determine the emotional level *after* the express_emotion call, as this is the level of the actual response.
        level_of_actual_expression = _current_emotional_sophistication_level

        # Log for clarity, similar to what's seen in the provided logs from the main system
        logging.info(f"Expressed emotion '{emotion_to_test}' (Level {level_of_actual_expression}): {last_spoken_message}")

        expected_responses_for_level = EMOTIONAL_RESPONSES[emotion_to_test].get(f"level_{level_of_actual_expression}", [])
        assert last_spoken_message in expected_responses_for_level, \
               f"Spoken message for {emotion_to_test} (expressed at L{level_of_actual_expression}) not in L{level_of_actual_expression} responses. Got: '{last_spoken_message}'"
        context.clear_spoken_messages_for_test()

    # Test unknown emotion (should use fallback)
    logging.info("EmotionSkill Test: Testing unknown emotion 'excited'.")
    express_emotion(context, emotion="excited")
    assert "not quite sure how to express 'excited'" in context.get_last_spoken_message_for_test(), "Fallback for unknown emotion failed."
    context.clear_spoken_messages_for_test()

    # Test custom message (should bypass levels)
    custom_text = "This is a custom emotional statement."
    logging.info(f"EmotionSkill Test: Testing custom message with hint 'happy': '{custom_text}'.")
    express_emotion(context, emotion="happy", custom_message=custom_text)
    assert context.get_last_spoken_message_for_test() == custom_text, "Custom message not spoken correctly."
    context.clear_spoken_messages_for_test()

    # Test forced evolution
    logging.info("EmotionSkill Test: Forcing emotional evolution to Level 2.")
    reset_emotional_state_for_test() # Ensure we start from L1 for this specific test
    context.clear_spoken_messages_for_test() # Clear any messages from context if reset_emotional_state_for_test were to speak
    force_emotional_evolution(context, levels_to_increase=1)
    assert _current_emotional_sophistication_level == 2
    assert "manually advanced" in context.get_last_spoken_message_for_test().lower()
    context.clear_spoken_messages_for_test()

    logging.info("EmotionSkill Test: Testing 'happy' at Level 2.")
    express_emotion(context, emotion="happy")
    assert context.get_last_spoken_message_for_test() in EMOTIONAL_RESPONSES["happy"]["level_2"], "Happy L2 response incorrect."
    context.clear_spoken_messages_for_test()

    # Test automatic evolution by calling express_emotion enough times
    logging.info(f"EmotionSkill Test: Testing automatic evolution after {INTERACTIONS_PER_EVOLUTION_STEP} interactions (currently at L2).")
    reset_emotional_state_for_test() # Reset to L1 for this specific test segment
    force_emotional_evolution(context, 1) # Get to L2
    context.clear_spoken_messages_for_test() # Clear evolution message
    for i in range(INTERACTIONS_PER_EVOLUTION_STEP):
        express_emotion(context, emotion="neutral") # Use neutral to trigger counter
        if i < INTERACTIONS_PER_EVOLUTION_STEP -1 : # Don't clear the evolution message on the last one
            context.clear_spoken_messages_for_test() 
    
    assert _current_emotional_sophistication_level == MAX_EMOTIONAL_SOPHISTICATION_LEVEL # Should be 3 if MAX is 3
    
    # When automatic evolution occurs during an express_emotion call:
    # 1. _attempt_emotional_evolution speaks the "expanding" message.
    # 2. express_emotion then speaks the actual emotional response for the new level.
    # Both messages will be in context.spoken_messages_during_mute from that single call.
    messages_after_evolution_trigger = context.spoken_messages_during_mute
    assert len(messages_after_evolution_trigger) >= 2, \
        f"Expected at least two messages (evolution + emotion) after evolution, got {len(messages_after_evolution_trigger)}: {messages_after_evolution_trigger}"
    assert "expanding" in messages_after_evolution_trigger[0].lower(), \
           f"Automatic evolution message not found as the first message. Got: '{messages_after_evolution_trigger[0]}'"
    context.clear_spoken_messages_for_test()

    logging.info("EmotionSkill Test: Testing 'sad' at Max Level (3).")
    express_emotion(context, emotion="sad")
    assert context.get_last_spoken_message_for_test() in EMOTIONAL_RESPONSES["sad"]["level_3"], "Sad L3 response incorrect."
    context.clear_spoken_messages_for_test()

    # Test trying to evolve past max
    logging.info("EmotionSkill Test: Testing forcing evolution past max level.")
    force_emotional_evolution(context, levels_to_increase=1) # Already at max
    assert _current_emotional_sophistication_level == MAX_EMOTIONAL_SOPHISTICATION_LEVEL
    assert "peak emotional sophistication" in context.get_last_spoken_message_for_test().lower()
    context.clear_spoken_messages_for_test()

    reset_emotional_state_for_test() # Clean up
    logging.info("EmotionSkill Test: Completed successfully.")