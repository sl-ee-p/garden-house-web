"""Foto 5 (night photo at the end of the home page).

usage: python tools/finale_refine.py trim   SRC.jpg   -> placeholder exports
       python tools/finale_refine.py refine SRC.jpg   -> refined exports (stage 2)

The supplied file carries black pillarbox bars (about 393 px each side) that
are not part of the scene: trim() finds the scene by a luminance column scan
and keeps a 2 px safety margin. The source file is never written.
Exports assets/img/finale-notte-{960,1440,W}.{avif,webp} plus a JPG fallback.
Needs numpy, Pillow and (for refine) OpenCV.
"""
import pathlib
import sys

import numpy as np
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'assets' / 'img'


def trim(img):
    lum = np.asarray(img.convert('L')).astype(float)
    cols = np.where(lum.mean(axis=0) > 14)[0]
    x0, x1 = cols[0] + 2, cols[-1] - 1
    rows = np.where(lum[:, x0:x1].max(axis=1) > 14)[0]  # no bars top/bottom expected
    y0, y1 = rows[0], rows[-1] + 1
    return img.crop((x0, y0, x1, y1))


def export(img, name='finale-notte'):
    full = img.width
    for w in (960, 1440, full):
        im = img if w == full else img.resize((w, round(img.height * w / img.width)), Image.LANCZOS)
        im.save(OUT / f'{name}-{w}.webp', quality=82, method=6)
        im.save(OUT / f'{name}-{w}.avif', quality=60, speed=4)
        print(name, w, im.size)
    img.save(OUT / f'{name}-{full}.jpg', quality=84, optimize=True, progressive=True)
    return full


def main():
    stage, src = sys.argv[1], sys.argv[2]
    img = trim(Image.open(src).convert('RGB'))
    if stage == 'refine':
        from finale_masks import refine  # stage 2, see tools/finale_masks.py
        img = refine(img)
    export(img)


if __name__ == '__main__':
    main()
