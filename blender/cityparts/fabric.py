"""City fabric: the dense mid-rise carpet around the hero buildings, with
sodium and LED street veins. Kept deliberately lower than the landmarks so
they read as the skyline; detailed enough (chamfers, setbacks, lit crowns,
rooftop plant) to hold up in aerial views through the haze."""

import math

from . import materials as M
from .util import MeshBuilder, collection, rng

GRID = 64.0
STREET = 14.0


def _blocked(x, y, r):
    if abs(x) < 34 + r and -460 < y < 620:
        return True
    if -205 - r < x < 170 + r and -220 < y < 380:
        return True
    if math.hypot(x, y - 700) < 200 + r:
        return True
    return False


def _chamfer_box(mb, x0, y0, x1, y1, z0, z1, c, mat_side, mat_top):
    pts = [(x1, y0 + c), (x1, y1 - c), (x1 - c, y1), (x0 + c, y1), (x0, y1 - c), (x0, y0 + c), (x0 + c, y0), (x1 - c, y0)]
    mb.ring_strip([(x, y, z0) for x, y in pts], [(x, y, z1) for x, y in pts], mat_side)
    mb.cap([(x, y, z1) for x, y in pts], mat_top)


def build(seed=23):
    R = rng(seed)
    col = collection('Fabric')
    walls = [
        M.window_wall('FabA', cell_w=2.4, floor_h=3.2, lit=0.5, strength=2.4, office=False, mullion=0.3, zone=3),
        M.window_wall('FabB', cell_w=3.0, floor_h=3.0, lit=0.42, strength=2.2, office=False, mullion=0.5, zone=2,
                      warm=(1.0, 0.5, 0.22), cool=(0.85, 0.9, 1.0)),
        M.window_wall('FabC', cell_w=1.8, floor_h=3.8, lit=0.35, strength=2.8, office=True, zone=5),
    ]
    roof = M.concrete('FabRoof', tone=0.05, panel=(6, 6), streaks=0.1)
    crown_cols = [(1.0, 0.1, 0.45), (0.1, 0.8, 1.0), (1.0, 0.55, 0.15), (0.6, 0.25, 1.0), (0.95, 0.95, 1.0)]
    crowns = [M.emission(f'FabCrown{i}', c, 10.0) for i, c in enumerate(crown_cols)]
    sodium = M.emission('StreetSodium', (1.0, 0.5, 0.15), 60.0)
    led = M.emission('StreetLED', (0.75, 0.88, 1.0), 50.0)
    plant = M.metal('RoofPlant', base=(0.05, 0.05, 0.055), rough=0.5)
    mats = walls + [roof] + crowns + [sodium, led, plant]
    ROOF = len(walls)
    C0 = ROOF + 1
    SOD, LED, PLANT = C0 + len(crowns), C0 + len(crowns) + 1, C0 + len(crowns) + 2
    mb = MeshBuilder()
    n = 0
    for gx in range(-12, 13):
        for gy in range(-13, 30):
            cx, cy = gx * GRID, gy * GRID
            d = math.hypot(cx, cy - 300)
            if d > 1250 or _blocked(cx, cy, GRID * 0.5):
                continue
            half = (GRID - STREET) / 2
            # subdivide the block into 1-4 buildings
            parts = [(cx - half, cy - half, cx + half, cy + half)]
            if R.random() < 0.65:
                sx = cx + R.uniform(-0.3, 0.3) * half
                parts = [(cx - half, cy - half, sx - 1.5, cy + half), (sx + 1.5, cy - half, cx + half, cy + half)]
                if R.random() < 0.5:
                    a = parts.pop(R.randrange(2))
                    sy = (a[1] + a[3]) / 2 + R.uniform(-0.25, 0.25) * (a[3] - a[1])
                    parts += [(a[0], a[1], a[2], sy - 1.5), (a[0], sy + 1.5, a[2], a[3])]
            for (x0, y0, x1, y1) in parts:
                if x1 - x0 < 8 or y1 - y0 < 8:
                    continue
                hgt = R.uniform(18, 46) * (1.0 + 0.8 * math.exp(-math.hypot(cx, cy - 700) / 500)) * (1.6 if R.random() < 0.1 else 1.0)
                wm = R.randrange(len(walls))
                c = min(x1 - x0, y1 - y0) * R.uniform(0.0, 0.18)
                z = 0.0
                tiers = R.choice([1, 1, 2, 2, 3])
                bx0, by0, bx1, by1 = x0, y0, x1, y1
                for t in range(tiers):
                    z1 = hgt if t == tiers - 1 else z + (hgt - z) * R.uniform(0.5, 0.75)
                    _chamfer_box(mb, bx0, by0, bx1, by1, z, z1, c, wm, ROOF)
                    if R.random() < 0.35:
                        cm = C0 + R.randrange(len(crowns))
                        _chamfer_box(mb, bx0 - 0.15, by0 - 0.15, bx1 + 0.15, by1 + 0.15, z1 - 1.1, z1 - 0.7, c, cm, cm)
                    ins = min(bx1 - bx0, by1 - by0) * R.uniform(0.08, 0.18)
                    bx0, by0, bx1, by1 = bx0 + ins, by0 + ins, bx1 - ins, by1 - ins
                    z = z1
                # rooftop plant: a few mechanical boxes and a water tank
                for _ in range(R.randint(1, 3)):
                    px, py = R.uniform(bx0 + 2, max(bx0 + 2.1, bx1 - 6)), R.uniform(by0 + 2, max(by0 + 2.1, by1 - 6))
                    mb.box((px, py, z), (px + R.uniform(2, 5), py + R.uniform(2, 5), z + R.uniform(1.5, 3.5)), PLANT)
                n += 1
    # street lamps: dotted lines of sodium / LED heads along the grid
    def lamp_run(p0, p1, mat, spacing=22.0):
        L = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        k = int(L // spacing)
        for i in range(k):
            t = (i + 0.5) / k
            x = p0[0] + (p1[0] - p0[0]) * t
            y = p0[1] + (p1[1] - p0[1]) * t
            if _blocked(x, y, 4.0) or math.hypot(x, y - 300) > 1300:
                continue
            mb.box((x - 0.35, y - 0.35, 7.6), (x + 0.35, y + 0.35, 7.8), mat)
    for gx in range(-12, 13):
        x = gx * GRID + GRID / 2
        mat = SOD if gx % 3 else LED
        for sgn in (-1, 1):
            lamp_run((x + sgn * 5.5, -900), (x + sgn * 5.5, 1600), mat)
    for gy in range(-14, 26):
        y = gy * GRID + GRID / 2
        mat = SOD if gy % 4 else LED
        for sgn in (-1, 1):
            lamp_run((-850, y + sgn * 5.5), (850, y + sgn * 5.5), mat)
    print(f'[fabric] {n} buildings')
    return mb.to_object('CityFabric', mats, col)
