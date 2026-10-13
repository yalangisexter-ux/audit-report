from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "assets" / "raw_strength_brand.png"
target = ROOT / "assets" / "raw_strength_icon.ico"
if not source.exists():
    raise SystemExit(f"Required existing brand artwork is missing: {source}")
with Image.open(source) as image:
    image = image.convert("RGBA")
    image.thumbnail((512, 512), Image.Resampling.LANCZOS)
    # Preserve the existing Raw Strength branding while producing crisp Windows
    # taskbar, title-bar, and installer icon sizes.
    image.save(target, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print(f"Generated branded Windows icon: {target}")
