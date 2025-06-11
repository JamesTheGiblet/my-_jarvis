import abc
import yaml
from typing import Dict, List, Any, Optional
import os
import time
from collections import deque

# Attempt to import provider-specific libraries
try: import google.generativeai as genai
except ImportError: genai = None
try: import anthropic
except ImportError: anthropic = None
try: import groq
except ImportError: groq = None
try: import ollama
except ImportError: ollama = None
try:
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, RetryError
except ImportError:
    print("WARNING: 'tenacity' library not found. pip install tenacity. Retries will not be available.")
    retry = None # Placeholder if tenacity is not installed
try: from google.api_core import exceptions as google_api_exceptions
except ImportError: # Corrected message
    print("WARNING: 'google-api-core' library not found. pip install google-api-core. Google API error handling might be limited.")
    google_api_exceptions = None # Placeholder

# --- Custom Exceptions ---
class APIError(Exception):
    """Base class for API related errors."""
    def __init__(self, message, underlying_exception=None):
        super().__init__(message)
        self.underlying_exception = underlying_exception

class APIRateLimitError(APIError):
    """Custom exception for rate limit errors (e.g., HTTP 429)."""
    pass

class APIConnectionError(APIError):
    """Custom exception for connection errors or server-side issues (e.g., HTTP 5xx)."""
    pass

class ModelNotReadyError(APIError):
    """Custom exception for when a model is not ready (e.g., Ollama model not pulled)."""
    pass

# --- RateLimitTracker Class ---
class RateLimitTracker:
    def __init__(self, rate_limit_rpm: int):
        if rate_limit_rpm <= 0: # Allow 0 to signify no tracking, though adapter should handle this
            self.rate_limit_rpm = float('inf') # Effectively no limit
        else:
            self.rate_limit_rpm = rate_limit_rpm
        self.requests = deque()
        self.time_window_seconds = 60.0

    def _prune_old_timestamps(self, current_time: float):
        while self.requests and self.requests[0] <= current_time - self.time_window_seconds:
            self.requests.popleft()

    def add_request_timestamp(self, current_time: float):
        self.requests.append(current_time) # Add first, then prune
        self._prune_old_timestamps(current_time)

    def is_limit_exceeded(self, current_time: float) -> bool:
        self._prune_old_timestamps(current_time)
        return len(self.requests) >= self.rate_limit_rpm

    def get_wait_time(self, current_time: float) -> float:
        self._prune_old_timestamps(current_time)
        if len(self.requests) < self.rate_limit_rpm:
            return 0.0
        # Time until the oldest request that counts towards the current limit expires
        # This would be the (len(self.requests) - self.rate_limit_rpm + 1)-th request from the left
        # Or more simply, the first request in the deque if we are at or over the limit.
        if self.requests:
            oldest_relevant_request_time = self.requests[0]
            wait_needed = (oldest_relevant_request_time + self.time_window_seconds) - current_time
            return max(0.0, wait_needed)
        return 0.0 # Should not happen if limit is exceeded and requests is populated

# --- Part 1: Abstract Base Class ---
class ModelAdapter(abc.ABC):
    """
    Abstract base class for all model adapters.
    Defines the common interface for interacting with different LLM APIs.
    """
    def __init__(self, model_id: str, provider: str, api_model_name: str, rate_limit_rpm: int, strengths: List[str]):
        self.model_id = model_id
        self.provider = provider
        self.api_model_name = api_model_name
        self.rate_limit_rpm = rate_limit_rpm
        self.strengths = strengths
        
        if self.rate_limit_rpm > 0 and retry: # Only initialize if RPM is positive and tenacity is available
            self.rate_limit_tracker: Optional[RateLimitTracker] = RateLimitTracker(self.rate_limit_rpm)
        else:
            self.rate_limit_tracker = None

    @abc.abstractmethod
    def generate(self, prompt: str) -> str:
        """
        Generates a response from the model given a prompt.

        Args:
            prompt: The input prompt string.

        Returns:
            The model's generated response string.
        """
        pass

# --- Tenacity Retry Configuration (Common) ---
if retry:
    COMMON_RETRY_STRATEGY = retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=(
            retry_if_exception_type(APIRateLimitError) |
            retry_if_exception_type(APIConnectionError)
        ),
        reraise=True # Reraise the last exception if all retries fail
    )
else: # Fallback if tenacity is not installed
    COMMON_RETRY_STRATEGY = lambda func: func # No-op decorator

# --- Concrete Adapter Implementations ---
class GoogleAdapter(ModelAdapter): # Renamed from GoogleModelAdapter for consistency
    def __init__(self, model_id: str, provider: str, api_model_name: str, rate_limit_rpm: int, strengths: List[str]):
        super().__init__(model_id, provider, api_model_name, rate_limit_rpm, strengths)
        if not genai:
            raise ImportError("Google Generative AI library not installed. Run 'pip install google-generativeai'")
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            print("WARNING: GOOGLE_API_KEY environment variable not set. GoogleAdapter may not function.")
        else:
            genai.configure(api_key=self.api_key)
        self.client = genai.GenerativeModel(self.api_model_name) if self.api_key else None

    @COMMON_RETRY_STRATEGY
    def _perform_api_call(self, prompt: str) -> str:
        try:
            print(f"INFO: GoogleAdapter ({self.api_model_name}) attempting API call for prompt: '{prompt[:50]}...'")
            response = self.client.generate_content(prompt)
            return response.text
        except genai.types.generation_types.BlockedPromptException as e:
            print(f"ERROR: GoogleAdapter ({self.api_model_name}) prompt blocked: {e}")
            raise APIError(f"Prompt blocked by Google content policy for {self.api_model_name}", underlying_exception=e) from e
        except google_api_exceptions.ResourceExhausted as e: # HTTP 429
            print(f"WARNING: GoogleAdapter ({self.api_model_name}) rate limit hit (ResourceExhausted - will retry): {e}")
            raise APIRateLimitError(f"Google API rate limit for {self.api_model_name}", underlying_exception=e) from e
        except google_api_exceptions.ServiceUnavailable as e: # HTTP 503
            print(f"WARNING: GoogleAdapter ({self.api_model_name}) service unavailable (ServiceUnavailable - will retry): {e}")
            raise APIConnectionError(f"Google API service unavailable for {self.api_model_name}", underlying_exception=e) from e
        except google_api_exceptions.GoogleAPIError as e: # Catch other Google API core errors
            # This could include InvalidArgument (400), PermissionDenied (403), etc.
            # These are generally not retried by our common strategy unless they are specifically APIRateLimitError or APIConnectionError.
            print(f"ERROR: GoogleAdapter ({self.api_model_name}) Google API error: {e}")
            # Check if it's a quota/rate limit related error not caught by ResourceExhausted
            if hasattr(e, 'code') and e.code == 429: # Another way a 429 might appear
                 raise APIRateLimitError(f"Google API rate limit (via GoogleAPIError 429) for {self.api_model_name}", underlying_exception=e) from e
            raise APIError(f"Google API error for {self.api_model_name}: {e}", underlying_exception=e) from e
        except Exception as e:
            # This catches other exceptions that might occur, including potential ones from the genai library
            # not covered by google.api_core.exceptions
            print(f"ERROR: GoogleAdapter ({self.api_model_name}) unexpected error during API call: {e}")
            raise APIError(f"Unexpected error in GoogleAdapter for {self.api_model_name}", underlying_exception=e) from e

    def generate(self, prompt: str) -> str:
        if not self.client:
            raise APIError(f"GoogleAdapter for {self.model_id} not initialized (missing API key or library).")

        if self.rate_limit_tracker:
            current_time = time.time()
            while self.rate_limit_tracker.is_limit_exceeded(current_time):
                wait_for = self.rate_limit_tracker.get_wait_time(current_time)
                if wait_for <= 0: break
                print(f"INFO: GoogleAdapter ({self.model_id}) client-side rate limit. Waiting for {wait_for:.2f}s.")
                time.sleep(wait_for)
                current_time = time.time()
        
        response_text = self._perform_api_call(prompt)
        if self.rate_limit_tracker:
            self.rate_limit_tracker.add_request_timestamp(time.time())
        return response_text

class AnthropicAdapter(ModelAdapter): # Renamed
    def __init__(self, model_id: str, provider: str, api_model_name: str, rate_limit_rpm: int, strengths: List[str]):
        super().__init__(model_id, provider, api_model_name, rate_limit_rpm, strengths)
        if not anthropic:
            raise ImportError("Anthropic library not installed. Run 'pip install anthropic'")
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            print("WARNING: ANTHROPIC_API_KEY environment variable not set. AnthropicAdapter may not function.")
            self.client = None
        else:
            self.client = anthropic.Anthropic(api_key=self.api_key)

    @COMMON_RETRY_STRATEGY
    def _perform_api_call(self, prompt: str) -> str:
        try:
            print(f"INFO: AnthropicAdapter ({self.api_model_name}) attempting API call for prompt: '{prompt[:50]}...'")
            response = self.client.messages.create(
                model=self.api_model_name,
                max_tokens=1024, # Example, adjust as needed
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.content[0].text
        except anthropic.RateLimitError as e:
            print(f"WARNING: AnthropicAdapter ({self.api_model_name}) rate limit hit (will retry): {e}")
            raise APIRateLimitError(f"Anthropic API rate limit for {self.api_model_name}", underlying_exception=e) from e
        except anthropic.APIConnectionError as e: # Includes DNS, connection timeouts
            print(f"WARNING: AnthropicAdapter ({self.api_model_name}) connection error (will retry): {e}")
            raise APIConnectionError(f"Anthropic API connection error for {self.api_model_name}", underlying_exception=e) from e
        except anthropic.InternalServerError as e: # Typically 5xx errors
            print(f"WARNING: AnthropicAdapter ({self.api_model_name}) internal server error (will retry): {e}")
            raise APIConnectionError(f"Anthropic API internal server error for {self.api_model_name}", underlying_exception=e) from e
        except anthropic.APIStatusError as e: # Other non-200 status codes
            print(f"ERROR: AnthropicAdapter ({self.api_model_name}) API status error: {e.status_code} {e.message}")
            raise APIError(f"Anthropic API status error {e.status_code} for {self.api_model_name}", underlying_exception=e) from e
        except Exception as e:
            print(f"ERROR: AnthropicAdapter ({self.api_model_name}) unexpected error during API call: {e}")
            raise APIError(f"Unexpected error in AnthropicAdapter for {self.api_model_name}", underlying_exception=e) from e

    def generate(self, prompt: str) -> str:
        if not self.client:
            raise APIError(f"AnthropicAdapter for {self.model_id} not initialized (missing API key or library).")

        if self.rate_limit_tracker:
            current_time = time.time()
            while self.rate_limit_tracker.is_limit_exceeded(current_time):
                wait_for = self.rate_limit_tracker.get_wait_time(current_time)
                if wait_for <= 0: break
                print(f"INFO: AnthropicAdapter ({self.model_id}) client-side rate limit. Waiting for {wait_for:.2f}s.")
                time.sleep(wait_for)
                current_time = time.time()

        response_text = self._perform_api_call(prompt)
        if self.rate_limit_tracker:
            self.rate_limit_tracker.add_request_timestamp(time.time())
        return response_text

class GroqAdapter(ModelAdapter): # Renamed
    def __init__(self, model_id: str, provider: str, api_model_name: str, rate_limit_rpm: int, strengths: List[str]):
        super().__init__(model_id, provider, api_model_name, rate_limit_rpm, strengths)
        if not groq:
            raise ImportError("Groq library not installed. Run 'pip install groq'")
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            print("WARNING: GROQ_API_KEY environment variable not set. GroqAdapter may not function.")
            self.client = None
        else:
            self.client = groq.Groq(api_key=self.api_key)

    @COMMON_RETRY_STRATEGY
    def _perform_api_call(self, prompt: str) -> str:
        try:
            print(f"INFO: GroqAdapter ({self.api_model_name}) attempting API call for prompt: '{prompt[:50]}...'")
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model=self.api_model_name,
            )
            return chat_completion.choices[0].message.content
        except groq.RateLimitError as e:
            print(f"WARNING: GroqAdapter ({self.api_model_name}) rate limit hit (will retry): {e}")
            raise APIRateLimitError(f"Groq API rate limit for {self.api_model_name}", underlying_exception=e) from e
        except groq.APIConnectionError as e:
            print(f"WARNING: GroqAdapter ({self.api_model_name}) connection error (will retry): {e}")
            raise APIConnectionError(f"Groq API connection error for {self.api_model_name}", underlying_exception=e) from e
        except groq.InternalServerError as e:
            print(f"WARNING: GroqAdapter ({self.api_model_name}) internal server error (will retry): {e}")
            raise APIConnectionError(f"Groq API internal server error for {self.api_model_name}", underlying_exception=e) from e
        except groq.APIStatusError as e: # Other non-200 status codes
            print(f"ERROR: GroqAdapter ({self.api_model_name}) API status error: {e.status_code} {e.message}")
            raise APIError(f"Groq API status error {e.status_code} for {self.api_model_name}", underlying_exception=e) from e
        except Exception as e:
            print(f"ERROR: GroqAdapter ({self.api_model_name}) unexpected error during API call: {e}")
            raise APIError(f"Unexpected error in GroqAdapter for {self.api_model_name}", underlying_exception=e) from e

    def generate(self, prompt: str) -> str:
        if not self.client:
            raise APIError(f"GroqAdapter for {self.model_id} not initialized (missing API key or library).")

        if self.rate_limit_tracker:
            current_time = time.time()
            while self.rate_limit_tracker.is_limit_exceeded(current_time):
                wait_for = self.rate_limit_tracker.get_wait_time(current_time)
                if wait_for <= 0: break
                print(f"INFO: GroqAdapter ({self.model_id}) client-side rate limit. Waiting for {wait_for:.2f}s.")
                time.sleep(wait_for)
                current_time = time.time()

        response_text = self._perform_api_call(prompt)
        if self.rate_limit_tracker:
            self.rate_limit_tracker.add_request_timestamp(time.time())
        return response_text

class OllamaAdapter(ModelAdapter): # Renamed
    def __init__(self, model_id: str, provider: str, api_model_name: str, rate_limit_rpm: int, strengths: List[str]):
        super().__init__(model_id, provider, api_model_name, rate_limit_rpm, strengths)
        if not ollama:
            raise ImportError("Ollama library not installed. Run 'pip install ollama'")
        # Ollama client typically doesn't require an API key for local instances.
        # It might require a host if not running on default localhost:11434
        # For simplicity, we assume default local setup.
        try:
            self.client = ollama.Client()
            # A quick check to see if Ollama server is reachable with a list models
            self.client.list() 
            print(f"INFO: OllamaAdapter connected to Ollama server for model {self.api_model_name}.")
        except Exception as e:
            print(f"WARNING: OllamaAdapter for {self.model_id} could not connect to Ollama server or list models: {e}. Ensure Ollama is running.")
            self.client = None

    @COMMON_RETRY_STRATEGY
    def _perform_api_call(self, prompt: str) -> str:
        try:
            print(f"INFO: OllamaAdapter ({self.api_model_name}) attempting API call for prompt: '{prompt[:50]}...'")
            response = ollama.chat(
                model=self.api_model_name,
                messages=[
                    {
                        'role': 'user',
                        'content': prompt,
                    },
                ]
            )
            return response['message']['content']
        except ollama.ResponseError as e:
            err_str = str(e).lower()
            if e.status_code == 429:
                print(f"WARNING: OllamaAdapter ({self.api_model_name}) rate limit hit (will retry): {e}")
                raise APIRateLimitError(f"Ollama API rate limit for {self.api_model_name}", underlying_exception=e) from e
            if e.status_code >= 500: # Server-side errors
                print(f"WARNING: OllamaAdapter ({self.api_model_name}) server error (will retry): {e}")
                raise APIConnectionError(f"Ollama server error for {self.api_model_name} (status {e.status_code})", underlying_exception=e) from e
            if ("model" in err_str and "not found" in err_str) or e.status_code == 404:
                 print(f"ERROR: OllamaAdapter ({self.api_model_name}) model not found. Pull with 'ollama pull {self.api_model_name}'. Details: {e}")
                 raise ModelNotReadyError(f"Ollama model '{self.api_model_name}' not found. Pull it first.", underlying_exception=e) from e
            print(f"ERROR: OllamaAdapter ({self.api_model_name}) API response error: {e.status_code} {e.error}")
            raise APIError(f"Ollama API response error {e.status_code} for {self.api_model_name}", underlying_exception=e) from e
        except ollama.RequestError as e: # Connection errors, timeouts
            print(f"WARNING: OllamaAdapter ({self.api_model_name}) connection error (will retry): {e}")
            raise APIConnectionError(f"Ollama connection error for {self.api_model_name}", underlying_exception=e) from e
        except Exception as e:
            print(f"ERROR: OllamaAdapter ({self.api_model_name}) unexpected error during API call: {e}")
            raise APIError(f"Unexpected error in OllamaAdapter for {self.api_model_name}", underlying_exception=e) from e

    def generate(self, prompt: str) -> str:
        if not self.client:
            raise APIError(f"OllamaAdapter for {self.model_id} not initialized or Ollama server not reachable.")

        # Ollama client-side rate limiting is less common as it's usually local, but we include for consistency
        if self.rate_limit_tracker:
            current_time = time.time()
            while self.rate_limit_tracker.is_limit_exceeded(current_time):
                wait_for = self.rate_limit_tracker.get_wait_time(current_time)
                if wait_for <= 0: break
                print(f"INFO: OllamaAdapter ({self.model_id}) client-side rate limit. Waiting for {wait_for:.2f}s.")
                time.sleep(wait_for)
                current_time = time.time()

        response_text = self._perform_api_call(prompt)
        if self.rate_limit_tracker:
            self.rate_limit_tracker.add_request_timestamp(time.time())
        return response_text

class UnknownProviderAdapter(ModelAdapter):
    def generate(self, prompt: str) -> str:
        error_message = f"UnknownProviderAdapter ({self.api_model_name}) for provider '{self.provider}': Generation not supported. Adapter not implemented."
        print(f"ERROR: {error_message}")
        raise NotImplementedError(error_message)


# --- Part 2: Model Registry ---
class ModelRegistry:
    """
    Manages and provides access to configured AI models and their adapters.
    Reads model configurations from a YAML file and initializes adapters.
    """
    def __init__(self, config_path: str = 'models.yaml'):
        """
        Initializes the ModelRegistry.

        Args:
            config_path: Path to the models.yaml configuration file.
                         Defaults to 'models.yaml' in the current working directory.
        """
        self.config_path = os.path.abspath(config_path) # Store absolute path
        self.models_config: List[Dict[str, Any]] = []
        self.adapters: Dict[str, ModelAdapter] = {}
        
        self._load_config_from_yaml()
        self._initialize_all_adapters() # This method loads models and stores adapters

    def _load_config_from_yaml(self):
        """Loads model configurations from the YAML file specified in self.config_path."""
        print(f"INFO: Attempting to load model configurations from: {self.config_path}")
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
                if config_data and 'models' in config_data and isinstance(config_data['models'], list):
                    self.models_config = config_data['models']
                    print(f"INFO: Successfully loaded {len(self.models_config)} model configurations.")
                else:
                    print(f"WARNING: 'models' key not found, not a list, or empty in {self.config_path}. No models will be loaded.")
                    self.models_config = []
        except FileNotFoundError:
            print(f"ERROR: Configuration file not found at {self.config_path}. No models will be loaded.")
            self.models_config = []
        except yaml.YAMLError as e:
            print(f"ERROR: Parsing YAML file {self.config_path}: {e}. No models will be loaded.")
            self.models_config = []
        except Exception as e:
            print(f"ERROR: An unexpected error occurred while loading {self.config_path}: {e}. No models will be loaded.")
            self.models_config = []

    def _initialize_all_adapters(self):
        """
        Initializes adapter instances for each model defined in self.models_config.
        This method effectively "loads all models" by creating their adapters.
        """
        if not self.models_config:
            print("INFO: No model configurations loaded, so no adapters will be initialized.")
            return

        print(f"INFO: Initializing adapters for {len(self.models_config)} configured models...")
        for model_conf in self.models_config:
            if not isinstance(model_conf, dict):
                print(f"WARNING: Skipping invalid model configuration item (not a dictionary): {model_conf}")
                continue

            model_id = model_conf.get('model_id')
            provider = model_conf.get('provider')
            api_model_name = model_conf.get('api_model_name')
            
            rate_limit_rpm_raw = model_conf.get('rate_limit_rpm')
            rate_limit_rpm = 0 # Default
            if rate_limit_rpm_raw is not None:
                try:
                    rate_limit_rpm = int(rate_limit_rpm_raw)
                except ValueError:
                    print(f"WARNING: Invalid 'rate_limit_rpm' value '{rate_limit_rpm_raw}' for model_id '{model_id}'. Defaulting to 0.")
            
            strengths = model_conf.get('strengths', [])
            if not isinstance(strengths, list):
                print(f"WARNING: 'strengths' for model_id '{model_id}' is not a list: {strengths}. Defaulting to empty list.")
                strengths = []

            if not all([model_id, provider, api_model_name]):
                print(f"WARNING: Skipping model due to missing 'model_id', 'provider', or 'api_model_name'. Config: {model_conf}")
                continue

            adapter_args = (model_id, provider, api_model_name, rate_limit_rpm, strengths)

            # Mapping provider names (case-insensitive) to adapter classes
            adapter_class_map = {
                'google': GoogleAdapter,
                'anthropic': AnthropicAdapter,
                'groq': GroqAdapter,
                'ollama': OllamaAdapter,
            }

            adapter_class = adapter_class_map.get(provider.lower())

            if adapter_class:
                try:
                    self.adapters[model_id] = adapter_class(*adapter_args)
                    print(f"INFO: Initialized adapter for model_id: '{model_id}' (Provider: {provider})")
                except Exception as e:
                    print(f"ERROR: Failed to initialize adapter for model_id '{model_id}' (Provider: {provider}). Error: {e}")
                    # Optionally, you could add a non-functional adapter or skip
                    # For now, it just means this adapter won't be in self.adapters if init fails
                    # Or, use UnknownProviderAdapter as a fallback if initialization fails badly
            else:
                print(f"WARNING: Unknown provider '{provider}' for model_id '{model_id}'. Using UnknownProviderAdapter.")
                self.adapters[model_id] = UnknownProviderAdapter(*adapter_args)
        
        if self.adapters:
             print(f"INFO: Successfully initialized {len(self.adapters)} model adapters: {list(self.adapters.keys())}")
        elif self.models_config: # Config was loaded but no adapters were created
             print("WARNING: Model configurations were loaded, but no valid adapters were initialized. Please check provider names and model details in the YAML file.")
        else:
            print("INFO: No adapters initialized as no model configurations were available.")

    def get_adapter(self, model_id: str) -> Optional[ModelAdapter]:
        """
        Retrieves a previously initialized model adapter by its model_id.

        Args:
            model_id: The unique identifier of the model.

        Returns:
            The ModelAdapter instance if found, otherwise None.
        """
        adapter = self.adapters.get(model_id)
        if not adapter:
            print(f"WARNING: Adapter for model_id '{model_id}' not found. Available adapters: {list(self.adapters.keys())}")
        return adapter

    def list_available_model_ids(self) -> List[str]:
        """Returns a list of model_ids for which adapters have been successfully initialized."""
        return list(self.adapters.keys())

# --- Part 5: Intelligent Model Router ---

TASK_PROFILES: Dict[str, Dict[str, Any]] = {
    "simple_chat": {
        "preferred_strengths": ["fast", "chat", "efficient"],
        "description": "For quick, conversational interactions, Q&A."
    },
    "complex_reasoning": {
        "preferred_strengths": ["powerful", "complex-reasoning", "large-context"],
        "description": "For tasks requiring deep understanding and multi-step reasoning."
    },
    "document_summarization": {
        "preferred_strengths": ["large-context", "powerful", "complex-reasoning"],
        "description": "For summarizing long documents accurately."
    },
    "code_generation": {
        "preferred_strengths": ["powerful", "strong-coding", "complex-reasoning", "fast"],
        "description": "For generating or assisting with programming code."
    },
    "creative_writing": {
        "preferred_strengths": ["powerful", "large-context"], # Add 'creative' if such a strength is defined
        "description": "For generating creative text formats, storytelling."
    },
    "local_fast_task": {
        "preferred_strengths": ["local", "fast", "offline-capable"],
        "description": "For tasks that need to run locally and quickly, possibly offline."
    }
}

class ModelRouter:
    def __init__(self, model_registry: ModelRegistry):
        self.model_registry = model_registry

    def select_model(self, task_name: str) -> Optional[ModelAdapter]:
        """
        Selects the best available and non-rate-limited model for a given task.

        Args:
            task_name: The name of the task (must be a key in TASK_PROFILES).

        Returns:
            A ModelAdapter instance for the best model, or None if no suitable model is found.
        """
        task_profile = TASK_PROFILES.get(task_name)
        if not task_profile:
            print(f"WARNING: Task profile for '{task_name}' not found.")
            return None

        preferred_strengths = set(task_profile.get("preferred_strengths", []))
        if not preferred_strengths:
            print(f"WARNING: No preferred strengths defined for task '{task_name}'.")
            return None

        best_model: Optional[ModelAdapter] = None
        max_score = -1

        for model_id in self.model_registry.list_available_model_ids():
            adapter = self.model_registry.get_adapter(model_id)
            if not adapter: continue

            # Check client-side rate limit
            if adapter.rate_limit_tracker and adapter.rate_limit_tracker.is_limit_exceeded(time.time()):
                print(f"INFO: ModelRouter skipping '{adapter.model_id}' for task '{task_name}' due to client-side rate limit.")
                continue

            model_strengths = set(adapter.strengths)
            score = len(preferred_strengths.intersection(model_strengths))

            if score > 0 and score > max_score: # Must have at least one matching strength
                max_score = score
                best_model = adapter
            elif score > 0 and score == max_score:
                # Basic tie-breaking: prefer models with higher RPM if scores are equal
                # (assuming higher RPM might mean more capacity or less likely to hit server-side limits)
                if best_model and adapter.rate_limit_rpm > best_model.rate_limit_rpm:
                    best_model = adapter

        if best_model:
            print(f"INFO: ModelRouter selected '{best_model.model_id}' (Score: {max_score}) for task '{task_name}'.")
        else:
            print(f"INFO: ModelRouter could not find a suitable, non-rate-limited model for task '{task_name}'.")
        
        return best_model

# --- Example Usage (Illustrative) ---
if __name__ == "__main__":
    # This assumes 'models.yaml' (from Part 1) is in the same directory as this script,
    # or you provide the full path to your 'models.yaml'.
    # For your specific path:
    # models_yaml_path = 'c:/Users/gilbe/Desktop/my _jarvis/models.yaml'
    
    # For a general example, let's assume it's in the same directory as this script:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    models_yaml_path = os.path.join(script_dir, 'models.yaml')

    print(f"--- Example: Initializing ModelRegistry with '{models_yaml_path}' ---")
    # Check if the target models.yaml exists before trying to load
    if not os.path.exists(models_yaml_path):
        print(f"ERROR: The 'models.yaml' file was not found at '{models_yaml_path}'.")
        print("Please ensure the file exists or adjust the 'models_yaml_path' variable.")
        print("\nNOTE: For the new adapters to work, you need to:")
        print("1. Install the required libraries: pip install google-generativeai anthropic groq ollama tenacity pyyaml")
        print("2. Set environment variables for API keys (e.g., GOOGLE_API_KEY, ANTHROPIC_API_KEY, GROQ_API_KEY).")
        print("3. Ensure your Ollama server is running if you plan to use Ollama models.")
        print("You can create a 'models.yaml' file with content similar to Part 1.")
    else:
        registry = ModelRegistry(config_path=models_yaml_path)
        print("--- ModelRegistry Initialization Complete ---")

        available_models = registry.list_available_model_ids()
        print(f"\nAvailable model IDs in registry: {available_models}")

        if available_models:
            print("\n--- Testing all available adapters ---")
            print("NOTE: Actual API calls will be attempted. Ensure API keys are set and services are reachable.")
            for model_id_to_test in available_models:
                print(f"\n--- Testing adapter for model_id: '{model_id_to_test}' ---")
                adapter = registry.get_adapter(model_id_to_test)

                if adapter:
                    print(f"  Adapter Type: {type(adapter).__name__}")
                    print(f"  Model ID: {adapter.model_id}")
                    print(f"  Provider: {adapter.provider}")
                    print(f"  API Model Name: {adapter.api_model_name}")
                    print(f"  Rate Limit (RPM): {adapter.rate_limit_rpm}")
                    print(f"  Strengths: {', '.join(adapter.strengths)}")
                    
                    # For Ollama, check if the model needs to be pulled
                    if isinstance(adapter, OllamaAdapter) and adapter.client:
                        try:
                            models_info = adapter.client.list()
                            if not any(m['name'].startswith(adapter.api_model_name) for m in models_info['models']):
                                print(f"  OLLAMA HINT: Model '{adapter.api_model_name}' might not be pulled. Consider running: ollama pull {adapter.api_model_name}")
                        except Exception:
                             pass # Already handled in __init__ or generate

                    try:
                        test_prompt = f"Hello {adapter.model_id}, tell me a very short fun fact about programming."
                        print(f"  Attempting to generate with prompt: '{test_prompt[:60]}...'")
                        response = adapter.generate(test_prompt)
                        print(f"  Response: {response}")
                    except NotImplementedError as e: # For UnknownProviderAdapter
                        print(f"  Caught expected error for unhandled provider: {e}")
                    except ModelNotReadyError as e:
                        print(f"  MODEL NOT READY for {model_id_to_test}: {e}")
                    except APIRateLimitError as e:
                        print(f"  RATE LIMIT ERROR for {model_id_to_test} (even after retries/client wait): {e}")
                    except APIConnectionError as e:
                        print(f"  CONNECTION ERROR for {model_id_to_test} (even after retries): {e}")
                    except APIError as e: # Catch other API errors from our hierarchy
                        print(f"  API ERROR for {model_id_to_test}: {e}")
                    except Exception as e: # Catch-all for other unexpected errors during generate
                        print(f"  An unexpected error occurred during generation for {model_id_to_test}: {e}")
                else:
                    print(f"  Could not retrieve adapter for '{model_id_to_test}', though it was listed as available.")
        else:
            print("\nNo models were successfully loaded into the registry. Check YAML configuration and file path.")

        # Example of trying to get a non-existent adapter
        print("\n--- Testing retrieval of a non-existent adapter ---")
        non_existent_adapter = registry.get_adapter("this-model-does-not-exist")
        if non_existent_adapter is None:
            print("  Correctly returned None for 'this-model-does-not-exist'.")

        print("\n--- Testing ModelRouter ---")
        if available_models: # Ensure registry was initialized and has models
            router = ModelRouter(registry)
            
            tasks_to_test = ["simple_chat", "document_summarization", "code_generation", "local_fast_task", "non_existent_task"]

            for task in tasks_to_test:
                print(f"\n--- Routing for task: '{task}' ---")
                selected_adapter = router.select_model(task)

                if selected_adapter:
                    print(f"  Router selected: {selected_adapter.model_id} (Provider: {selected_adapter.provider})")
                    print(f"  Model Strengths: {', '.join(selected_adapter.strengths)}")
                    print(f"  Task Preferred Strengths: {', '.join(TASK_PROFILES.get(task, {}).get('preferred_strengths', []))}")
                    try:
                        # Perform a quick generation to see it in action
                        prompt = f"This is a test for '{task}' using {selected_adapter.model_id}. Briefly explain your primary function."
                        print(f"  Attempting generation with {selected_adapter.model_id}...")
                        response = selected_adapter.generate(prompt)
                        print(f"  Response from {selected_adapter.model_id}: {response[:100]}...") # Print first 100 chars
                    except Exception as e:
                        print(f"  Error during generation with {selected_adapter.model_id} for task '{task}': {e}")
                else:
                    print(f"  No suitable model found by router for task: '{task}'.")
        else:
            print("\nModelRouter tests skipped as no models are available in the registry.")