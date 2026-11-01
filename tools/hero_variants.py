"""Responsive variants of the home hero from the live site's full-resolution
original (https://www.techs-gardenhouse.com/images/test3.jpg, 3024x1369).

usage: python tools/hero_variants.py /path/to/test3.jpg
Writes assets/img/hero-giardino-{960,1440,2048,3024}.{webp,avif}.
Same framing as before: the whole photo, only resized. Needs Pillow.
"""
import pathlib
import sys

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
WIDTHS = (960, 1440, 2048, 3024)


def main():
    src = Image.open(sys.argv[1]).convert('RGB')
    out = ROOT / 'assets' / 'img'
    for w in WIDTHS:
        im = src if w >= src.width else src.resize((w, round(src.height * w / src.width)), Image.LANCZOS)
        im.save(out / f'hero-giardino-{w}.webp', quality=80, method=6)
        im.save(out / f'hero-giardino-{w}.avif', quality=58, speed=4)
        print(w, im.size)


if __name__ == '__main__':
    main()
