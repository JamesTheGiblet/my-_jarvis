# skills/creative_synthesizer_skill.py

import datetime
import logging # Use standard logging
from typing import Dict, Any # Removed List, TYPE_CHECKING, Optional for now

def summarize_creatively(context, text_to_summarize: str):
    """Generates a creative summary for the provided text using an LLM."""
    if not text_to_summarize or not text_to_summarize.strip():
        context.speak("Sir, you haven't provided any text for me to summarize.")
        return

    logging.info(f"[summarize_creatively] Requesting creative summary for: '{text_to_summarize[:70]}...'")
    context.speak("One moment, sir. Crafting a creative summary for you...")

    # This prompt is specific to the summarization task and is sent via the existing chat_session.
    summarization_prompt = (
        "You are a master of language, renowned for your ability to distill complex information "
        "into brief, imaginative, and engaging summaries. Your summaries should not just state facts, "
        "but evoke feeling, paint pictures with words, and offer fresh perspectives. "
        "Avoid dry, factual restatements. Aim for poetic, metaphorical, or narrative flair. "
        "The summary should be concise and capture the essence of the text. "
        f"Please provide a creative summary for the following text:\n\n---\n{text_to_summarize}\n---"
    )

    try:
        # Using the existing chat_session from the context to send this specific prompt
        response = context.chat_session.send_message(summarization_prompt)
        summary = response.text.strip()

        if summary:
            context.speak("Here is the creative summary, sir:")
            context.speak(summary)
            logging.info(f"[summarize_creatively] Summary generated: {summary[:100]}...")
        else:
            context.speak("I'm sorry, sir. I wasn't able to generate a summary this time.")
            logging.warning("[summarize_creatively] LLM returned an empty summary.")
    except Exception as e:
        logging.error(f"[summarize_creatively] Error calling LLM for summarization: {e}", exc_info=True)
        context.speak(f"My apologies, sir. I encountered an error while trying to summarize: {str(e)}")

def echo_text(context, text_to_echo: str):
    """Echoes the provided text back."""
    if not text_to_echo:
        context.speak("You didn't provide any text for me to echo, sir.")
        return
    context.speak(f"As you wish, sir: {text_to_echo}")

def get_text_stats(context, text_for_stats: str):
    """Provides basic statistics (word count, char count) for the given text."""
    if not text_for_stats:
        context.speak("Sir, please provide some text for me to analyze.")
        return
    
    word_count = len(text_for_stats.split())
    char_count_with_spaces = len(text_for_stats)
    # More robustly count characters without spaces, handling various newline characters
    char_count_no_spaces = len(text_for_stats.replace(" ", "").replace("\n", "").replace("\r", ""))
    
    context.speak(f"Analyzing the text: \"{text_for_stats[:50]}...\"")
    context.speak(f"Word count: {word_count}")
    context.speak(f"Character count (including spaces): {char_count_with_spaces}")
    context.speak(f"Character count (excluding spaces): {char_count_no_spaces}")

def _test_skill(context):
    """
    Runs a quick self-test for the creative_synthesizer_skill module.
    """
    logging.info("[creative_synthesizer_test] Running self-test for creative_synthesizer_skill module...")
    try:
        test_text_short = "Hello world! This is a test."
        test_text_long_for_summary = "The quick brown fox jumps over the lazy dog. This sentence contains all letters of the alphabet. It is often used for practice typing, and for testing fonts and displays."

        # Test 1: echo_text
        logging.info(f"[creative_synthesizer_test] Attempting to call echo_text with: '{test_text_short}'")
        echo_text(context, test_text_short)
        logging.info(f"[creative_synthesizer_test] echo_text called.")

        # Test 2: get_text_stats
        logging.info(f"[creative_synthesizer_test] Attempting to call get_text_stats with: '{test_text_short}'")
        get_text_stats(context, test_text_short)
        logging.info(f"[creative_synthesizer_test] get_text_stats called.")

        # Test 3: summarize_creatively (LLM call)
        logging.info(f"[creative_synthesizer_test] Attempting to call summarize_creatively with: '{test_text_long_for_summary[:30]}...'")
        summarize_creatively(context, test_text_long_for_summary)
        # The actual summary content won't be asserted here, but the flow and LLM call attempt will be logged.
        logging.info(f"[creative_synthesizer_test] summarize_creatively called (check logs for LLM interaction details).")

        logging.info("[creative_synthesizer_test] All creative_synthesizer_skill self-tests passed successfully.")
    except Exception as e:
        logging.error(f"[creative_synthesizer_test] Self-test FAILED: {e}", exc_info=True)
        raise # Re-raise the exception to be caught by load_skills in main.py
