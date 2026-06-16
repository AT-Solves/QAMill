"""
embed_logo.py — run once after placing qamill-logo.png in this folder.
Converts the PNG to base64 and writes:
  - assets/qamill-logo-b64.txt   (base64 string for Python to import)
  - assets/qamill-favicon-b64.txt (32x32 resized favicon)
"""
import base64, sys
from pathlib import Path

HERE   = Path(__file__).parent
logo   = HERE / "qamill-logo.png"

if not logo.exists():
    print("ERROR: qamill-logo.png not found in", HERE)
    sys.exit(1)

raw = logo.read_bytes()
b64 = base64.b64encode(raw).decode()

(HERE / "qamill-logo-b64.txt").write_text(b64)
print(f"Logo saved: {len(b64)} base64 chars")

# Try to make a favicon via Pillow (optional)
try:
    from PIL import Image
    import io
    img = Image.open(logo).convert("RGBA").resize((32, 32), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    fav_b64 = base64.b64encode(buf.getvalue()).decode()
    (HERE / "qamill-favicon-b64.txt").write_text(fav_b64)
    print(f"Favicon saved: {len(fav_b64)} base64 chars")
except ImportError:
    # Pillow not installed — use the full logo as favicon too
    (HERE / "qamill-favicon-b64.txt").write_text(b64)
    print("Pillow not found — using full logo as favicon (install Pillow for proper 32x32)")
