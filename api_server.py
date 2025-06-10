# api_server.py
import logging
import os
from typing import Optional, List, Dict, Any

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
import uvicorn
import asyncio

# Assuming main.py and its components are in the same directory or accessible
try:
    from main import PraxisCore, set_gui_output_callback
    from config import GEMINI_1_5_FLASH_RPM, GEMINI_1_5_FLASH_TPM, GEMINI_1_5_FLASH_RPD
except ImportError as e:
    print(f"Critical Error: Could not import PraxisCore from main.py: {e}")
    print("Ensure api_server.py is in the same directory as main.py or main.py is in PYTHONPATH.")
    PraxisCore = None
    set_gui_output_callback = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- API Models ---
class CommandRequest(BaseModel):
    user_input: str
    user_name: Optional[str] = "API_User" # Default user for API interactions

class CommandResponse(BaseModel):
    message: str
    ai_response_summary: Optional[str] = None
    interaction_id: Optional[int] = None

class StatusResponse(BaseModel):
    user: str
    mode: str
    praxis_state: str
    ai_name: str
    rpm: str
    tpm: str
    rpd: str

class LogEntry(BaseModel):
    line: str

praxis_core_instance: Optional[Any] = None

@asynccontextmanager
async def lifespan(app_instance: FastAPI): # app_instance will be the FastAPI app
    global praxis_core_instance
    if PraxisCore and set_gui_output_callback:
        logging.info("API Server: Initializing PraxisCore...")

        # Dummy callbacks for API context, as API won't directly update a GUI
        def api_dummy_gui_output_callback(message: str):
            # In a more advanced setup, this could push messages to a WebSocket or SSE
            logging.debug(f"API Praxis Speak (dummy callback): {message}")
            pass

        def api_dummy_status_update_callback(status: Dict[str, Any], enable_feedback_buttons: bool = False):
            logging.debug(f"API Praxis Status (dummy callback): {status}")
            pass

        set_gui_output_callback(api_dummy_gui_output_callback)
        praxis_core_instance = PraxisCore(gui_update_status_callback=api_dummy_status_update_callback)
        
        # Initialize with a default API user or handle user sessions more robustly later
        # For now, we'll initialize with a generic user.
        # In a real app, user management/session handling would be needed.
        if not praxis_core_instance.current_user_name: # Check if already initialized by some other means
            praxis_core_instance.initialize_user_session("API_Default_User")
        logging.info("API Server: PraxisCore initialized.")
    else:
        logging.error("API Server: PraxisCore could not be loaded. API will be non-functional.")
    
    yield # This is where the application runs
    
    # --- Shutdown logic ---
    if praxis_core_instance and praxis_core_instance.is_running:
        logging.info("API Server: Shutting down PraxisCore...")
        praxis_core_instance.shutdown()
        logging.info("API Server: PraxisCore shutdown complete.")

# --- FastAPI App Setup ---
# Pass the lifespan context manager to the FastAPI app
app = FastAPI(title="Praxis API", version="0.1.0", lifespan=lifespan)


@app.post("/command", response_model=CommandResponse)
async def process_command(request: CommandRequest = Body(...)):
    if not praxis_core_instance or not praxis_core_instance.skill_context:
        raise HTTPException(status_code=503, detail="PraxisCore not available or not initialized.")

    # Ensure the user session is for the user in the request if provided
    # This is a simplified user management for now.
    if request.user_name and praxis_core_instance.current_user_name != request.user_name:
        logging.info(f"API: Switching user context to {request.user_name}")
        praxis_core_instance.initialize_user_session(request.user_name)
        # Allow some time for re-initialization if it involves async/threaded operations
        await asyncio.sleep(0.5)

    logging.info(f"API: Received command: '{request.user_input}' from user '{praxis_core_instance.current_user_name}'")
    
    # PraxisCore.process_command_text is synchronous.
    # For a truly async API with long-running tasks, consider background tasks or Celery.
    # For now, we run it directly. The TTS queue in main.py helps with non-blocking speech.
    praxis_core_instance.process_command_text(request.user_input)
    
    # Retrieve the summary of what Praxis "spoke" and the interaction ID
    ai_response = praxis_core_instance.last_ai_response_summary_for_feedback
    interaction_id = praxis_core_instance.last_interaction_id_for_feedback

    return CommandResponse(
        message="Command processed.",
        ai_response_summary=ai_response,
        interaction_id=interaction_id
    )

@app.get("/status", response_model=StatusResponse)
async def get_status():
    if not praxis_core_instance:
        raise HTTPException(status_code=503, detail="PraxisCore not available.")
    
    return StatusResponse(
        user=praxis_core_instance.current_user_name or "N/A",
        mode=praxis_core_instance.input_mode_config.get('mode', "N/A"),
        praxis_state=praxis_core_instance.skill_context.ai_name if praxis_core_instance.skill_context else "Initializing", # Simplified state
        ai_name=praxis_core_instance.ai_name,
        rpm=f"{praxis_core_instance.get_current_rpm()}/{GEMINI_1_5_FLASH_RPM}",
        tpm=f"{praxis_core_instance.get_current_tpm()}/{GEMINI_1_5_FLASH_TPM}",
        rpd=f"{praxis_core_instance.daily_request_count}/{GEMINI_1_5_FLASH_RPD}"
    )

@app.get("/logs", response_model=List[LogEntry])
async def get_codex_logs(lines: int = 100):
    log_file_path = "codex.log"
    if not os.path.exists(log_file_path):
        raise HTTPException(status_code=404, detail="Log file not found.")
    try:
        with open(log_file_path, "r", encoding="utf-8", errors="replace") as f:
            log_lines = f.readlines()
        return [LogEntry(line=line.strip()) for line in log_lines[-lines:]]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading log file: {str(e)}")

if __name__ == "__main__":
    # Ensure this script is run from the project root where main.py is located
    # or that main.py is correctly in PYTHONPATH.
    if not PraxisCore:
        print("Exiting API server due to PraxisCore import failure.")
    else:
        uvicorn.run(app, host="127.0.0.1", port=8000)