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