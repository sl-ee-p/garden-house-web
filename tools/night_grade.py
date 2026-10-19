"""Turn the original poolside photo into a moonlit night version for the dark Signature design.

Only the original photo is used: the sky is masked and repainted as a night sky (keeping the
original clouds as faint moonlit clouds), the rest of the scene is graded to night and the
garden house front is lifted by a soft cool moonlight from the upper left.

    python3 -m venv .venv && .venv/bin/pip install pillow numpy scipy
    .venv/bin/python tools/night_grade.py
"""
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / 'assets' / 'img'
SRC = IMG / 'sally-piscina-1200.webp'
WIDTHS = (480, 720, 1200)
MOON = (450, 360)  # moon centre in 1200 px coordinates
rng = np.random.default_rng(7)


def smooth(a, s):
    return ndimage.gaussian_filter(a, s)


def sky_mask(rgb):
    h, w, _ = rgb.shape
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx, mn = rgb.max(-1), rgb.min(-1)
    sat = (mx - mn) / (mx + 1e-6)
    blue = (b > r + 0.12) & (b > g + 0.02) & (b > 0.45)
    cloud = (mn > 0.70) & (sat < 0.22)
    cand = blue | cloud
    yy, xx = np.mgrid[0:h, 0:w]
    cand &= yy < 1000
    # the garden house itself: front face, then the side face whose top slopes down to the right
    roof = np.where(xx <= 988, 446, 446 + (xx - 988) * 38 / 149)
    cand &= ~((xx >= 398) & (xx <= 1137) & (yy >= roof))
    lab, _ = ndimage.label(cand)
    keep = np.unique(lab[:40][lab[:40] > 0])  # regions connected to the top edge
    big = np.bincount(lab.ravel())
    ids = set(keep) | {i for i in range(1, len(big)) if big[i] > 400 and i not in keep and
                      (yy[lab == i].mean() < 760)}
    m = np.isin(lab, list(ids)).astype(np.float32)
    # small gaps between leaves read as sky too, so close the mask a little
    m = ndimage.binary_closing(m > 0.5, iterations=1).astype(np.float32)
    return np.clip(smooth(m, 1.2), 0, 1)


def night_sky(rgb, h, w):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    t = np.clip(yy / 1000, 0, 1)[..., None]
    top = np.array([0.020, 0.035, 0.075])
    hor = np.array([0.060, 0.090, 0.150])
    sky = top * (1 - t) + hor * t
    # moon halo
    d = np.hypot(xx - MOON[0], yy - MOON[1])
    halo = (np.exp(-(d / 70) ** 2) * 0.22 + np.exp(-(d / 260) ** 2) * 0.07)[..., None]
    sky = sky + halo * np.array([0.75, 0.82, 0.95])
    # original clouds, dim and cool, brighter near the moon
    lum = rgb @ np.array([0.299, 0.587, 0.114])
    mn = rgb.min(-1)
    cloudiness = np.clip((mn - 0.55) / 0.4, 0, 1)
    cloudiness = smooth(cloudiness, 0.8)
    lit = 0.10 + 0.35 * np.exp(-(d / 420) ** 2)
    cloud_col = (lum * lit)[..., None] * np.array([0.78, 0.84, 0.98])
    sky = sky * (1 - cloudiness[..., None] * 0.85) + cloud_col * cloudiness[..., None]
    # stars, hidden behind clouds and the moon glow, thinner towards the horizon
    stars = np.zeros((h, w), np.float32)
    n = 520
    sy = rng.uniform(0, 900, n).astype(int)
    sx = rng.uniform(0, w, n).astype(int)
    mag = rng.power(3.5, n) ** 3
    stars[sy, sx] = mag * 0.9
    stars = smooth(stars, 0.55) * 4.5
    bright = rng.random(n) < 0.06
    big = np.zeros_like(stars)
    big[sy[bright], sx[bright]] = 1
    stars += smooth(big, 1.1) * 3.0
    vis = (1 - cloudiness) * (1 - np.clip(halo[..., 0] * 5, 0, 1)) * np.clip(1.2 - yy / 900, 0, 1)
    sky = sky + (stars * vis)[..., None] * np.array([0.92, 0.95, 1.0])
    # moon disc
    disc = np.clip(1 - (d - 15) / 1.5, 0, 1)
    sky = sky * (1 - disc[..., None]) + disc[..., None] * np.array([0.93, 0.94, 0.90])
    return sky


def night_scene(rgb, h, w):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    lum = (rgb @ np.array([0.299, 0.587, 0.114]))[..., None]
    # pull most of the colour out (the eye sees little colour at night), keep a little of the pool
    pool = np.clip(((rgb[..., 2] - rgb[..., 0]) - 0.25) / 0.2, 0, 1) * (yy > 1150)
    pool = smooth(pool, 2)[..., None]
    sat = 0.30 + 0.45 * pool
    out = lum + (rgb - lum) * sat
    out = out * np.array([0.72, 0.86, 1.08])
    out = np.clip(out, 0, 1) ** 1.25 * 0.36
    # moonlight from the upper left: lit front of the house, falloff across the garden
    light = np.clip(1 - np.hypot((xx - 520) / 900, (yy - 700) / 700), 0, 1) ** 1.5
    front = ((xx > 398) & (xx < 985) & (yy > 448) & (yy < 1100)).astype(np.float32)
    front = smooth(front, 3)
    gain = 1 + 0.35 * light + 0.45 * front
    out = out * gain[..., None]
    return out


def grade(src):
    rgb = np.asarray(src.convert('RGB'), np.float32) / 255
    h, w, _ = rgb.shape
    m = sky_mask(rgb)[..., None]
    out = night_scene(rgb, h, w) * (1 - m) + night_sky(rgb, h, w) * m
    # gentle vignette and fine grain, so the dark areas don't band
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    v = 1 - 0.22 * (np.hypot((xx - w / 2) / w, (yy - h * 0.45) / h) * 1.6) ** 2
    out = out * v[..., None] + rng.normal(0, 0.006, out.shape)
    return Image.fromarray((np.clip(out, 0, 1) ** (1 / 1.0) * 255 + 0.5).astype(np.uint8))


def main():
    night = grade(Image.open(SRC))
    for w in WIDTHS:
        h = round(night.height * w / night.width)
        night.resize((w, h), Image.LANCZOS).save(IMG / f'sally-piscina-notte-{w}.webp', quality=82, method=6)
    print('wrote', ', '.join(f'sally-piscina-notte-{w}.webp' for w in WIDTHS))


if __name__ == '__main__':
    main()
