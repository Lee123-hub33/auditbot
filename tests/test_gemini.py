# test_gemini.py
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Error: GEMINI_API_KEY not found in environment variables.")
else:
    print(f"Key found: {api_key[:5]}... Testing connection...")
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content("Say 'Hello, API is working!'")
        print(f"Success! Response: {response.text}")
    except Exception as e:
        print(f"Failed to connect: {e}")