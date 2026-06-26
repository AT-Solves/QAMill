"""
Test Gemini API directly to diagnose the issue
Run: python test_gemini.py <your-gemini-api-key>
"""
import sys
import httpx
import json

if len(sys.argv) < 2:
    print("Usage: python test_gemini.py <gemini-api-key>")
    sys.exit(1)

api_key = sys.argv[1]
prompt = "Say 'WORKING' in one word."

print("\n" + "="*70)
print("GEMINI API DIAGNOSTIC TEST")
print("="*70)

# Test different endpoint variations
endpoints = [
    {
        "name": "v1beta with model",
        "url": f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
        "auth_type": "query_param"
    },
    {
        "name": "v1 with model",
        "url": f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent",
        "auth_type": "query_param"
    },
    {
        "name": "v1beta with pro model",
        "url": f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
        "auth_type": "query_param"
    },
    {
        "name": "v1 with pro model",
        "url": f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent",
        "auth_type": "query_param"
    },
]

for test in endpoints:
    print(f"\n[TEST] {test['name']}")
    print(f"  URL: {test['url']}")

    try:
        with httpx.Client(timeout=10) as client:
            response = client.post(
                test['url'],
                params={"key": api_key},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"maxOutputTokens": 100},
                },
            )

            print(f"  Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                result = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                print(f"  Result: ✅ SUCCESS")
                print(f"  Response: {result[:100]}")
            else:
                print(f"  Result: ❌ FAILED")
                try:
                    error = response.json()
                    print(f"  Error: {json.dumps(error, indent=2)[:300]}")
                except:
                    print(f"  Response: {response.text[:300]}")

    except Exception as e:
        print(f"  Result: ❌ EXCEPTION")
        print(f"  Error: {str(e)[:200]}")

print("\n" + "="*70)
print("DIAGNOSTIC COMPLETE")
print("="*70 + "\n")
