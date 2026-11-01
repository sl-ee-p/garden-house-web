"""Stage 2 of tools/finale_refine.py: targeted fixes to the AI night photo so
the house matches the real product. Coordinates are in the trimmed image
(1830x1206). Every fix is local and masked; nothing else is repainted.

1. Interior: the door glass and the punto luce showed invented rooms, a
   staircase and a railing. They become a plain warm light: a smooth
   low-order fit of the existing glow (so the light level and falloff stay
   the same) plus matched grain. Pixels that are not glow (the handle lever
   crossing the glass) are kept, weighted by how orange they are.
2. Door (variant B only): the real door is glazed on the upper part with a
   panelled lower leaf (see assets/img/concezione-*.webp and the 3D model).
   The lower leaf is rebuilt from the wall's own panel rows next to the door,
   with a frame rail where the glass ends.
3. Ground: odd objects and isolated sparkle specks are inpainted (OpenCV
   Telea); an unexplained lit strip beside the house takes the light level
   of the ground around it.
"""
import numpy as np
from PIL import Image

DOOR_GLASS = dict(x=(818, 970), y=(550, 1017))
WIN_GLASS = dict(x=(1128, 1172), y=(523, 930))


def _edges(glow, box, min_count):
    """Per-row glass span from the glow mask, then straight line fits."""
    (x0, x1), (y0, y1) = box['x'], box['y']
    ys, ls, rs = [], [], []
    for y in range(y0 + 3, y1 - 3):
        xs = np.where(glow[y, x0:x1])[0]
        if len(xs) >= min_count:
            ys.append(y); ls.append(x0 + xs[0]); rs.append(x0 + xs[-1])
    ys = np.array(ys, float)
    fl = np.polyfit(ys, ls, 1)
    fr = np.polyfit(ys, rs, 1)
    return fl, fr


def _quad_mask(shape, fl, fr, y0, y1):
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w]
    left = np.polyval(fl, yy)
    right = np.polyval(fr, yy)
    return (xx >= left - .5) & (xx <= right + .5) & (yy >= y0) & (yy <= y1)


def _smooth_fill(a, mask, rng):
    """Least-squares quadratic surface per channel over the glass, plus grain."""
    ys, xs = np.nonzero(mask)
    yn = (ys - ys.mean()) / (np.ptp(ys) + 1)
    xn = (xs - xs.mean()) / (np.ptp(xs) + 1)
    basis = np.stack([np.ones_like(yn), xn, yn, xn * xn, yn * yn, xn * yn], 1)
    out = a.copy()
    for c in range(3):
        v = a[ys, xs, c]
        coef, *_ = np.linalg.lstsq(basis, v, rcond=None)
        resid = v - basis @ coef
        keep = np.abs(resid) < 2.5 * resid.std() + 1  # ignore the invented objects
        coef, *_ = np.linalg.lstsq(basis[keep], v[keep], rcond=None)
        out[ys, xs, c] = basis @ coef
    grain = rng.normal(0, 1.6, (len(ys), 1))
    out[ys, xs] += grain
    return out


def _window(a, rng):
    """The punto luce: keep its jamb shading (the median column profile across
    all rows, which no single object survives) scaled by the smooth vertical
    light level; this removes the staircase and railing."""
    (x0, x1), (y0, y1) = WIN_GLASS['x'], WIN_GLASS['y']
    R, B = a[..., 0], a[..., 2]
    inside = (R - B > 3)[:, x0:x1]  # glass and dark jamb, not the grey frame
    lefts, rights = [], []
    ys = np.arange(y0, y1)
    for y in ys:
        xs = np.where(inside[y])[0]
        lefts.append(x0 + xs[0]); rights.append(x0 + xs[-1])
    fl = np.polyfit(ys, lefts, 1)
    fr = np.polyfit(ys, rights, 1)
    width = int(round(np.median(np.array(rights) - np.array(lefts)))) + 1
    rows = np.stack([a[y, int(round(np.polyval(fl, y))):][:width] for y in ys])
    profile = np.median(rows, axis=0)  # (width, 3)
    level = rows.mean(axis=(1, 2))
    trend = np.polyval(np.polyfit(ys, level, 2), ys) / profile.mean()
    out = a.copy()
    for i, y in enumerate(ys):
        xl = int(round(np.polyval(fl, y)))
        out[y, xl:xl + width] = profile * trend[i] + rng.normal(0, 1.4, (width, 1))
    return out


def interior(a, rng):
    R, B = a[..., 0], a[..., 2]
    glow = (R > 110) & (R - B > 45)
    weight = np.clip((R - B - 18) / 40, 0, 1)  # handle and frame pixels -> 0
    fl, fr = _edges(glow, DOOR_GLASS, 100)
    m = _quad_mask(a.shape[:2], fl, fr, *DOOR_GLASS['y'])
    filled = _smooth_fill(a, m, rng)
    alpha = (m * weight)[..., None]
    a = a * (1 - alpha) + filled * alpha
    return _window(a, rng)


# Odd objects on the ground (x0, y0, x1, y1, dx): a blue tyre-like shape at
# the left edge and a blue plastic-looking lump at the bottom. Each is covered
# with the ground dx pixels beside it, feathered.
GROUND_OBJECTS = [(0, 994, 50, 1034, 56), (136, 1160, 184, 1204, -52)]
# A lit orange strip on the ground right of the house that no light explains.
SIDE_LIGHT = (1462, 938, 1830, 1006)
HOUSE = (655, 330, 1485, 1078)


def ground(a):
    import cv2
    img = np.clip(a + .5, 0, 255).astype(np.uint8)
    h, w = img.shape[:2]
    for x0, y0, x1, y1, dx in GROUND_OBJECTS:
        soft = np.zeros((h, w), np.float32)
        soft[y0:y1, x0:x1] = 1
        soft = cv2.GaussianBlur(soft, (0, 0), 4)[..., None]
        shifted = np.roll(img, -dx, axis=1).astype(np.float32)
        img = (img * (1 - soft) + shifted * soft + .5).astype(np.uint8)
    mask = np.zeros((h, w), np.uint8)
    # isolated bright specks on the ground (stars stay: sky is above y 830)
    lum = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY).astype(int)
    med = cv2.medianBlur(lum.astype(np.uint8), 9).astype(int)
    speck = ((lum - med) > 26) & (lum > 60)
    speck[:830] = False
    hx0, hy0, hx1, hy1 = HOUSE
    speck[hy0:hy1, hx0:hx1] = False
    n, lab, stats, _ = cv2.connectedComponentsWithStats(speck.astype(np.uint8), 8)
    small = np.isin(lab, [i for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] <= 14])
    mask[cv2.dilate(small.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0] = 255
    img = cv2.inpaint(img, mask, 4, cv2.INPAINT_TELEA)
    a = img.astype(float)

    # side light: swap the strip's low frequencies for the neighbouring
    # ground's, keeping its own texture; soft edges
    x0, y0, x1, y1 = SIDE_LIGHT
    region = a[y0 - 40:y1 + 40, x0 - 40:x1]
    low = cv2.GaussianBlur(region, (0, 0), 14)
    above = a[y0 - 34:y0 - 6, x0:x1].reshape(-1, 3).mean(0)
    below = a[y1 + 6:y1 + 34, x0:x1].reshape(-1, 3).mean(0)
    target = (above + below) / 2
    soft = np.zeros(region.shape[:2])
    soft[40:40 + (y1 - y0), 40:] = 1
    soft = cv2.GaussianBlur(soft, (0, 0), 9)[..., None]
    a[y0 - 40:y1 + 40, x0 - 40:x1] = region + soft * (target - low)
    return a


def half_glass_door(a, rng):
    """Variant B. The real door is glazed on the upper ~60% of the leaf
    (concezione render: 140 of 228 px), panelled below. Below that line the
    glass becomes a frame rail plus panel rows continued from the wall right
    of the door (same grooves, same slope, same light)."""
    (gx0, gx1), (gy0, gy1) = (822, 967), DOOR_GLASS['y']
    split = int(gy0 + 0.61 * (gy1 - gy0))
    rail = 14
    stile = a[600:1000, 803:813].reshape(-1, 3).mean(0)  # door frame colour
    strip = a[:, 1000:1085]
    profile = np.median(strip, axis=1)  # per-row wall colour, grooves included
    slope = 0.022  # groove slope measured across the front wall (px/px)
    xc = 1042
    out = a.copy()
    warm = (a[..., 0] - a[..., 2]) > 10  # glass edge pixels around the core box
    for y in range(split, gy1 + 8):
        for x in range(gx0 - 6, gx1 + 6):
            core = gx0 - 1 <= x < gx1 + 1 and y <= gy1 + 1
            if not (core or warm[y, x]):
                continue
            if y < split + rail:
                out[y, x] = stile - (8 if y >= split + rail - 2 else 0)  # shadow line under the rail
            else:
                yy = y - slope * (x - xc)
                y0 = int(np.floor(yy)); f = yy - y0
                out[y, x] = profile[y0] * (1 - f) + profile[y0 + 1] * f
        out[y, gx0 - 1:gx1 + 1] += rng.normal(0, 1.2, (gx1 - gx0 + 2, 1)) * (y <= gy1 + 1)
    return out


def refine(img, variant='A'):
    rng = np.random.default_rng(7)
    a = np.asarray(img).astype(float)
    a = interior(a, rng)
    if variant == 'B':
        a = half_glass_door(a, rng)
    a = ground(a)
    return Image.fromarray(np.clip(a + .5, 0, 255).astype(np.uint8))
