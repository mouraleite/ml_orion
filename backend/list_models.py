import os
import google.generativeai as genai

# Try to list available models
try:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Set GEMINI_API_KEY environment variable to list models.")
    else:
        genai.configure(api_key=api_key)
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(m.name)
except Exception as e:
    import traceback
    traceback.print_exc()
