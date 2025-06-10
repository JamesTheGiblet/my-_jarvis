# config.py
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Securely configure the API key
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")
model = None

try:
    if not GOOGLE_API_KEY:
        raise ValueError("GEMINI_API_KEY not found in your .env file.")
    
    genai.configure(api_key=GOOGLE_API_KEY)
    
    # Use the recommended model name
    model = genai.GenerativeModel('gemini-1.5-flash')
    print("AI Brain configured successfully.")

except Exception as e:
    print(f"Error configuring Google AI: {e}")
    
# Rate Limits for Gemini 1.5 Flash (as of documentation when this was added)
# These are for reference and potential client-side checks, actual limits are enforced by the API.
GEMINI_1_5_FLASH_RPM = 15  # Requests Per Minute
GEMINI_1_5_FLASH_TPM = 1000000  # Tokens Per Minute
GEMINI_1_5_FLASH_RPD = 1500 # Requests Per Day