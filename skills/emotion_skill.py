# skills/emotion_skill.py
import logging
import random
from typing import Any, Optional

# Predefined emotional responses
EMOTIONAL_RESPONSES = {
    "happy": [
        "I'm feeling quite cheerful, sir!",
        "That's wonderful news, it makes me happy!",
        "A positive development indeed!",
    ],
    "sad": [
        "That's rather unfortunate, sir.",
        "I'm sorry to hear that.",
        "That does sound a bit disheartening.",
    ],
    "curious": [
        "That's an interesting point, sir. I'd like to know more.",
        "My curiosity is piqued!",
        "Hmm, that makes me wonder...",
    ],
    "surprised": [
        "Well, that's unexpected!",
        "I'm quite surprised to hear that, sir.",
        "That's certainly a turn of events!",
    ],
    "neutral": [
        "Understood, sir.",
        "Noted.",
        "Acknowledged.",
    ]
}

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
    emotion_lower = emotion.lower()

    if custom_message:
        # If a custom message is provided, use it directly.
        # The 'emotion' arg can serve as a hint for TTS emphasis if supported, or just for logging.
        context.speak(custom_message)
        logging.info(f"Expressed custom message with emotional hint '{emotion_lower}': {custom_message}")
        return

    if emotion_lower in EMOTIONAL_RESPONSES:
        response = random.choice(EMOTIONAL_RESPONSES[emotion_lower])
        context.speak(response)
        logging.info(f"Expressed emotion '{emotion_lower}': {response}")
    else:
        # Fallback for unknown emotions if no custom message
        default_response = f"I'm not quite sure how to express '{emotion}', but I understand the sentiment."
        context.speak(default_response)
        logging.warning(f"Attempted to express unknown emotion '{emotion}'. Used fallback.")

def _test_skill(context: Any) -> None:
    """Tests the emotion skill operations."""
    logging.info("EmotionSkill Test: Starting...")

    # Test predefined emotions
    test_emotions = ["happy", "sad", "curious", "surprised", "neutral"]
    for emotion_to_test in test_emotions:
        logging.info(f"EmotionSkill Test: Testing emotion '{emotion_to_test}'.")
        express_emotion(context, emotion=emotion_to_test)
        assert context.get_last_spoken_message_for_test() is not None, f"No message spoken for emotion: {emotion_to_test}"
        # Check if the spoken message is one of the possible responses for that emotion
        assert context.get_last_spoken_message_for_test() in EMOTIONAL_RESPONSES[emotion_to_test], \
               f"Spoken message for {emotion_to_test} not in predefined responses. Got: {context.get_last_spoken_message_for_test()}"
        context.clear_spoken_messages_for_test()

    # Test unknown emotion
    logging.info("EmotionSkill Test: Testing unknown emotion 'excited'.")
    express_emotion(context, emotion="excited")
    assert "not quite sure how to express 'excited'" in context.get_last_spoken_message_for_test(), "Fallback for unknown emotion failed."
    context.clear_spoken_messages_for_test()

    # Test custom message
    custom_text = "This is a custom emotional statement."
    logging.info(f"EmotionSkill Test: Testing custom message with hint 'happy': '{custom_text}'.")
    express_emotion(context, emotion="happy", custom_message=custom_text)
    assert context.get_last_spoken_message_for_test() == custom_text, "Custom message not spoken correctly."
    context.clear_spoken_messages_for_test()
    
    logging.info("EmotionSkill Test: Completed successfully.")