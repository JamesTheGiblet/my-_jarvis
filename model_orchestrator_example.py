# model_orchestrator_example.py
import os
import sys

# Ensure the model_layer module can be found if this script is run directly
# This assumes model_layer.py is in the same directory or Python path is configured
try:
    from model_layer import (
        ModelRegistry,
        ModelRouter,
        TASK_PROFILES, # For displaying task info
        APIError,
        APIRateLimitError,
        APIConnectionError,
        ModelNotReadyError
    )
except ImportError:
    print("ERROR: Could not import from model_layer.py.")
    print("Ensure model_layer.py is in the same directory or in your PYTHONPATH.")
    sys.exit(1)

def execute_task(router: ModelRouter, task_name: str, prompt: str) -> str:
    """
    Executes a given task using the best available model selected by the router.

    Args:
        router: An instance of ModelRouter.
        task_name: The name of the task (e.g., 'simple_chat', 'document_summarization').
        prompt: The input prompt for the LLM.

    Returns:
        The response from the LLM, or an error message if execution fails.
    """
    print(f"\n--- Executing Task: '{task_name}' ---")
    print(f"Prompt: \"{prompt[:100]}{'...' if len(prompt) > 100 else ''}\"")

    selected_adapter = router.select_model(task_name)

    if not selected_adapter:
        error_msg = f"No suitable model found by the router for task '{task_name}'."
        print(f"ERROR: {error_msg}")
        return error_msg

    print(f"Selected Model: {selected_adapter.model_id} (Provider: {selected_adapter.provider})")

    try:
        response, p_tokens, c_tokens = selected_adapter.generate(prompt)
        print(f"Response from {selected_adapter.model_id} (P_tokens: {p_tokens}, C_tokens: {c_tokens}): {response[:200]}{'...' if len(response) > 200 else ''}")
        return response
    except ModelNotReadyError as e:
        error_msg = f"Model '{selected_adapter.model_id}' is not ready: {e}"
    except APIRateLimitError as e:
        error_msg = f"Rate limit hit for model '{selected_adapter.model_id}': {e}"
    except APIConnectionError as e:
        error_msg = f"Connection error with model '{selected_adapter.model_id}': {e}"
    except APIError as e: # Catch other API errors from our hierarchy
        error_msg = f"API error with model '{selected_adapter.model_id}': {e}"
    except Exception as e:
        error_msg = f"An unexpected error occurred with model '{selected_adapter.model_id}': {e}"
    
    print(f"ERROR: {error_msg}")
    return error_msg

if __name__ == "__main__":
    # Define the path to your models.yaml file
    # This assumes models.yaml is in the same directory as this script.
    # Adjust if it's elsewhere, e.g., models_yaml_path = 'c:/Users/gilbe/Desktop/my_jarvis/models.yaml'
    script_dir = os.path.dirname(os.path.abspath(__file__))
    models_yaml_path = os.path.join(script_dir, 'models.yaml')

    if not os.path.exists(models_yaml_path):
        print(f"CRITICAL: 'models.yaml' not found at '{models_yaml_path}'. This script cannot run without it.")
        sys.exit(1)

    print("Initializing Model Registry and Router...")
    registry = ModelRegistry(config_path=models_yaml_path)
    router = ModelRouter(registry)
    print("Initialization complete.")

    # Example Task Executions
    execute_task(router, "simple_chat", "Hello Praxis, how are you today?")
    execute_task(router, "document_summarization", "Summarize the following text about the benefits of remote work: [Insert a long paragraph here about remote work benefits, e.g., improved work-life balance, reduced commute, access to global talent, etc.]")
    execute_task(router, "code_generation", "Write a simple Python function that takes two numbers and returns their sum.")
    execute_task(router, "local_fast_task", "What is the capital of France? Answer very quickly.")
    execute_task(router, "complex_reasoning", "Explain the theory of relativity in simple terms for a high school student.")

    print("\n--- All example tasks processed. ---")