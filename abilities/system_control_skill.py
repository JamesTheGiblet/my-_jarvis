# skills/system_control_skill.py
import logging
from typing import Any

def set_input_mode_text(context: Any) -> None:
    """Switches the primary input method for Praxis to text-based commands."""
    if context.input_mode_config['mode'] == 'text':
        context.speak("I am already in text input mode, sir.")
    else:
        context.input_mode_config['mode'] = 'text'
        context.speak("Understood. Switching to text input mode.")
        logging.info("Input mode switched to text by skill.")

def set_input_mode_voice(context: Any) -> None:
    """Switches the primary input method for Praxis to voice-based commands, if available."""
    if not context.speech_recognition_available:
        context.speak("I'm sorry, voice input is currently unavailable on this system.")
        logging.warning("Attempted to switch to voice input, but SR is not available.")
        return

    if context.input_mode_config['mode'] == 'voice':
        context.speak("I am already in voice input mode, sir.")
    else:
        context.input_mode_config['mode'] = 'voice'
        context.speak("Understood. Switching to voice input mode. I'll be listening.")
        logging.info("Input mode switched to voice by skill.")

def _test_skill(context: Any) -> None:
    """Tests the system control skills."""
    logging.info("SystemControlSkill: _test_skill called.")
    
    original_mode = context.input_mode_config['mode']
    
    logging.info("SystemControlSkill: Testing switch to text mode.")
    set_input_mode_text(context)
    assert context.input_mode_config['mode'] == 'text', "Failed to switch to text mode"
    assert "Switching to text input mode" in context.get_last_spoken_message_for_test()
    context.clear_spoken_messages_for_test()

    if context.speech_recognition_available:
        logging.info("SystemControlSkill: Testing switch to voice mode.")
        set_input_mode_voice(context)
        assert context.input_mode_config['mode'] == 'voice', "Failed to switch to voice mode"
        assert "Switching to voice input mode" in context.get_last_spoken_message_for_test()
        context.clear_spoken_messages_for_test()
    else:
        logging.info("SystemControlSkill: Skipping voice mode test as SR is not available.")
        set_input_mode_voice(context)
        assert "voice input is currently unavailable" in context.get_last_spoken_message_for_test()
        assert context.input_mode_config['mode'] == 'text', "Mode should remain text if SR unavailable"
        context.clear_spoken_messages_for_test()

    context.input_mode_config['mode'] = original_mode # Restore original mode
    logging.info(f"SystemControlSkill: Restored original input mode to '{original_mode}'.")
    logging.info("SystemControlSkill: _test_skill completed.")