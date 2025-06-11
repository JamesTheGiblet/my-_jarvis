# evaluate_ceq.py
import os
import sys
import logging
from typing import List, Dict, Any

# Ensure the main project directory is in PYTHONPATH
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

try:
    from main import PraxisCore, set_gui_output_callback
    from evaluation_harness.ceq_benchmarks.manual_sentiment_benchmark import ManualSentimentCEQBenchmark
except ImportError:
    print("Could not import PraxisCore. CEQ evaluation requires main.py and its dependencies.")
    PraxisCore = None # type: ignore
    set_gui_output_callback = None # type: ignore
    ManualSentimentCEQBenchmark = None # type: ignore

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    logging.info("Starting CEQ Evaluation Harness...")

    if not PraxisCore or not set_gui_output_callback:
        logging.error("PraxisCore or set_gui_output_callback not available. Aborting CEQ evaluation.")
        return

    if not ManualSentimentCEQBenchmark:
        logging.error("ManualSentimentCEQBenchmark not available. Aborting.")
        return

    # --- Initialize PraxisCore ---
    def dummy_gui_output_callback(message: str):
        pass

    def dummy_status_update_callback(status: dict, enable_feedback_buttons: bool = False):
        pass

    set_gui_output_callback(dummy_gui_output_callback)
    praxis = PraxisCore(gui_update_status_callback=dummy_status_update_callback)
    praxis.initialize_user_session("CEQ_Evaluator")

    if not praxis.skill_context:
        logging.error("Praxis skill_context not initialized. Aborting.")
        return

    # --- Instantiate and Run Benchmarks ---
    # For now, only ManualSentimentCEQBenchmark
    # Future: Discover and run multiple CEQ benchmark classes
    benchmarks_to_run: List[ManualSentimentCEQBenchmark] = [] # type: ignore
    manual_ceq_benchmark = ManualSentimentCEQBenchmark()
    benchmarks_to_run.append(manual_ceq_benchmark)

    overall_results: Dict[str, Any] = {}

    for benchmark in benchmarks_to_run:
        logging.info(f"Running CEQ Benchmark: {benchmark.name}...")
        benchmark.load_data() # Prompts file path is handled internally by the benchmark
        run_output = benchmark.run(praxis_instance=praxis)
        metrics = benchmark.calculate_metrics(run_output)
        overall_results[benchmark.name] = metrics

    logging.info("\n--- CEQ Evaluation Summary ---")
    
    # Process and display results for ManualSentimentCEQBenchmark
    manual_results = overall_results.get(manual_ceq_benchmark.name)
    if manual_results:
        criteria = manual_results.get("criteria", [])
        scores_per_prompt = manual_results.get("manual_scores_per_prompt", [])
        
        if criteria and scores_per_prompt:
            avg_scores_per_criterion: dict[str, float] = {crit: 0.0 for crit in criteria}
            num_prompts_scored = len(scores_per_prompt)

            for item_scores_data in scores_per_prompt:
                for crit, score_val in item_scores_data["scores"].items():
                    avg_scores_per_criterion[crit] += score_val
            
            for crit in avg_scores_per_criterion:
                avg_scores_per_criterion[crit] /= num_prompts_scored if num_prompts_scored > 0 else 1
                logging.info(f"Average score for '{crit}': {avg_scores_per_criterion[crit]:.2f}")
            
            overall_ceq_avg = sum(avg_scores_per_criterion.values()) / len(avg_scores_per_criterion) if avg_scores_per_criterion else 0
            print(f"\nOverall CEQ Score (Manual Sentiment): {overall_ceq_avg:.2f}")
            logging.info(f"CEQ Score (Overall Average for {manual_ceq_benchmark.name}): {overall_ceq_avg:.2f}")
        else:
            logging.warning(f"No scores or criteria found for {manual_ceq_benchmark.name} to summarize.")
    else:
        logging.info("No results from ManualSentimentCEQBenchmark to display.")

    praxis.shutdown()

if __name__ == "__main__":
    main()