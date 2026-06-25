import os
from PIL import Image, ImageDraw, ImageFont

OUT = "frontend/static/images"
os.makedirs(OUT, exist_ok=True)

CANDIDATES = [
    ("c1.jpg", "#1a3a6b", "أ"),
    ("c2.jpg", "#c8a84b", "س"),
    ("c3.jpg", "#1db954", "م"),
    ("c4.jpg", "#8b5cf6", "ن"),
    ("default-candidate.jpg", "#6b7280", "؟"),
]

for fname, color, letter in CANDIDATES:
    img = Image.new("RGB", (300, 300), color)
    draw = ImageDraw.Draw(img)
    draw.ellipse([20, 20, 280, 280], fill=color, outline="white", width=6)
    try:
        font = ImageFont.truetype("arial.ttf", 120)
    except:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), letter, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((300-w)//2, (300-h)//2 - 10), letter, fill="white", font=font)
    img.save(os.path.join(OUT, fname))
    print(f"Created: {fname}")

print("Done!")
