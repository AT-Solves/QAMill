"""
Run this ONCE after saving qamill-logo.png in this folder:
    python backend/assets/install_logo.py

It:
 1. Creates base64 txt files for the HTML report + favicon
 2. Copies the PNG to vscode-extension/media/ for the extension icon
 3. Regenerates the demo report so the logo shows immediately
"""
import base64, shutil, sys
from pathlib import Path

ROOT   = Path(__file__).parent.parent.parent   # repo root
HERE   = Path(__file__).parent
logo   = HERE / "qamill-logo.png"
MEDIA  = ROOT / "vscode-extension" / "media"

if not logo.exists():
    print("ERROR: save the logo as", logo)
    sys.exit(1)

# 1. base64 for HTML report
raw = logo.read_bytes()
b64 = base64.b64encode(raw).decode()
(HERE / "qamill-logo-b64.txt").write_text(b64)
print(f"[OK] logo base64 written ({len(b64)} chars)")

# 2. favicon (32×32 if Pillow available, else same image)
try:
    from PIL import Image
    import io
    img = Image.open(logo).convert("RGBA").resize((32, 32), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    fav_b64 = base64.b64encode(buf.getvalue()).decode()
    print("[OK] 32×32 favicon generated via Pillow")
except ImportError:
    fav_b64 = b64
    print("[  ] Pillow not installed — using full PNG as favicon")
(HERE / "qamill-favicon-b64.txt").write_text(fav_b64)

# 3. copy to VS Code extension media folder
MEDIA.mkdir(exist_ok=True)
shutil.copy2(logo, MEDIA / "qamill-logo.png")
print(f"[OK] copied to {MEDIA / 'qamill-logo.png'}")

# 4. regenerate demo report
import subprocess, sys as _sys
result = subprocess.run(
    [_sys.executable, str(ROOT / "backend" / "report_generator.py"),
     str(ROOT / "sample_project" / "Reports" / "qamill-elite-report.html")],
    capture_output=True, text=True
)
if result.returncode == 0:
    print("[OK] demo report regenerated:", result.stdout.strip())
else:
    print("[WARN] report regen failed:", result.stderr[:200])

print("\nDone. Reload VS Code window to see the extension icon.")
