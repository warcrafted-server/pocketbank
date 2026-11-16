"""Genera docs/img/logo.png (400x400): bolsa de cuero con moneda, dibujada por código."""

from pathlib import Path

from PIL import Image, ImageDraw

S = 400
OUT = Path(__file__).resolve().parent.parent / "docs" / "img" / "logo.png"

img = Image.new("RGBA", (S, S), (28, 20, 14, 255))
d = ImageDraw.Draw(img)
d.rounded_rectangle((8, 8, S - 9, S - 9), 28, outline=(170, 135, 60), width=6, fill=(40, 30, 22))
d.rounded_rectangle((20, 20, S - 21, S - 21), 20, outline=(90, 70, 35), width=2)

# cuerpo de la bolsa
d.ellipse((90, 150, 310, 350), fill=(120, 78, 40), outline=(60, 38, 18), width=6)
d.ellipse((120, 175, 215, 270), fill=(146, 98, 54))
# cuello y cuerda
d.polygon([(150, 160), (250, 160), (278, 112), (122, 112)], fill=(104, 66, 34), outline=(60, 38, 18))
d.rounded_rectangle((136, 150, 264, 176), 10, fill=(232, 190, 80), outline=(150, 105, 40), width=4)
# picos de la boca
d.polygon([(122, 112), (100, 66), (150, 100)], fill=(120, 78, 40), outline=(60, 38, 18))
d.polygon([(278, 112), (300, 66), (250, 100)], fill=(120, 78, 40), outline=(60, 38, 18))
d.polygon([(150, 100), (200, 62), (250, 100), (278, 112), (122, 112)], fill=(104, 66, 34), outline=(60, 38, 18))
# moneda
cx, cy, r = 200, 262, 46
d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(232, 190, 80), outline=(150, 105, 40), width=6)
d.ellipse((cx - r + 12, cy - r + 12, cx + r - 12, cy + r - 12), outline=(190, 145, 50), width=3)
d.ellipse((cx - 14, cy - 14, cx + 14, cy + 14), fill=(150, 105, 40))

OUT.parent.mkdir(parents=True, exist_ok=True)
img.convert("RGB").save(OUT)
img.convert("RGBA").resize((64, 64)).save(OUT.parent.parent.parent / "Media" / "logo.tga")
print(OUT)
