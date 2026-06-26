"""
Direct test to see Gemini response format
Run: python test_gemini_response.py <api-key>
"""
import sys
import httpx
import json

if len(sys.argv) < 2:
    print("Usage: python test_gemini_response.py <gemini-api-key>")
    sys.exit(1)

api_key = sys.argv[1]
prompt = "Generate a simple Python test function. Just write the code."

print("\n" + "="*70)
print("GEMINI RESPONSE FORMAT TEST")
print("="*70)

endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent"

print(f"\nEndpoint: {endpoint}")
print(f"Model: gemini-3.5-flash")
print(f"Prompt: {prompt[:50]}...\n")

try:
    with httpx.Client(timeout=30) as client:
        response = client.post(
            endpoint,
            params={"key": api_key},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": 500},
            },
        )

        print(f"Status: {response.status_code}\n")

        if response.status_code == 200:
            data = response.json()

            print("FULL RESPONSE:")
            print(json.dumps(data, indent=2))

            print("\n" + "="*70)
            print("PARSING TEST:")
            print("="*70)

            # Test extraction
            print(f"\nResponse keys: {list(data.keys())}")

            candidates = data.get("candidates", [])
            print(f"candidates length: {len(candidates)}")

            if candidates:
                content = candidates[0].get("content", {})
                print(f"content keys: {list(content.keys())}")

                parts = content.get("parts", [])
                print(f"parts length: {len(parts)}")

                if parts:
                    text = parts[0].get("text", "")
                    print(f"\nExtracted text length: {len(text)}")
                    print(f"Extracted text:\n{text[:300]}")

        else:
            print(f"Error: {response.text}")

except Exception as e:
    print(f"Exception: {str(e)}")

print("\n" + "="*70 + "\n")
