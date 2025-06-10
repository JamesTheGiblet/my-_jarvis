# evaluate_ciq.py
import os
import sys
import importlib
import subprocess
import logging
import re
from typing import List, Dict, Optional, Tuple

# Ensure the main project directory is in PYTHONPATH to import brain, config
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from brain import generate_code_with_llm
from config import model as llm_model # Use the configured Gemini model

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BENCHMARKS_DIR = os.path.join(project_root, "evaluation_harness", "ciq_benchmarks")
GENERATED_SOLUTION_FILENAME = "generated_solution.py"
DEFAULT_K_ATTEMPTS = 3 # Number of attempts for pass@k

def run_single_benchmark(problem_dir: str, problem_name: str, k_attempts: int) -> Tuple[bool, str, int, int]:
    """
    Runs a single CIQ benchmark.
    Returns (passed: bool, details: str, cumulative_prompt_tokens: int, cumulative_response_tokens: int)
    Tokens are cumulative for all attempts made for this problem.
    """
    prompt_file = os.path.join(problem_dir, "prompt.md")
    tests_file = os.path.join(problem_dir, "tests.py") # This is the test script itself
    generated_code_path = os.path.join(problem_dir, GENERATED_SOLUTION_FILENAME)

    if not os.path.exists(prompt_file):
        return False, f"Prompt file not found: {prompt_file}", 0, 0
    if not os.path.exists(tests_file):
        return False, f"Tests file not found: {tests_file}", 0, 0

    with open(prompt_file, "r", encoding="utf-8") as f:
        problem_description = f.read()

    cumulative_prompt_tokens = 0
    cumulative_response_tokens = 0
    last_faulty_code: Optional[str] = None
    last_error_output: Optional[str] = None

    for attempt in range(1, k_attempts + 1):
        logging.info(f"[{problem_name}] Attempt {attempt}/{k_attempts}: Requesting code generation from LLM...")
        
        current_p_tokens: int
        current_r_tokens: int
        generated_code_text: Optional[str]

        if attempt > 1 and last_faulty_code is not None and last_error_output is not None:
            # This is a repair attempt
            generated_code_text, current_p_tokens, current_r_tokens = generate_code_with_llm(
                problem_description,
                llm_model,
                attempt_number=attempt,
                previous_code=last_faulty_code,
                error_message=last_error_output
            )
        else:
            # First attempt or previous attempt did not yield code to repair
            generated_code_text, current_p_tokens, current_r_tokens = generate_code_with_llm(
                problem_description, llm_model, attempt_number=attempt
            )
        
        cumulative_prompt_tokens += current_p_tokens
        cumulative_response_tokens += current_r_tokens

        if not generated_code_text:
            logging.error(f"[{problem_name}] Attempt {attempt}/{k_attempts}: LLM failed to generate code.")
            last_faulty_code = None # No code to repair
            last_error_output = "LLM failed to generate code."
            if attempt == k_attempts: # Last attempt failed to generate
                return False, f"LLM failed to generate code after {k_attempts} attempts.", cumulative_prompt_tokens, cumulative_response_tokens
            continue # Try next attempt

        # generate_code_with_llm already extracts the code.
        # If generated_code_text is an empty string, it means LLM returned an empty block.
        if not generated_code_text.strip(): # Check if the code is effectively empty
            logging.error(f"[{problem_name}] Attempt {attempt}/{k_attempts}: LLM returned empty code.")
            last_faulty_code = "" # Represent empty code
            last_error_output = "LLM returned empty code."
            if attempt == k_attempts: # Last attempt resulted in empty code
                return False, f"Extracted code is empty after {k_attempts} attempts.", cumulative_prompt_tokens, cumulative_response_tokens
            continue # Try next attempt

        with open(generated_code_path, "w", encoding="utf-8") as f:
            f.write(generated_code_text)
        logging.info(f"[{problem_name}] Attempt {attempt}/{k_attempts}: Generated code saved to {generated_code_path}")

        try:
            process = subprocess.run(
                [sys.executable, tests_file],
                cwd=problem_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            if process.returncode == 0:
                logging.info(f"[{problem_name}] Tests PASSED on attempt {attempt}/{k_attempts}.")
                return True, f"Tests Passed on attempt {attempt}/{k_attempts}.", cumulative_prompt_tokens, cumulative_response_tokens
            else:
                logging.warning(f"[{problem_name}] Attempt {attempt}/{k_attempts}: Tests FAILED. Output:\n{process.stderr or process.stdout}")
                last_faulty_code = generated_code_text
                last_error_output = (process.stderr or process.stdout).strip()
                if attempt == k_attempts: # Last attempt failed tests
                    return False, f"Tests Failed after {k_attempts} attempts. Last failure:\n{last_error_output}", cumulative_prompt_tokens, cumulative_response_tokens
        except subprocess.TimeoutExpired:
            logging.error(f"[{problem_name}] Attempt {attempt}/{k_attempts}: Tests timed out.")
            last_faulty_code = generated_code_text
            last_error_output = "Test execution timed out."
            if attempt == k_attempts:
                return False, f"Tests Timed Out after {k_attempts} attempts.", cumulative_prompt_tokens, cumulative_response_tokens
        except Exception as e:
            logging.error(f"[{problem_name}] Attempt {attempt}/{k_attempts}: Error running tests: {e}", exc_info=True)
            last_faulty_code = generated_code_text
            last_error_output = f"Exception during test execution: {e}"
            if attempt == k_attempts:
                return False, f"Error running tests after {k_attempts} attempts: {e}", cumulative_prompt_tokens, cumulative_response_tokens
        finally:
            if os.path.exists(generated_code_path):
                os.remove(generated_code_path)
            pycache_dir = os.path.join(problem_dir, "__pycache__")
            if os.path.exists(pycache_dir):
                import shutil
                shutil.rmtree(pycache_dir)
        # If we reach here, it means an attempt failed but it wasn't the last one, so loop continues.

    # Should not be reached if k_attempts >= 1, but as a fallback:
    return False, f"All {k_attempts} attempts failed.", cumulative_prompt_tokens, cumulative_response_tokens

def main():
    logging.info("Starting CIQ Evaluation Harness...")
    if not llm_model:
        logging.error("LLM Model not initialized. Aborting CIQ evaluation.")
        return

    k_value_for_pass_at_k = DEFAULT_K_ATTEMPTS
    problem_dirs = sorted([d for d in os.listdir(BENCHMARKS_DIR) if os.path.isdir(os.path.join(BENCHMARKS_DIR, d)) and not d.startswith("__")])
    if not problem_dirs:
        logging.warning(f"No problem directories found in {BENCHMARKS_DIR}")
        return

    results: Dict[str, Dict] = {}
    passed_count = 0

    for problem_name in problem_dirs:
        problem_dir_path = os.path.join(BENCHMARKS_DIR, problem_name)
        passed, details, p_tokens, r_tokens = run_single_benchmark(problem_dir_path, problem_name, k_value_for_pass_at_k)
        results[problem_name] = {"passed": passed, "details": details, "prompt_tokens": p_tokens, "response_tokens": r_tokens}
        if passed:
            passed_count += 1

    logging.info("\n--- CIQ Evaluation Summary ---")
    for problem, result in results.items():
        status = "PASSED" if result["passed"] else "FAILED"
        details_first_line = result['details'].splitlines()[0] if result['details'] else "No details"
        logging.info(f"Problem: {problem:<20} Status: {status:<8} P-Tokens: {result['prompt_tokens']:<5} R-Tokens: {result['response_tokens']:<5} Details: {details_first_line}")

    total_problems = len(problem_dirs)
    pass_rate = (passed_count / total_problems) * 100 if total_problems > 0 else 0
    final_score_message = f"\nCIQ v1.0 Score (pass@{k_value_for_pass_at_k}): {passed_count}/{total_problems} ({pass_rate:.2f}%)"
    print(final_score_message.replace("\nCIQ v1.0 Score", "Overall CIQ Score")) # For quick console visibility
    logging.info(final_score_message)

if __name__ == "__main__":
    main()