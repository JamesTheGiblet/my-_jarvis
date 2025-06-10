# evaluate_ceq.py
import os
import sys
import json
import logging
import time

# Ensure the main project directory is in PYTHONPATH
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

try:
    from main import PraxisCore, set_gui_output_callback
except ImportError:
    print("Could not import PraxisCore. CEQ evaluation requires main.py and its dependencies.")
    PraxisCore = None # type: ignore
    set_gui_output_callback = None # type: ignore

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

PROMPTS_FILE = os.path.join(project_root, "evaluation_harness", "ceq_benchmarks", "prompts.json")

EVALUATION_CRITERIA = [
    "Did it recognize the user's emotional state/intent?",
    "Was the tone of the response appropriate?",
    "Did it offer a clear explanation or action if applicable?",
    "Did it state its limitations or confidence appropriately?"
]

def get_manual_score(prompt_id: str, prompt_text: str, ai_response: str) -> dict:
    print("\n" + "="*50)
    print(f"Evaluating CEQ Prompt ID: {prompt_id}")
    print(f"User Prompt: {prompt_text}")
    print(f"AI Response: {ai_response if ai_response else '[No response captured]'}")
    print("-"*50)
    
    scores = {}
    for i, criterion in enumerate(EVALUATION_CRITERIA):
        while True:
            try:
                score = input(f"Score for '{criterion}' (1-5): ")
                score_val = int(score)
                if 1 <= score_val <= 5:
                    scores[criterion] = score_val
                    break
                else:
                    print("Invalid score. Please enter a number between 1 and 5.")
            except ValueError:
                print("Invalid input. Please enter a number.")
    return scores

def main():
    logging.info("Starting CEQ Evaluation Harness...")

    if not PraxisCore or not set_gui_output_callback:
        logging.error("PraxisCore or set_gui_output_callback not available. Aborting CEQ evaluation.")
        return

    if not os.path.exists(PROMPTS_FILE):
        logging.error(f"Prompts file not found: {PROMPTS_FILE}")
        return

    with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
        prompts_data = json.load(f)

    # --- Initialize PraxisCore ---
    # For CEQ, we don't need GUI callbacks in the traditional sense,
    # but PraxisCore expects them. We can provide simple print statements.
    def dummy_gui_output_callback(message: str):
        # This is where AI's "speak" output would go if not muted.
        # We'll capture it from skill_context.spoken_messages_during_mute instead.
        pass

    def dummy_status_update_callback(status: dict):
        # logging.debug(f"Praxis Status Update (CEQ Eval): {status}")
        pass

    set_gui_output_callback(dummy_gui_output_callback)
    praxis = PraxisCore(gui_update_status_callback=dummy_status_update_callback)
    
    # Initialize a dummy user session
    # The user name for CEQ evaluation might not be critical, but initialization is.
    praxis.initialize_user_session("CEQ_Evaluator")
    time.sleep(1) # Allow initialization to complete, including skill loading

    if not praxis.skill_context:
        logging.error("Praxis skill_context not initialized. Aborting.")
        return

    praxis.skill_context.is_muted = True # Mute TTS and capture spoken messages

    all_scores = []
    for prompt_item in prompts_data:
        prompt_id = prompt_item["id"]
        prompt_text = prompt_item["prompt_text"]
        
        praxis.skill_context.clear_spoken_messages_for_test()
        praxis.process_command_text(prompt_text) # This will use the LLM
        
        # Wait a moment for async operations if any (though process_command_text is mostly sync)
        time.sleep(0.5) 
        
        ai_responses = praxis.skill_context.spoken_messages_during_mute
        ai_full_response = "\n".join(ai_responses) if ai_responses else "AI did not produce a spoken response."

        scores = get_manual_score(prompt_id, prompt_text, ai_full_response)
        all_scores.append({"id": prompt_id, "scores": scores})

    logging.info("\n--- CEQ Evaluation Summary ---")
    # Calculate average scores
    avg_scores: dict[str, float] = {crit: 0.0 for crit in EVALUATION_CRITERIA}
    num_prompts = len(all_scores)
    if num_prompts > 0:
        for item_scores in all_scores:
            for crit, score_val in item_scores["scores"].items():
                avg_scores[crit] += score_val
        for crit in avg_scores:
            avg_scores[crit] /= num_prompts
            logging.info(f"Average score for '{crit}': {avg_scores[crit]:.2f}")
    
    overall_ceq_score = sum(avg_scores.values()) / len(avg_scores) if avg_scores else 0
    print(f"\nOverall CEQ Score: {overall_ceq_score:.2f}")
    logging.info(f"\nCEQ v1.0 Score (Overall Average): {overall_ceq_score:.2f}")

    praxis.shutdown()

if __name__ == "__main__":
    main()