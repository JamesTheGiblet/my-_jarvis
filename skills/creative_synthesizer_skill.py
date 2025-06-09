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

def get_creative_skill_current_date(context):
    """
    Gets the current date.
    Note: This functionality is similar to get_date in core_skills.py 
    and get_calendar_current_date in calendar.py. 
    Consider if this specific version is needed or if it can be consolidated.
    """
    current_date_str = datetime.date.today().isoformat()
    context.speak(f"Sir, according to my creative synthesizer module, the current date is {current_date_str}.")

# The __main__ block from the original file has been removed as it was
# for testing the class-based structure and is not directly applicable
# to testing these individual functions without mocking the 'context' object.
