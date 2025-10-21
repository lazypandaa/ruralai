import google.generativeai as genai
import os

# --- WARNING: Using a hardcoded API key is not secure. ---
# This script uses the key for quick verification.
# It's recommended to switch back to environment variables for your project.
API_KEY = "AIzaSyB6CGK-X3QQ-xBVDyhZ9pFIXYkIKiva0yg"

try:
    genai.configure(api_key=API_KEY)

    print("Fetching available models for your API key...\n")
    print("="*40)
    print("Models supporting 'generateContent':")
    print("="*40)

    # List only the models that support the 'generateContent' method,
    # as this is what your application uses.
    for m in genai.list_models():
      if 'generateContent' in m.supported_generation_methods:
        print(f"  - {m.name}")

    print("\nThese are the models you can use in your `GeminiClient` class.")

except Exception as e:
    print(f"An error occurred: {e}")
    print("\nPlease double-check that your API key is correct and has billing enabled if required.")