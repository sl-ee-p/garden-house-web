"""Make flat, tileable surface textures for the configurator from the brochure's panel photos.

Each photo in assets/img/finiture shows one 500 mm board in the same 3/4 view. The board face is
rectified to a flat rectangle, the plain lower half (between the groove and the bottom edge) is kept,
and the studio shading is evened out, so only the colour and the grain of the finish remain.
The 3D model already carries the boards' joints and grooves, so the texture must not repeat them.

    python3 -m venv .venv && .venv/bin/pip install pillow numpy scipy
    .venv/bin/python tools/panel_textures.py
"""
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'assets' / 'img' / 'finiture'
OUT = SRC / 'tex'

# Corners of the board face in every 378 x 423 photo (same render setup for all 16):
# top-left, top-right, bottom-right, bottom-left.
FACE = [(57, 47), (334, 62), (334, 345), (57, 389)]
W, H = 600, 500  # rectified board face, about 1 px per mm
LOWER = (300, 474)  # rows of the plain lower face in the rectified board, clear of groove and edge
SIZE = (512, 160)


def homography(src, dst):
    # coefficients for PIL's perspective transform, mapping output (dst) to input (src) pixels
    a = []
    for (x, y), (u, v) in zip(dst, src):
        a.append([x, y, 1, 0, 0, 0, -u * x, -u * y, -u])
        a.append([0, 0, 0, x, y, 1, -v * x, -v * y, -v])
    _, _, vt = np.linalg.svd(np.array(a, float))
    h = vt[-1] / vt[-1][-1]
    return tuple(h[:8])


def texture(path):
    im = Image.open(path).convert('RGB')
    coeffs = homography(FACE, [(0, 0), (W, 0), (W, H), (0, H)])
    flat = im.transform((W, H), Image.PERSPECTIVE, coeffs, Image.BICUBIC)
    face = np.asarray(flat, np.float32)[LOWER[0]:LOWER[1], 14:W - 26]
    # even out the render's light falloff, keep the grain
    shade = ndimage.gaussian_filter(face.mean(-1), 40)
    face = face * (shade.mean() / shade)[..., None]
    out = Image.fromarray(np.clip(face, 0, 255).astype(np.uint8)).resize(SIZE, Image.LANCZOS)
    return out


def main():
    OUT.mkdir(exist_ok=True)
    names = []
    for path in sorted(SRC.glob('*-378.webp')):
        name = path.name.replace('-378.webp', '')
        texture(path).save(OUT / f'{name}.webp', quality=86, method=6)
        names.append(name)
    print(len(names), 'textures in', OUT.relative_to(ROOT))


if __name__ == '__main__':
    main()
