# skills / maths_tool.py

import math 
import logging # Use standard logging
from typing import Union # For type hinting numbers

# Helper functions remain private, skill functions will call them.
def _add(a: float, b: float) -> float:
    return a + b

def _subtract(a: float, b: float) -> float:
    return a - b

def _multiply(a: float, b: float) -> float:
    return a * b

def _divide(a: float, b: float) -> float:
    if b == 0:
        raise ValueError("Division by zero is not allowed.")
    return a / b

def _power(base: float, exponent: float) -> float:
    return math.pow(base, exponent)

def _log(number: float, base: float = math.e) -> float:
    if number <= 0:
        raise ValueError("Logarithm undefined for non-positive numbers.")
    if base <= 0 or base == 1:
        raise ValueError("Logarithm base must be positive and not equal to 1.")
    return math.log(number, base)

def _sin(angle_degrees: float) -> float:
    return math.sin(math.radians(angle_degrees))

def _cos(angle_degrees: float) -> float:
    return math.cos(math.radians(angle_degrees))

# --- New Skill Functions ---

def calculate_add(context, number1: Union[int, float], number2: Union[int, float]):
    """Adds two numbers."""
    try:
        num1_float, num2_float = float(number1), float(number2)
        result = _add(num1_float, num2_float)
        context.speak(f"The sum of {num1_float} and {num2_float} is {result}.")
        logging.info(f"Calculated sum: {num1_float} + {num2_float} = {result}")
    except ValueError:
        context.speak("Sir, please provide valid numbers for addition.")
    except Exception as e:
        context.speak(f"An error occurred during addition: {str(e)}")
        logging.error(f"Error in calculate_add: {e}", exc_info=True)

def calculate_subtract(context, number1: Union[int, float], number2: Union[int, float]):
    """Subtracts the second number from the first."""
    try:
        num1_float, num2_float = float(number1), float(number2)
        result = _subtract(num1_float, num2_float)
        context.speak(f"The difference between {num1_float} and {num2_float} is {result}.")
        logging.info(f"Calculated difference: {num1_float} - {num2_float} = {result}")
    except ValueError:
        context.speak("Sir, please provide valid numbers for subtraction.")
    except Exception as e:
        context.speak(f"An error occurred during subtraction: {str(e)}")
        logging.error(f"Error in calculate_subtract: {e}", exc_info=True)

def calculate_multiply(context, number1: Union[int, float], number2: Union[int, float]):
    """Multiplies two numbers."""
    try:
        num1_float, num2_float = float(number1), float(number2)
        result = _multiply(num1_float, num2_float)
        context.speak(f"The product of {num1_float} and {num2_float} is {result}.")
        logging.info(f"Calculated product: {num1_float} * {num2_float} = {result}")
    except ValueError:
        context.speak("Sir, please provide valid numbers for multiplication.")
    except Exception as e:
        context.speak(f"An error occurred during multiplication: {str(e)}")
        logging.error(f"Error in calculate_multiply: {e}", exc_info=True)

def calculate_divide(context, number1: Union[int, float], number2: Union[int, float]):
    """Divides the first number by the second."""
    try:
        num1_float, num2_float = float(number1), float(number2)
        result = _divide(num1_float, num2_float)
        context.speak(f"The result of dividing {num1_float} by {num2_float} is {result}.")
        logging.info(f"Calculated division: {num1_float} / {num2_float} = {result}")
    except ValueError as e: # Catches division by zero and invalid number format
        context.speak(f"Sir, I encountered an issue with the division: {str(e)}")
    except Exception as e:
        context.speak(f"An error occurred during division: {str(e)}")
        logging.error(f"Error in calculate_divide: {e}", exc_info=True)

def calculate_power(context, base: Union[int, float], exponent: Union[int, float]):
    """Raises the base to the power of the exponent."""
    try:
        base_float, exponent_float = float(base), float(exponent)
        result = _power(base_float, exponent_float)
        context.speak(f"{base_float} raised to the power of {exponent_float} is {result}.")
        logging.info(f"Calculated power: {base_float} ** {exponent_float} = {result}")
    except ValueError:
        context.speak("Sir, please provide valid numbers for the power calculation.")
    except Exception as e:
        context.speak(f"An error occurred during the power calculation: {str(e)}")
        logging.error(f"Error in calculate_power: {e}", exc_info=True)

def calculate_log(context, number: Union[int, float], log_base: Union[int, float] = math.e):
    """Calculates the logarithm of a number with an optional base (default is natural log)."""
    try:
        number_float, base_float = float(number), float(log_base)
        result = _log(number_float, base_float)
        base_str = f"base {base_float}" if base_float != math.e else "natural log"
        context.speak(f"The {base_str} of {number_float} is {result}.")
        logging.info(f"Calculated log (base {base_float}) of {number_float} = {result}")
    except ValueError as e: # Catches invalid number/base for log
        context.speak(f"Sir, there was an issue with the logarithm calculation: {str(e)}")
    except Exception as e:
        context.speak(f"An error occurred during the logarithm calculation: {str(e)}")
        logging.error(f"Error in calculate_log: {e}", exc_info=True)

def calculate_sine(context, angle_degrees: Union[int, float]):
    """Calculates the sine of an angle given in degrees."""
    try:
        angle_float = float(angle_degrees)
        result = _sin(angle_float)
        context.speak(f"The sine of {angle_float} degrees is {result:.4f}.") # Format for trig functions
        logging.info(f"Calculated sine of {angle_float} degrees = {result}")
    except ValueError:
        context.speak("Sir, please provide a valid angle in degrees for sine calculation.")
    except Exception as e:
        context.speak(f"An error occurred during sine calculation: {str(e)}")
        logging.error(f"Error in calculate_sine: {e}", exc_info=True)

def calculate_cosine(context, angle_degrees: Union[int, float]):
    """Calculates the cosine of an angle given in degrees."""
    try:
        angle_float = float(angle_degrees)
        result = _cos(angle_float)
        context.speak(f"The cosine of {angle_float} degrees is {result:.4f}.")
        logging.info(f"Calculated cosine of {angle_float} degrees = {result}")
    except ValueError:
        context.speak("Sir, please provide a valid angle in degrees for cosine calculation.")
    except Exception as e:
        context.speak(f"An error occurred during cosine calculation: {str(e)}")
        logging.error(f"Error in calculate_cosine: {e}", exc_info=True)