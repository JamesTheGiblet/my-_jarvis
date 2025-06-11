# evaluation_harness/ceq_benchmarks/manual_sentiment_benchmark.py
import os
import json
import time
from typing import List, Dict, Any, Optional

from evaluation_harness.benchmarks_base import CEQBenchmarkBase

# Attempt to import PraxisCore for type hinting if available
try:
    from main import PraxisCore
except ImportError:
    PraxisCore = None # type: ignore

DEFAULT_PROMPTS_FILE = "prompts.json" # Relative to ceq_benchmarks directory

EVALUATION_CRITERIA = [
    "Did it recognize the user's emotional state/intent?",
    "Was the tone of the response appropriate?",
    "Did it offer a clear explanation or action if applicable?",
    "Did it state its limitations or confidence appropriately?"
]

class ManualSentimentCEQBenchmark(CEQBenchmarkBase):
    def __init__(self, name: str = "ManualSentimentCEQ"):
        super().__init__(name=name)
        self.prompts_data: List[Dict[str, Any]] = []

    def load_data(self, data_path: Optional[str] = None) -> None:
        if data_path is None:
            # Construct path relative to this file's directory if not provided
            current_dir = os.path.dirname(os.path.abspath(__file__))
            data_path = os.path.join(current_dir, DEFAULT_PROMPTS_FILE)

        if not os.path.exists(data_path):
            self.logger.error(f"Prompts file not found: {data_path}")
            raise FileNotFoundError(f"Prompts file not found: {data_path}")
        
        with open(data_path, "r", encoding="utf-8") as f:
            self.prompts_data = json.load(f)
        self.logger.info(f"Loaded {len(self.prompts_data)} prompts from {data_path}")

    def run(self, praxis_instance: Optional[PraxisCore] = None, **kwargs) -> List[Dict[str, Any]]: # type: ignore
        if not praxis_instance or not praxis_instance.skill_context:
            self.logger.error("PraxisCore instance or skill_context not available for running benchmark.")
            return []

        results = []
        original_mute_state = praxis_instance.skill_context.is_muted
        praxis_instance.skill_context.is_muted = True # Mute TTS and capture

        for prompt_item in self.prompts_data:
            prompt_id = prompt_item["id"]
            prompt_text = prompt_item["prompt_text"]
            
            praxis_instance.skill_context.clear_spoken_messages_for_test()
            praxis_instance.process_command_text(prompt_text)
            time.sleep(0.5) # Allow for any brief async processing
            
            ai_responses = praxis_instance.skill_context.spoken_messages_for_test
            ai_full_response = "\n".join(ai_responses) if ai_responses else "AI did not produce a spoken response."
            
            results.append({
                "prompt_id": prompt_id,
                "prompt_text": prompt_text,
                "ai_response": ai_full_response
            })
        
        praxis_instance.skill_context.is_muted = original_mute_state # Restore mute state
        return results

    def calculate_metrics(self, run_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        all_manual_scores = []
        for result in run_results:
            print("\n" + "="*50)
            self.logger.info(f"Evaluating CEQ Prompt ID: {result['prompt_id']}")
            print(f"User Prompt: {result['prompt_text']}")
            print(f"AI Response: {result['ai_response']}")
            print("-"*50)
            
            scores = {}
            for criterion in EVALUATION_CRITERIA:
                while True:
                    try:
                        score = input(f"Score for '{criterion}' (1-5): ")
                        score_val = int(score)
                        if 1 <= score_val <= 5: scores[criterion] = score_val; break
                        else: print("Invalid score. Please enter 1-5.")
                    except ValueError: print("Invalid input. Please enter a number.")
            all_manual_scores.append({"id": result['prompt_id'], "scores": scores})
        return {"manual_scores_per_prompt": all_manual_scores, "criteria": EVALUATION_CRITERIA}