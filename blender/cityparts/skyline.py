"""Background skyline: towers beyond the canyon that give the city depth.
They sit far enough away that the haze turns them into layered silhouettes
of lit floors and crown lights."""

import math

from . import materials as M
from .util import MeshBuilder, collection, rng, superellipse


def _oct(cx, cy, hx, hy, ch, z):
    c = min(hx, hy) * ch
    pts = [(hx, -(hy - c)), (hx, hy - c), (hx - c, hy), (-(hx - c), hy), (-hx, hy - c), (-hx, -(hy - c)), (-(hx - c), -hy), (hx - c, -hy)]
    return [(cx + x, cy + y, z) for x, y in pts]


def build(seed=17):
    R = rng(seed)
    col = collection('Skyline')
    walls = [
        M.window_wall('SkyA', cell_w=1.6, floor_h=4.0, lit=0.38, strength=3.0, office=True),
        M.window_wall('SkyB', cell_w=2.6, floor_h=3.3, lit=0.5, strength=2.6, office=False, mullion=0.35),
        M.window_wall('SkyC', cell_w=1.3, floor_h=4.2, lit=0.3, strength=3.4, office=True, warm=(0.8, 0.9, 1.0), cool=(0.6, 0.8, 1.0)),
        M.window_wall('SkyD', cell_w=3.2, floor_h=3.6, lit=0.55, strength=2.4, office=False, mullion=0.5, warm=(1.0, 0.55, 0.3)),
    ]
    crowns = [M.emission(f'SkyCrown{i}', c, 18.0) for i, c in enumerate([
        (1.0, 0.08, 0.45), (0.05, 0.8, 1.0), (0.6, 0.2, 1.0), (1.0, 0.5, 0.1), (0.9, 0.95, 1.0)])]
    roof = M.concrete('SkyRoof', tone=0.05)
    beacon = M.emission('SkyBeacon', (1.0, 0.05, 0.03), 60.0)
    mats = walls + crowns + [roof, beacon]
    ROOF, BEACON = len(walls) + len(crowns), len(walls) + len(crowns) + 1
    mb = MeshBuilder()

    def ok(x, y, r):
        if abs(x) < 30 + r and -420 < y < 600:      # keep the canyon clear
            return False
        if math.hypot(x, y - 700) < 140 + r:        # spire plaza
            return False
        if -230 - r < x < 210 + r and -260 < y < 420:  # hero buildings and their surroundings
            return False
        return True

    placed = []
    tries = 0
    while len(placed) < 58 and tries < 4000:
        tries += 1
        side = R.random()
        if side < 0.32:
            x, y = R.uniform(-900, -190), R.uniform(-500, 1600)
        elif side < 0.64:
            x, y = R.uniform(150, 900), R.uniform(-500, 1600)
        elif side < 0.9:
            x, y = R.uniform(-700, 700), R.uniform(850, 2200)
        else:
            x, y = R.uniform(-600, 600), R.uniform(-900, -450)
        hx, hy = R.uniform(14, 34), R.uniform(14, 34)
        rad = math.hypot(hx, hy)
        if not ok(x, y, rad) or any(math.hypot(x - px, y - py) < rad + pr + 18 for px, py, pr in placed):
            continue
        placed.append((x, y, rad))
        dist_spire = math.hypot(x, y - 700)
        hgt = R.uniform(80, 220) * (1.0 + 1.2 * math.exp(-dist_spire / 700)) * (R.random() < 0.15 and 1.6 or 1.0)
        wm = R.randrange(len(walls))
        kind = R.choices(['setback', 'cyl', 'twin', 'zig'], [4, 2, 1, 1.5])[0]
        cm = len(walls) + R.randrange(len(crowns))
        if kind == 'setback':
            z, sx, sy = 0.0, hx, hy
            segs = R.randint(2, 4)
            for s in range(segs):
                z1 = hgt if s == segs - 1 else z + hgt * R.uniform(0.35, 0.55) * (1 - z / hgt)
                mb.ring_strip(_oct(x, y, sx, sy, 0.25, z), _oct(x, y, sx, sy, 0.25, z1), wm)
                mb.cap(_oct(x, y, sx, sy, 0.25, z1), ROOF)
                if R.random() < 0.5:
                    mb.ring_strip(_oct(x, y, sx + 0.3, sy + 0.3, 0.25, z1 - 1.2), _oct(x, y, sx + 0.3, sy + 0.3, 0.25, z1 - 0.6), cm)
                z = z1
                sx *= R.uniform(0.7, 0.88)
                sy *= R.uniform(0.7, 0.88)
            top = hgt
        elif kind == 'cyl':
            r = min(hx, hy)
            ring = lambda rr, zz: [(x + rr * math.cos(2 * math.pi * k / 40), y + rr * math.sin(2 * math.pi * k / 40), zz) for k in range(40)]
            mb.ring_strip(ring(r, 0), ring(r * 0.85, hgt), wm)
            mb.cap(ring(r * 0.85, hgt), ROOF)
            for zz in (hgt - 6, hgt - 2.5):
                mb.ring_strip(ring(r * 0.86, zz), ring(r * 0.86, zz + 0.8), cm)
            top = hgt
        elif kind == 'twin':
            for s in (-1, 1):
                ox = x + s * hx * 0.6
                mb.ring_strip(_oct(ox, y, hx * 0.4, hy, 0.3, 0), _oct(ox, y, hx * 0.4, hy, 0.3, hgt), wm)
                mb.cap(_oct(ox, y, hx * 0.4, hy, 0.3, hgt), ROOF)
            bz = hgt * R.uniform(0.55, 0.75)
            mb.box((x - hx * 0.25, y - 5, bz), (x + hx * 0.25, y + 5, bz + 8), wm)
            mb.box((x - hx * 0.25, y - 5.1, bz + 8), (x + hx * 0.25, y + 5.1, bz + 8.6), cm)
            top = hgt
        else:
            z, sx, sy = 0.0, hx * 1.3, hy * 1.3
            steps = R.randint(4, 7)
            for s in range(steps):
                z1 = z + hgt / steps
                mb.ring_strip(_oct(x, y, sx, sy, 0.1, z), _oct(x, y, sx, sy, 0.1, z1), wm)
                mb.cap(_oct(x, y, sx, sy, 0.1, z1), ROOF)
                mb.ring_strip(_oct(x, y, sx + 0.2, sy + 0.2, 0.1, z1 - 0.8), _oct(x, y, sx + 0.2, sy + 0.2, 0.1, z1 - 0.4), cm)
                z = z1
                sx *= 0.84
                sy *= 0.84
            top = hgt
        if R.random() < 0.6:
            mh = R.uniform(15, 50)
            mb.box((x - 0.5, y - 0.5, top), (x + 0.5, y + 0.5, top + mh), ROOF)
            mb.box((x - 0.8, y - 0.8, top + mh), (x + 0.8, y + 0.8, top + mh + 1.2), BEACON)
    print(f'[skyline] {len(placed)} towers')
    return mb.to_object('Skyline', mats, col)
