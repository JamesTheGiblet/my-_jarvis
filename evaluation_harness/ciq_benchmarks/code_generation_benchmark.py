# evaluation_harness/ciq_benchmarks/code_generation_benchmark.py
import os
import sys
import subprocess
import logging
from typing import Tuple, Optional, List, Dict, Any

from evaluation_harness.benchmarks_base import CIQBenchmarkBase
from brain import generate_code_with_llm # Assuming brain.py is in project_root
from config import model as llm_model # Use the configured Gemini model

GENERATED_SOLUTION_FILENAME = "generated_solution.py"

class CodeGenerationBenchmark(CIQBenchmarkBase):
    def __init__(self, problem_name: str, problem_dir: str, k_attempts: int = 3):
        super().__init__(name=f"CodeGeneration_{problem_name}")
        self.problem_name = problem_name
        self.problem_dir = problem_dir
        self.k_attempts = k_attempts
        self.prompt_file = os.path.join(self.problem_dir, "prompt.md")
        self.tests_file = os.path.join(self.problem_dir, "tests.py")
        self.generated_code_path = os.path.join(self.problem_dir, GENERATED_SOLUTION_FILENAME)

    def load_data(self, data_path: Optional[str] = None) -> None:
        # Data (prompt and tests) are inherent to the problem_dir
        if not os.path.exists(self.prompt_file):
            self.logger.error(f"Prompt file not found: {self.prompt_file}")
            raise FileNotFoundError(f"Prompt file not found: {self.prompt_file}")
        if not os.path.exists(self.tests_file):
            self.logger.error(f"Tests file not found: {self.tests_file}")
            raise FileNotFoundError(f"Tests file not found: {self.tests_file}")
        self.logger.info(f"Data for {self.name} seems to be in place.")

    def run(self, praxis_instance: Optional[Any] = None, **kwargs) -> Dict[str, Any]:
        """
        Runs this specific code generation benchmark.
        Returns a dictionary containing:
            'passed': bool,
            'details': str,
            'cumulative_prompt_tokens': int,
            'cumulative_response_tokens': int
        """
        with open(self.prompt_file, "r", encoding="utf-8") as f:
            problem_description = f.read()

        cumulative_prompt_tokens = 0
        cumulative_response_tokens = 0
        last_faulty_code: Optional[str] = None
        last_error_output: Optional[str] = None

        for attempt in range(1, self.k_attempts + 1):
            self.logger.info(f"Attempt {attempt}/{self.k_attempts}: Requesting code generation...")
            
            current_p_tokens: int
            current_r_tokens: int
            generated_code_text: Optional[str]

            if attempt > 1 and last_faulty_code is not None and last_error_output is not None:
                generated_code_text, current_p_tokens, current_r_tokens = generate_code_with_llm(
                    problem_description, llm_model, attempt_number=attempt,
                    previous_code=last_faulty_code, error_message=last_error_output
                )
            else:
                generated_code_text, current_p_tokens, current_r_tokens = generate_code_with_llm(
                    problem_description, llm_model, attempt_number=attempt
                )
            
            cumulative_prompt_tokens += current_p_tokens
            cumulative_response_tokens += current_r_tokens

            if not generated_code_text or not generated_code_text.strip():
                self.logger.error(f"Attempt {attempt}/{self.k_attempts}: LLM failed to generate code or returned empty.")
                last_faulty_code = generated_code_text if generated_code_text is not None else ""
                last_error_output = "LLM failed to generate code or returned empty."
                if attempt == self.k_attempts:
                    return {"passed": False, "details": f"LLM failed/empty after {self.k_attempts} attempts.", "cumulative_prompt_tokens": cumulative_prompt_tokens, "cumulative_response_tokens": cumulative_response_tokens}
                continue

            with open(self.generated_code_path, "w", encoding="utf-8") as f:
                f.write(generated_code_text)
            self.logger.info(f"Attempt {attempt}/{self.k_attempts}: Generated code saved.")

            try:
                process = subprocess.run(
                    [sys.executable, self.tests_file], cwd=self.problem_dir,
                    capture_output=True, text=True, timeout=30
                )
                if process.returncode == 0:
                    self.logger.info(f"Tests PASSED on attempt {attempt}/{self.k_attempts}.")
                    return {"passed": True, "details": f"Tests Passed on attempt {attempt}.", "cumulative_prompt_tokens": cumulative_prompt_tokens, "cumulative_response_tokens": cumulative_response_tokens}
                else:
                    self.logger.warning(f"Attempt {attempt}/{self.k_attempts}: Tests FAILED. Output:\n{process.stderr or process.stdout}")
                    last_faulty_code = generated_code_text
                    last_error_output = (process.stderr or process.stdout).strip()
            except subprocess.TimeoutExpired:
                self.logger.error(f"Attempt {attempt}/{self.k_attempts}: Tests timed out.")
                last_faulty_code = generated_code_text
                last_error_output = "Test execution timed out."
            except Exception as e:
                self.logger.error(f"Attempt {attempt}/{self.k_attempts}: Error running tests: {e}", exc_info=True)
                last_faulty_code = generated_code_text
                last_error_output = f"Exception during test execution: {e}"
            finally:
                if os.path.exists(self.generated_code_path): os.remove(self.generated_code_path)
                pycache_dir = os.path.join(self.problem_dir, "__pycache__")
                if os.path.exists(pycache_dir):
                    import shutil
                    shutil.rmtree(pycache_dir)
            
            if attempt == self.k_attempts: # Last attempt failed
                return {"passed": False, "details": f"Tests Failed after {self.k_attempts} attempts. Last error:\n{last_error_output}", "cumulative_prompt_tokens": cumulative_prompt_tokens, "cumulative_response_tokens": cumulative_response_tokens}

        return {"passed": False, "details": f"All {self.k_attempts} attempts failed.", "cumulative_prompt_tokens": cumulative_prompt_tokens, "cumulative_response_tokens": cumulative_response_tokens}

    def calculate_metrics(self, run_results: Dict[str, Any]) -> Dict[str, Any]:
        # For this benchmark, run_results already contains the primary metrics
        return run_results