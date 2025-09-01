# gpt/inference.py

import ollama

# Make sure you've pulled the model first:
# ollama pull gpt-oss:20b

def query_gpt(prompt: str) -> str:
    try:
        response = ollama.chat(
            model="gpt-oss:20b",
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 1.0}
        )
        return response['message']['content'].strip()
    except Exception as e:
        print(f"[!] GPT call failed: {e}")
        return "[GPT ERROR] The chicken remained silent."

