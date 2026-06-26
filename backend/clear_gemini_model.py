"""
Clear old Gemini model from storage to use new default
This forces it to use gemini-3.5-flash (latest)
"""
import json
from pathlib import Path

auth_file = Path.home() / ".qamill" / "auth.json"

if not auth_file.exists():
    print(f"Auth file not found: {auth_file}")
    exit(1)

print(f"Reading auth file: {auth_file}")
data = json.loads(auth_file.read_text())

if "llm" in data and "gemini" in data["llm"]:
    gemini_config = data["llm"]["gemini"]
    old_model = gemini_config.get("model")

    print(f"\nFound Gemini configuration:")
    print(f"  API Key: {gemini_config.get('api_key', 'N/A')[:20]}...")
    print(f"  Old Model: {old_model}")

    # Remove the old model - will use adapter default (gemini-3.5-flash)
    if "model" in gemini_config:
        del gemini_config["model"]
        print(f"  → Deleted old model, will use: gemini-3.5-flash")

    # Save back
    auth_file.write_text(json.dumps(data, indent=2))
    print(f"\n✅ Auth file updated!")
    print(f"Next generation will use gemini-3.5-flash\n")
else:
    print("Gemini not found in auth file")
