"""Layout shared by the texture painter and the Blender build.

Paper atlas: pixel coordinates at the 2048 authoring size, x right and y down.
Mask space: meters on the mask plane, x to the viewer's right and y up, with the
mask's face centered near the origin.
"""
import math

import numpy as np

# ---------------------------------------------------------------- paper atlas
ATLAS = 2048
CELL_W, CELL_H, GUTTER = 404, 560, 4
COLS, ROWS = 5, 3

# Poster and flyer designs. The first six get a dry and a soaked copy.
DESIGNS = ["tomorrow", "pure", "tower", "flow", "hydrated", "green", "funday", "visitor", "smile"]
CELLS = [(d, 0) for d in DESIGNS[:6]] + [(d, 1) for d in DESIGNS[:6]] + [(d, 0) for d in DESIGNS[6:]]
DRY_CELLS = [i for i, (_, wet) in enumerate(CELLS) if not wet]
WET_CELLS = [i for i, (_, wet) in enumerate(CELLS) if wet]


def cell_rect(i):
    """Pixel rect (x0, y0, x1, y1) of poster cell i."""
    c, r = i % COLS, i // COLS
    x0 = GUTTER + c * (CELL_W + GUTTER)
    y0 = GUTTER + r * (CELL_H + GUTTER)
    return x0, y0, x0 + CELL_W, y0 + CELL_H


MISC_Y0 = GUTTER + ROWS * (CELL_H + GUTTER)
REGIONS = {
    "back": (4, MISC_Y0, 680, ATLAS - 4),     # wet paper back side
    "pulp": (684, MISC_Y0, 1364, ATLAS - 4),  # dark papier-mache core
    "tape": (1368, MISC_Y0, 1700, ATLAS - 4), # yellowed packing tape, length along x
    "void": (1704, MISC_Y0, ATLAS - 4, ATLAS - 4),  # near-black hollow
}


def px_to_uv(x, y):
    return x / ATLAS, 1.0 - y / ATLAS


def rect_uv(rect, inset=6):
    """UV rect (u0, v0, u1, v1) of a pixel rect, inset to stay clear of mip bleed."""
    x0, y0, x1, y1 = rect
    u0, v1 = px_to_uv(x0 + inset, y0 + inset)
    u1, v0 = px_to_uv(x1 - inset, y1 - inset)
    return u0, v0, u1, v1


# ---------------------------------------------------------------- mask shape
MASK_UV_SCALE = 0.48  # meters of mask per UV unit
MASK_YC = 0.02        # droplet center height
MASK_R = 0.23         # droplet half height (tip at y = 0.25)
MASK_HW = 0.17        # half width at the widest point
MASK_M = 1.1          # tip sharpness

_ts = np.linspace(0, 2 * math.pi, 4001)
_K = float(np.max(np.sin(_ts) * np.abs(np.sin(_ts / 2)) ** MASK_M))


def mask_uv(x, y):
    return 0.5 + x / MASK_UV_SCALE, 0.5 + (y - MASK_YC) / MASK_UV_SCALE


def droplet_point(t):
    x = MASK_HW * math.sin(t) * abs(math.sin(t / 2)) ** MASK_M / _K
    y = MASK_YC + MASK_R * math.cos(t)
    return x, y


def _jag(i, amp, seed):
    """Deterministic jitter for cut edges."""
    return amp * math.sin(i * 12.9898 + seed * 78.233) * math.sin(i * 4.1414 + seed * 3.7)


# Missing chunk on the viewer's left, between these droplet parameters.
NOTCH_T0, NOTCH_T1 = 4.86, 5.20
NOTCH_PATH = [(-0.122, 0.062), (-0.098, 0.076), (-0.104, 0.088), (-0.090, 0.099), (-0.093, 0.114)]
NOTCH_TIP = 1  # index in NOTCH_PATH where the crack starts


def mask_outline(n=150):
    """Outer outline (mask space), clockwise from the tip, with the broken notch cut in."""
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        if NOTCH_T0 < t < NOTCH_T1:
            continue
        pts.append(droplet_point(t))
        if i + 1 < n and t <= NOTCH_T0 < 2 * math.pi * (i + 1) / n:
            pts.append(droplet_point(NOTCH_T0))
            pts.extend(NOTCH_PATH)
            pts.append(droplet_point(NOTCH_T1))
    return pts


# Eye holes: center, radii, tilt (deg). Deliberately mismatched.
EYES = [
    ((-0.064, 0.004), (0.028, 0.042), 7.0),
    ((0.066, -0.004), (0.031, 0.047), -5.0),
]


def eye_outline(k, n=30, grow=0.0):
    (cx, cy), (rx, ry), tilt = EYES[k]
    a = math.radians(tilt)
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        j = 1.0 + _jag(i, 0.07, k + 1) if grow == 0.0 else 1.0
        x, y = (rx + grow) * math.cos(t) * j, (ry + grow) * math.sin(t) * j
        pts.append((cx + x * math.cos(a) - y * math.sin(a), cy + x * math.sin(a) + y * math.cos(a)))
    return pts


SMILE_HW = 0.090


def smile_y(x):
    """Center line of the grin: corners up, middle sagging."""
    return -0.124 + 0.036 * (x / SMILE_HW) ** 2


def smile_slit(n=22):
    """Hole polygon of the knife-cut slit along the grin."""
    upper, lower = [], []
    for i in range(n + 1):
        x = -SMILE_HW + 2 * SMILE_HW * i / n
        f = 1 - (x / SMILE_HW) ** 2
        h = 0.0012 + 0.0068 * f ** 0.8
        upper.append((x, smile_y(x) + h + _jag(i, 0.0014, 7) * f))
        lower.append((x, smile_y(x) - h - _jag(i, 0.0018, 9) * f))
    # drop the shared end points so the polygon is simple
    return upper + lower[::-1][1:-1]


def crack_path():
    """Crack from the notch to the left eye hole; ends on an eye outline vertex."""
    start = NOTCH_PATH[NOTCH_TIP]
    eye = eye_outline(0)
    end_i = min(range(len(eye)), key=lambda i: (eye[i][0] + 0.090) ** 2 + (eye[i][1] - 0.046) ** 2)
    mid = [(-0.093, 0.068), (-0.095, 0.060), (-0.087, 0.054), (-0.086, 0.045)]
    return [start] + mid + [eye[end_i]], end_i


def grin_outline(n=40):
    """Painted open grin around the slit (texture only)."""
    w = 0.100
    up, lo = [], []
    for i in range(n + 1):
        x = -w + 2 * w * i / n
        f = max(0.0, 1 - (x / w) ** 2)
        up.append((x, smile_y(x * SMILE_HW / w) + 0.007 * f ** 0.5))
        lo.append((x, smile_y(x * SMILE_HW / w) - 0.006 - 0.026 * f ** 0.9))
    return up + lo[::-1]
