"""THE HELIX: a twisting glass tower across the canyon from the Hive.

Design: 76 superelliptic floor plates, each rotated 1.1 degrees from the one
below (a quarter turn over 300 m). Every slab edge carries an LED line whose
colour drifts from cyan to violet with height, so the twist reads as
spiralling bands of light. Vertical aluminium fins follow the rotation,
the top floors open into a lantern crown around a needle spire, and the
tower lands in a glazed lobby drum."""

import math

from . import materials as M
from .util import MeshBuilder, collection, offset_polygon, superellipse

CX, CY = 76.0, 80.0
A, B, N = 30.0, 12.5, 2.6
FLOORS = 76
FH = 4.0
BASE = 18.0
TWIST = math.radians(1.2)


def strip_material():
    g = M.G('HelixLED')
    obj = g.coords('Object')
    sep = g.n('ShaderNodeSeparateXYZ')
    g.link(obj, sep.inputs[0])
    t = g.math('DIVIDE', sep.outputs['Z'], BASE + FLOORS * FH)
    col = g.ramp(t, [(0.0, (0.05, 0.85, 1.0)), (0.45, (0.2, 0.35, 1.0)), (0.8, (0.62, 0.18, 1.0)), (1.0, (1.0, 0.15, 0.6))])
    e = g.n('ShaderNodeEmission', Strength=20.0)
    g.link(col, e.inputs['Color'])
    return g.done(e.outputs[0])


def slat_material():
    g = M.G('HelixLobbyCore')
    uv = g.coords('UV')
    sep = g.n('ShaderNodeSeparateXYZ')
    g.link(uv, sep.inputs[0])
    slat = g.math('GREATER_THAN', g.math('FRACT', g.math('MULTIPLY', sep.outputs['X'], 4.0)), 0.3)
    wood = g.mix(slat, (0.05, 0.025, 0.012), (0.42, 0.2, 0.08))
    glow = g.mix(slat, (0.0, 0.0, 0.0), (1.0, 0.6, 0.3))
    grad = g.ramp(g.math('DIVIDE', sep.outputs['Y'], BASE), [(0.0, (1.4, 1.4, 1.4)), (0.6, (0.6, 0.6, 0.6)), (1.0, (1.0, 1.0, 1.0))])
    glow = g.mix(1.0, glow, grad, 'MULTIPLY')
    b = g.bsdf(**{'Base Color': wood, 'Roughness': 0.4, 'Emission Color': glow, 'Emission Strength': 1.6})
    return g.done(b.outputs[0])


def build():
    col = collection('Helix')
    glass = M.window_wall('HelixGlass', cell_w=1.55, floor_h=FH, lit=0.42, strength=3.5, mullion=0.09, office=True,
                          warm=(1.0, 0.72, 0.45), cool=(0.72, 0.86, 1.0), accent=(0.3, 0.9, 1.0),
                          glass=(0.01, 0.014, 0.022))
    slab = M.concrete('HelixSlab', tone=0.2, tint=(0.95, 0.97, 1.0), panel=(4, 0.5), streaks=0.1)
    fin = M.metal('HelixFin', base=(0.55, 0.57, 0.6), rough=0.25)
    led = strip_material()
    lobby = slat_material()
    spire_m = M.metal('HelixSpire', base=(0.6, 0.62, 0.66), rough=0.2)
    beacon = M.emission('HelixBeacon', (1.0, 0.05, 0.03), 80.0)
    lobby_glass = M.clear_glass('HelixLobbyGlass', tint=(0.9, 0.95, 1.0), rough=0.02)
    ceil = M.emission('HelixLobbyCeil', (1.0, 0.85, 0.65), 6.0)
    mats = [glass, slab, fin, led, lobby, spire_m, beacon, lobby_glass, ceil]
    mb = MeshBuilder()

    # lobby drum: clear glazing on mullions around a warm timber-slatted core
    drum = superellipse(A + 3, B + 3, N, 72, 0.0, CX, CY)
    mb.ring_strip([(x, y, 0.0) for x, y in drum], [(x, y, BASE - 1.0) for x, y in drum], 7)
    for k in range(0, 72, 2):
        x, y = drum[k]
        mb.box((x - 0.12, y - 0.12, 0.0), (x + 0.12, y + 0.12, BASE - 1.0), 2)
    inner = superellipse(A - 4, B - 4, N, 72, 0.0, CX, CY)
    mb.ring_strip([(x, y, 0.0) for x, y in inner], [(x, y, BASE - 1.2) for x, y in inner], 4)
    mb.cap([(x, y, 0.03) for x, y in drum], 1)
    ring_out = superellipse(A + 1.5, B + 1.5, N, 72, 0.0, CX, CY)
    ring_in = superellipse(A - 0.5, B - 0.5, N, 72, 0.0, CX, CY)
    mb.add([(x, y, BASE - 1.25) for x, y in ring_out] + [(x, y, BASE - 1.25) for x, y in ring_in],
           [(i, 72 + i, 72 + (i + 1) % 72, (i + 1) % 72) for i in range(72)], 8)
    canopy = offset_polygon(superellipse(A + 3, B + 3, N, 72, 0.0, CX, CY), 6.0)
    mb.extrude_polygon(canopy, BASE - 1.0, BASE, 1, 1)
    mb.box((CX - 1, CY - 1, BASE), (CX + 1, CY + 1, BASE + 0.1), 1)

    for i in range(FLOORS + 4):
        z = BASE + i * FH
        rot = i * TWIST
        plate = superellipse(A, B, N, 96, rot, CX, CY)
        edge = offset_polygon(plate, 1.1)
        crown = i >= FLOORS
        # slab with its LED line
        mb.extrude_polygon(edge, z, z + 0.55, 1, 1)
        band0 = offset_polygon(plate, 1.12)
        mb.ring_strip([(x, y, z + 0.16) for x, y in band0], [(x, y, z + 0.36) for x, y in band0], 3)
        if not crown:
            mb.ring_strip([(x, y, z + 0.55) for x, y in plate], [(x, y, z + FH) for x, y in plate], 0)
        # vertical fins following the floor's rotation
        nf = 96
        for k in range(0, nf, 2):
            px, py = plate[k]
            ex, ey = edge[k]
            dx, dy = ex - px, ey - py
            L = math.hypot(dx, dy)
            ux, uy = dx / L, dy / L
            tx, ty = -uy, ux
            o0 = 0.15
            o1 = 0.95 if not crown else 1.0
            w = 0.09
            quad_pts = [(px + ux * o0 + tx * w, py + uy * o0 + ty * w), (px + ux * o1 + tx * w, py + uy * o1 + ty * w),
                        (px + ux * o1 - tx * w, py + uy * o1 - ty * w), (px + ux * o0 - tx * w, py + uy * o0 - ty * w)]
            mb.extrude_polygon(list(reversed(quad_pts)), z + 0.55, z + FH, 2, 2)
    top = BASE + (FLOORS + 4) * FH
    mb.extrude_polygon(superellipse(A * 0.6, B * 0.6, N, 48, (FLOORS + 4) * TWIST, CX, CY), top, top + 3.0, 1, 1)
    # needle spire
    ring_pts = lambda r, z: [(CX + r * math.cos(2 * math.pi * k / 12), CY + r * math.sin(2 * math.pi * k / 12), z) for k in range(12)]
    mb.ring_strip(ring_pts(2.2, top + 3.0), ring_pts(0.25, top + 62.0), 5)
    mb.box((CX - 0.6, CY - 0.6, top + 40), (CX + 0.6, CY + 0.6, top + 41.2), 6)
    mb.box((CX - 0.5, CY - 0.5, top + 62), (CX + 0.5, CY + 0.5, top + 63.0), 6)
    return mb.to_object('HelixTower', mats, col)
