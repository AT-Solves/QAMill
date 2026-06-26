"""
List available Gemini models for your API key
Run: python list_gemini_models.py <your-gemini-api-key>
"""
import sys
import httpx
import json

if len(sys.argv) < 2:
    print("Usage: python list_gemini_models.py <gemini-api-key>")
    sys.exit(1)

api_key = sys.argv[1]

print("\n" + "="*70)
print("GEMINI AVAILABLE MODELS")
print("="*70 + "\n")

# Try to list models using v1 and v1beta
for api_version in ["v1", "v1beta"]:
    print(f"[{api_version}] Listing available models...")

    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(
                f"https://generativelanguage.googleapis.com/{api_version}/models",
                params={"key": api_key},
            )

            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])

                if models:
                    print(f"\nAvailable models in {api_version}:")
                    for model in models:
                        name = model.get("name", "unknown")
                        display_name = model.get("displayName", "")
                        supported_methods = model.get("supportedGenerationMethods", [])

                        # Extract just the model name (remove "models/" prefix)
                        model_name = name.replace("models/", "")

                        print(f"\n  Name: {model_name}")
                        print(f"  Display: {display_name}")
                        print(f"  Methods: {', '.join(supported_methods)}")
                else:
                    print(f"No models found in {api_version}")
            else:
                print(f"Status: {response.status_code}")
                try:
                    error = response.json()
                    print(f"Error: {json.dumps(error, indent=2)[:200]}")
                except:
                    print(f"Response: {response.text[:200]}")

    except Exception as e:
        print(f"Exception: {str(e)[:200]}\n")

print("\n" + "="*70)
print("COPY THE MODEL NAME (without 'models/' prefix) TO USE IN QAMill")
print("="*70 + "\n")
