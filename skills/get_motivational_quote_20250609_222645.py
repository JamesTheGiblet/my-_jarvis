# Proposed new skill generated by Praxis on 2025-06-09T22:26:45.775572
# Task: a skill that tells a very short, one-line motivational quote

# skills/motivational_quote.py
# (Generated by Praxis Autonomous Learning Agent)

import logging
from typing import Any
import random

logging.basicConfig(level=logging.INFO)

def get_motivational_quote(context: Any):
    """
    Provides a short, one-line motivational quote to the user.

    Args:
        context: An object providing access to user interaction and user data.  Must have a `speak(str)` method.
    """
    quotes = [
        "The only way to do great work is to love what you do.",
        "Believe you can and you're halfway there.",
        "The future belongs to those who believe in the beauty of their dreams.",
        "Keep your face always toward the sunshine, and shadows will fall behind you.",
        "The best and most beautiful things in the world cannot be seen or even touched - they must be felt with the heart."
    ]
    quote = random.choice(quotes)
    context.speak(f"Here's a little motivation for you, {context.current_user_name}: {quote}")


def _test_skill(context: Any):
    """
    Tests the get_motivational_quote skill.
    """
    logging.info("Starting test for get_motivational_quote skill...")
    try:
        get_motivational_quote(context)
        logging.info("get_motivational_quote skill executed successfully.")
        context.speak("Motivational quote test completed successfully!")
    except Exception as e:
        logging.error(f"Error during get_motivational_quote skill test: {e}")
        context.speak(f"Motivational quote test failed: {e}")

import random # added for random quote selection