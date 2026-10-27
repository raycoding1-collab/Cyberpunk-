"""Bridges across the canyon: a maglev viaduct (with a train crossing) and a
glass sky-tube linking a Hive pylon to the Monolith."""

import math

from . import materials as M
from .util import MeshBuilder, collection, superellipse

VIA_Y = 146.0
VIA_Z = 38.0
TUBE_Y = 202.0
TUBE_Z = 118.0


def _sweep_x(mb, profile_fn, x0, x1, steps, mat, caps=True):
    """Loft a YZ profile along +x. profile_fn(t) -> list of (y, z) (CCW seen from +x)."""
    rings = []
    for i in range(steps + 1):
        t = i / steps
        x = x0 + (x1 - x0) * t
        rings.append([(x, y, z) for y, z in profile_fn(t)])
    for i in range(steps):
        mb.ring_strip(rings[i], rings[i + 1], mat)
    if caps:
        mb.cap(rings[0], mat, flip=True)
        mb.cap(rings[-1], mat)


def viaduct(col):
    conc = M.concrete('ViaductConcrete', tone=0.17, panel=(6.0, 1.0), streaks=0.35)
    under = M.emission('ViaductUnder', (0.1, 0.8, 1.0), 24.0)
    edge = M.emission('ViaductEdge', (1.0, 0.9, 0.8), 30.0)
    steel = M.metal('ViaductSteel', base=(0.06, 0.06, 0.07), rough=0.3)
    mats = [conc, under, edge, steel]
    mb = MeshBuilder()
    x0, x1 = -70.0, 210.0
    # box girder with a tapered keel
    prof = [(-4.2, 0.0), (-4.4, 2.8), (4.4, 2.8), (4.2, 0.0), (2.2, -1.6), (-2.2, -1.6)]
    prof = [(VIA_Y + y, VIA_Z - 2.8 + z) for y, z in prof]
    # make CCW (seen from +x: y right, z up)
    prof = list(reversed(prof))
    _sweep_x(mb, lambda t: prof, x0, x1, 1, 0)
    # light line in the keel and along both parapets
    mb.box((x0, VIA_Y - 0.25, VIA_Z - 4.45), (x1, VIA_Y + 0.25, VIA_Z - 4.38), 1)
    for s in (-1, 1):
        mb.box((x0, VIA_Y + s * 4.42 - 0.04, VIA_Z - 0.6), (x1, VIA_Y + s * 4.42 + 0.04, VIA_Z - 0.45), 2)
        mb.box((x0, VIA_Y + s * 4.1 - 0.15, VIA_Z), (x1, VIA_Y + s * 4.1 + 0.15, VIA_Z + 1.2), 0)
    # guideway rail
    mb.box((x0, VIA_Y - 1.6, VIA_Z), (x1, VIA_Y + 1.6, VIA_Z + 0.6), 3)
    # sculpted Y-piers outside the canyon walls
    for px in (-46.0, 46.0, 120.0, 190.0):
        for s in (-1, 1):
            mb.beam((px, VIA_Y, 0.0), (px, VIA_Y + s * 3.0, VIA_Z - 4.4), 2.2, 2.6, 0)
        mb.beam((px, VIA_Y, -1.0), (px, VIA_Y, 18.0), 3.4, 3.4, 0)
    mb.to_object('Viaduct', mats, col)


def train(col, x_head=62.0, cars=4):
    body = M.paint('TrainBody', (0.62, 0.64, 0.68), rough=0.22, metallic=0.6)
    win = M.window_wall('TrainWindows', cell_w=1.8, floor_h=1.2, lit=0.95, strength=6.0, mullion=0.12, office=False,
                        warm=(0.9, 0.95, 1.0), cool=(0.85, 0.92, 1.0), accent=(1.0, 0.9, 0.85))
    stripe = M.emission('TrainStripe', (1.0, 0.1, 0.45), 18.0)
    head = M.emission('TrainHead', (1.0, 0.95, 0.9), 60.0)
    glow = M.emission('TrainGlow', (0.2, 0.7, 1.0), 10.0)
    mats = [body, win, stripe, head, glow]
    mb = MeshBuilder()
    L, gap = 25.0, 1.2
    zb = VIA_Z + 0.9
    for c in range(cars):
        xa = x_head - c * (L + gap) - L
        xb = xa + L
        nose_front = c == 0
        nose_back = c == cars - 1

        def prof(t, xa=xa, xb=xb, nf=nose_front, nb=nose_back):
            k = 1.0
            if nf and t > 0.78:
                k = math.sqrt(max(0.0, 1 - ((t - 0.78) / 0.22) ** 2)) * 0.95 + 0.05
            if nb and t < 0.12:
                k = math.sqrt(max(0.0, 1 - ((0.12 - t) / 0.12) ** 2)) * 0.9 + 0.1
            pts = superellipse(1.7, 1.75, 3.2, 28)
            return [(VIA_Y + y * k, zb + 1.75 + z * (0.35 + 0.65 * k) - (1 - k) * 0.6) for y, z in pts]
        _sweep_x(mb, prof, xa, xb, 18, 0)
        # window band, livery stripe, glow skirt
        for s in (-1, 1):
            wy = VIA_Y + s * 1.71
            q = MeshBuilder()
            q.add([(xa + 2.0, wy, zb + 2.0), (xb - 2.0, wy, zb + 2.0), (xb - 2.0, wy, zb + 2.9), (xa + 2.0, wy, zb + 2.9)],
                  [(0, 1, 2, 3) if s < 0 else (3, 2, 1, 0)], 0, [(0, 0), (L - 4, 0), (L - 4, 1.2), (0, 1.2)])
            mb.merge(q, mat_offset=1)
            mb.box((xa + 1.0, wy - 0.02 * s, zb + 1.35), (xb - 1.0, wy + 0.02 * s, zb + 1.5), 2)
        mb.box((xa + 1.0, VIA_Y - 1.4, zb - 0.05), (xb - 1.0, VIA_Y + 1.4, zb + 0.02), 4)
    # headlights
    for s in (-1, 1):
        mb.box((x_head - 0.8, VIA_Y + s * 0.7 - 0.25, zb + 1.5), (x_head - 0.5, VIA_Y + s * 0.7 + 0.25, zb + 1.75), 3)
    mb.to_object('Train', mats, col, smooth=True)


def sky_tube(col):
    glass = M.clear_glass('TubeGlass', tint=(0.85, 0.95, 1.0), rough=0.04)
    rib = M.metal('TubeRib', base=(0.08, 0.08, 0.09), rough=0.3)
    floor = M.concrete('TubeFloor', tone=0.1)
    light = M.emission('TubeLight', (1.0, 0.85, 0.7), 14.0)
    ring = M.emission('TubeRing', (1.0, 0.12, 0.5), 22.0)
    mats = [glass, rib, floor, light, ring]
    mb = MeshBuilder()
    x0, x1 = -19.0, 18.0
    R = 4.2

    def circ(t):
        return [(TUBE_Y + R * math.cos(a), TUBE_Z + R * math.sin(a)) for a in [2 * math.pi * k / 36 for k in range(36)]]
    _sweep_x(mb, circ, x0, x1, 1, 0, caps=False)
    x = x0 + 0.5
    while x < x1:
        pts = circ(0)
        for k in range(36):
            y0_, z0_ = pts[k]
            y1_, z1_ = pts[(k + 1) % 36]
            mb.beam((x, y0_, z0_), (x, y1_, z1_), 0.35, 0.3, 1, up=(1, 0, 0))
        x += 3.0
    mb.box((x0, TUBE_Y - 3.4, TUBE_Z - 2.6), (x1, TUBE_Y + 3.4, TUBE_Z - 2.2), 2)
    mb.box((x0, TUBE_Y - 0.25, TUBE_Z + 3.6), (x1, TUBE_Y + 0.25, TUBE_Z + 3.7), 3)
    for xx in (x0 + 0.2, x1 - 0.2):
        pts = circ(0)
        for k in range(36):
            y0_, z0_ = pts[k]
            y1_, z1_ = pts[(k + 1) % 36]
            mb.beam((xx, y0_, z0_), (xx, y1_, z1_), 0.5, 0.25, 4, up=(1, 0, 0))
    # under-truss
    mb.beam((x0, TUBE_Y, TUBE_Z - 4.4), (x1, TUBE_Y, TUBE_Z - 4.4), 1.0, 1.0, 1)
    k = 0
    x = x0
    while x < x1 - 0.1:
        nx = min(x1, x + 3.0)
        a = (x, TUBE_Y, TUBE_Z - 4.4) if k % 2 == 0 else (x, TUBE_Y, TUBE_Z - 2.6)
        b = (nx, TUBE_Y, TUBE_Z - 2.6) if k % 2 == 0 else (nx, TUBE_Y, TUBE_Z - 4.4)
        mb.beam(a, b, 0.3, 0.3, 1)
        x = nx
        k += 1
    mb.to_object('SkyTube', mats, col)


def build():
    col = collection('Bridges')
    viaduct(col)
    train(col)
    sky_tube(col)
