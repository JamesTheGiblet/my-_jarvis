# skills/data_analysis_skill.py

import statistics
from collections import Counter
import re
import logging # Use standard logging
from typing import Any, Dict, List, Union # Added Union

# If DEFAULT_STOP_WORDS was from a shared config and is a simple list,
# define it here or ensure config.py is accessible in the Python path.
# For simplicity, let's assume it's a short list or handle its absence.
DEFAULT_STOP_WORDS = set([
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "should",
    "can", "could", "may", "might", "must", "and", "but", "or", "nor",
    "for", "so", "yet", "in", "on", "at", "by", "from", "to", "with",
    "about", "above", "after", "again", "against", "all", "am", "as",
    "because", "before", "below", "between", "both", "during", "each",
    "few", "further", "he", "her", "here", "hers", "herself", "him",
    "himself", "his", "how", "i", "if", "into", "it", "its", "itself",
    "let", "me", "more", "most", "my", "myself", "no", "not", "now",
    "of", "off", "once", "only", "other", "our", "ours", "ourselves",
    "out", "over", "own", "same", "she", "since", "some", "still",
    "such", "than", "that", "their", "theirs", "them", "themselves",
    "then", "there", "these", "they", "this", "those", "through",
    "too", "under", "until", "up", "very", "we", "what", "when",
    "where", "which", "while", "who", "whom", "why", "with", "you",
    "your", "yours", "yourself", "yourselves"
])

def analyze_log_summary(context, log_entries: List[Dict[str, str]]):
    """
    Generates a simple summary of log data.
    Args:
        context: The skill context.
        log_entries (List[Dict[str, str]]): A list of log entry dictionaries. 
                                            Example: [{"level": "INFO", "message": "User logged in"}]
    """
    if not log_entries:
        context.speak("Sir, there are no log entries to summarize.")
        return
    
    num_entries = len(log_entries)
    level_counts = Counter(entry.get("level", "UNKNOWN").upper() for entry in log_entries)
    
    context.speak(f"Log summary: Processed {num_entries} entries.")
    if level_counts:
        context.speak("Entry levels found:")
        for level, count in level_counts.items():
            context.speak(f"- {level}: {count}")
    logging.info(f"Analyzed log summary for {num_entries} entries. Levels: {level_counts}")

def analyze_data_complexity(context, data_items: List[Any]):
    """
    Analyzes the complexity of provided data using a simplified score.
    Args:
        context: The skill context.
        data_items (List[Any]): A list of data items (can be mixed types).
    """
    if not data_items:
        context.speak("No data items provided for complexity analysis, sir.")
        return
    
    complexity_score = sum(len(str(item)) for item in data_items) * 0.1 # Original simple metric
    context.speak(f"The simplified complexity score for the provided data is: {complexity_score:.2f}")
    logging.info(f"Calculated complexity score: {complexity_score} for {len(data_items)} items.")

def analyze_basic_statistics(context, numbers: List[Union[int, float]]):
    """
    Calculates basic statistics (mean, count) for numerical data.
    Args:
        context: The skill context.
        numbers (List[Union[int, float]]): A list of numbers.
    """
    if not numbers or not all(isinstance(n, (int, float)) for n in numbers):
        context.speak("Sir, please provide a list of numbers for basic statistical analysis.")
        return

    mean_val = statistics.mean(numbers)
    count_val = len(numbers)
    context.speak(f"Basic statistics: Count is {count_val}, Mean is {mean_val:.2f}.")
    logging.info(f"Calculated basic stats: count={count_val}, mean={mean_val} for input: {numbers}")

def analyze_advanced_statistics(context, numbers: List[Union[int, float]]):
    """
    Calculates advanced statistics (median, standard deviation) for numerical data.
    Args:
        context: The skill context.
        numbers (List[Union[int, float]]): A list of numbers.
    """
    if not numbers or not all(isinstance(n, (int, float)) for n in numbers):
        context.speak("Sir, please provide a list of numbers for advanced statistical analysis.")
        return
    
    if len(numbers) < 2:
        median_val = numbers[0] if numbers else "N/A"
        stdev_val = 0 if numbers else "N/A"
        context.speak(f"Advanced statistics: Median is {median_val}. Standard deviation is {stdev_val} (requires at least two data points for meaningful stdev).")
    else:
        median_val = statistics.median(numbers)
        stdev_val = statistics.stdev(numbers)
        context.speak(f"Advanced statistics: Median is {median_val:.2f}, Standard Deviation is {stdev_val:.2f}.")
    logging.info(f"Calculated advanced stats: median={median_val}, stdev={stdev_val} for input: {numbers}")

def search_keywords_in_text(context, texts: List[str], keywords: List[str]):
    """
    Searches for keywords in a list of text strings.
    Args:
        context: The skill context.
        texts (List[str]): A list of text strings to search within.
        keywords (List[str]): A list of keywords to search for.
    """
    if not texts or not keywords:
        context.speak("Sir, I need both texts to search in and keywords to search for.")
        return

    results = {}
    normalized_keywords = [kw.lower() for kw in keywords]

    for i, text_item in enumerate(texts):
        found_kws = []
        normalized_text = text_item.lower()
        for kw in normalized_keywords:
            if kw in normalized_text:
                found_kws.append(kw)
        if found_kws:
            results[f"Text {i+1} (preview: '{text_item[:30]}...')"] = found_kws
    
    if results:
        context.speak("Keyword search results:")
        for text_ref, kws_found in results.items():
            context.speak(f"- In {text_ref}: found {', '.join(kws_found)}")
    else:
        context.speak(f"No occurrences of the keywords ({', '.join(keywords)}) were found in the provided texts.")
    logging.info(f"Keyword search for '{keywords}' in {len(texts)} texts. Results: {results}")

def match_regex_in_text(context, texts: List[str], regex_pattern: str):
    """
    Matches a regex pattern in a list of text strings.
    Args:
        context: The skill context.
        texts (List[str]): A list of text strings to search within.
        regex_pattern (str): The regular expression pattern to match.
    """
    if not texts or not regex_pattern:
        context.speak("Sir, I need texts and a regex pattern to perform the match.")
        return
    
    try:
        pattern = re.compile(regex_pattern)
    except re.error as e:
        context.speak(f"The provided regex pattern is invalid, sir: {e}")
        logging.error(f"Invalid regex pattern '{regex_pattern}': {e}")
        return

    results = {}
    for i, text_item in enumerate(texts):
        matches = pattern.findall(text_item)
        if matches:
            results[f"Text {i+1} (preview: '{text_item[:30]}...')"] = matches
            
    if results:
        context.speak(f"Regex pattern '{regex_pattern}' match results:")
        for text_ref, match_list in results.items():
            context.speak(f"- In {text_ref}: found {', '.join(map(str,match_list))}")
    else:
        context.speak(f"No matches for the regex pattern '{regex_pattern}' were found in the provided texts.")
    logging.info(f"Regex match for pattern '{regex_pattern}' in {len(texts)} texts. Results: {results}")

def analyze_correlation(context, series_data: Dict[str, List[Union[int, float]]]):
    """
    Calculates correlation between two numerical series from a dictionary.
    Args:
        context: The skill context.
        series_data (Dict[str, List[Union[int, float]]]): A dictionary where keys are series names 
                                                          and values are lists of numbers.
                                                          Example: {"series_a": [1,2,3], "series_b": [2,4,6]}
    """
    if not series_data or len(series_data) < 2:
        context.speak("Sir, I need at least two numerical series to calculate correlation.")
        return

    series_names = list(series_data.keys())
    series_values = list(series_data.values())

    # Validate series
    for i, s_name in enumerate(series_names):
        if not isinstance(series_values[i], list) or not all(isinstance(n, (int, float)) for n in series_values[i]):
            context.speak(f"Series '{s_name}' does not contain a valid list of numbers, sir.")
            return
        if i > 0 and len(series_values[i]) != len(series_values[0]):
            context.speak("Sir, all series must have the same length to calculate correlation.")
            return
    
    if len(series_values[0]) < 2:
        context.speak("Correlation analysis requires at least two data points per series, sir.")
        return

    # For simplicity, calculate correlation between the first two series provided
    # A more advanced version could calculate a correlation matrix for multiple series.
    s1_name, s2_name = series_names[0], series_names[1]
    s1_vals, s2_vals = series_values[0], series_values[1]
    
    try:
        # Pearson correlation coefficient
        correlation_coefficient = statistics.correlation(s1_vals, s2_vals)
        context.speak(f"The Pearson correlation coefficient between '{s1_name}' and '{s2_name}' is {correlation_coefficient:.4f}.")
        logging.info(f"Calculated correlation between '{s1_name}' and '{s2_name}': {correlation_coefficient}")
    except statistics.StatisticsError as e:
        context.speak(f"Could not calculate correlation, sir. {e}")
        logging.error(f"StatisticsError during correlation: {e}")
    except Exception as e:
        context.speak(f"An unexpected error occurred during correlation analysis, sir: {e}")
        logging.error(f"Unexpected error during correlation: {e}", exc_info=True)

def _test_skill(context):
    """
    Runs a quick self-test for the data_analysis_skill module.
    """
    logging.info("[data_analysis_test] Running self-test for data_analysis_skill module...")
    try:
        # Sample data for testing
        sample_log_entries = [
            {"level": "INFO", "message": "User logged in"},
            {"level": "WARNING", "message": "Low disk space"},
            {"level": "INFO", "message": "Process completed"}
        ]
        sample_data_items = [1, "hello", [1, 2], {"key": "value"}, 3.14]
        sample_numbers = [10, 15, 20, 25, 30, 20]
        sample_texts = ["The quick brown fox.", "Jumps over the lazy dog.", "Python is fun."]
        sample_keywords = ["fox", "python"]
        sample_regex = r"\b\w{3}\b" # Matches 3-letter words
        sample_series_data = {
            "series_A": [1, 2, 3, 4, 5],
            "series_B": [2, 4, 6, 8, 10],
            "series_C": [5, 4, 3, 2, 1]
        }

        # Test 1: analyze_log_summary
        logging.info("[data_analysis_test] Testing analyze_log_summary...")
        analyze_log_summary(context, sample_log_entries)

        # Test 2: analyze_data_complexity
        logging.info("[data_analysis_test] Testing analyze_data_complexity...")
        analyze_data_complexity(context, sample_data_items)

        # Test 3: analyze_basic_statistics
        logging.info("[data_analysis_test] Testing analyze_basic_statistics...")
        analyze_basic_statistics(context, sample_numbers)

        # Test 4: analyze_advanced_statistics
        logging.info("[data_analysis_test] Testing analyze_advanced_statistics...")
        analyze_advanced_statistics(context, sample_numbers)

        # Test 5: search_keywords_in_text
        logging.info("[data_analysis_test] Testing search_keywords_in_text...")
        search_keywords_in_text(context, sample_texts, sample_keywords)

        # Test 6: match_regex_in_text
        logging.info("[data_analysis_test] Testing match_regex_in_text...")
        match_regex_in_text(context, sample_texts, sample_regex)

        # Test 7: analyze_correlation
        logging.info("[data_analysis_test] Testing analyze_correlation...")
        analyze_correlation(context, sample_series_data)

        logging.info("[data_analysis_test] All data_analysis_skill self-tests passed successfully.")

    except Exception as e:
        logging.error(f"[data_analysis_test] Self-test FAILED: {e}", exc_info=True)
        raise # Re-raise the exception to be caught by load_skills in main.py