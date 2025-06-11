# evaluate_ciq.py
import os
import sys
import logging
from typing import Dict, List

# Ensure the main project directory is in PYTHONPATH to import brain, config
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from config import model as llm_model
from evaluation_harness.ciq_benchmarks.code_generation_benchmark import CodeGenerationBenchmark

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BENCHMARKS_DIR = os.path.join(project_root, "evaluation_harness", "ciq_benchmarks")
DEFAULT_K_ATTEMPTS = 3 # Number of attempts for pass@k

def main():
    logging.info("Starting CIQ Evaluation Harness...")
    if not llm_model:
        logging.error("LLM Model not initialized. Aborting CIQ evaluation.")
        return

    # --- Discover and Instantiate Benchmarks ---
    # For now, we only have CodeGenerationBenchmark.
    # Future: This could be more dynamic, discovering classes inheriting from CIQBenchmarkBase.
    benchmarks_to_run: List[CodeGenerationBenchmark] = []
    
    # Discover code generation problems (subdirectories in BENCHMARKS_DIR)
    # Note: BENCHMARKS_DIR itself is ciq_benchmarks. Problems are subdirs within it.
    problem_subdirs_root = BENCHMARKS_DIR 
    if not os.path.isdir(problem_subdirs_root):
        logging.warning(f"Problem subdirectories root not found: {problem_subdirs_root}")
        return

    problem_names = sorted([
        d for d in os.listdir(problem_subdirs_root) 
        if os.path.isdir(os.path.join(problem_subdirs_root, d)) and not d.startswith("__")
    ])

    if not problem_names:
        logging.warning(f"No problem directories found in {problem_subdirs_root} for Code Generation.")
        # If you add other benchmark types, you might not want to return here.
        # For now, since it's the only type, we can.
        return

    for problem_name in problem_names:
        problem_dir_path = os.path.join(problem_subdirs_root, problem_name)
        benchmark_instance = CodeGenerationBenchmark(problem_name, problem_dir_path, k_attempts=DEFAULT_K_ATTEMPTS)
        benchmarks_to_run.append(benchmark_instance)

    # --- Run Benchmarks and Collect Results ---
    all_results: Dict[str, Dict] = {}
    passed_count = 0
    total_benchmarks_run = 0

    for benchmark in benchmarks_to_run:
        logging.info(f"Running CIQ Benchmark: {benchmark.name}...")
        benchmark.load_data() # Load data specific to this benchmark
        run_output = benchmark.run() # Pass praxis_instance if needed by other benchmarks
        metrics = benchmark.calculate_metrics(run_output)
        all_results[benchmark.name] = metrics
        if metrics.get("passed", False):
            passed_count += 1
        total_benchmarks_run +=1

    logging.info("\n--- CIQ Evaluation Summary ---")
    for problem, result in all_results.items():
        status = "PASSED" if result["passed"] else "FAILED"
        details_first_line = result['details'].splitlines()[0] if result['details'] else "No details"
        p_tokens = result.get('cumulative_prompt_tokens', 'N/A')
        r_tokens = result.get('cumulative_response_tokens', 'N/A')
        logging.info(f"Benchmark: {problem:<30} Status: {status:<8} P-Tokens: {p_tokens:<5} R-Tokens: {r_tokens:<5} Details: {details_first_line}")

    pass_rate = (passed_count / total_benchmarks_run) * 100 if total_benchmarks_run > 0 else 0
    # The concept of pass@k is specific to CodeGenerationBenchmark.
    # For a general CIQ score, you might average different types of scores later.
    final_score_message = f"\nCIQ Score (pass@{DEFAULT_K_ATTEMPTS} for CodeGen): {passed_count}/{total_benchmarks_run} ({pass_rate:.2f}%)"
    print(final_score_message.replace("\nCIQ v1.0 Score", "Overall CIQ Score")) # For quick console visibility
    logging.info(final_score_message)

if __name__ == "__main__":
    main()