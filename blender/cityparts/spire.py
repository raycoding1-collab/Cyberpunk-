"""THE SPIRE: the Kagemori arcology closing the end of the canyon.

Design: a chamfered-octagon tower tapering from 84 m to 34 m across over
740 m. A golden glass core is wrapped by a staggered bronze diagrid whose
nodes carry small amber lamps, so the lattice reads as a net of light. Two
sky lobbies are carved out of the core (gardens glowing behind the frame).
Four blades rise from the faces and lean together around a beacon, ringed
by a floating halo; a needle carries the aircraft lights to 1 km. At its
foot a monumental portal opens onto a plaza with a black reflecting pool."""

import math

import bpy
from mathutils import Vector

from . import materials as M
from .util import MeshBuilder, collection

CX, CY = 0.0, 700.0
H = 740.0
GOLD = (1.0, 0.52, 0.12)


def half(z):
    return 42.0 * (1.0 - 0.6 * (max(z, 0.0) / H) ** 1.25)


def octagon(h, z, inset=0.0, cx=CX, cy=CY):
    h = h - inset
    c = h * 0.36
    pts = [(h, -(h - c)), (h, h - c), (h - c, h), (-(h - c), h), (-h, h - c), (-h, -(h - c)), (-(h - c), -h), (h - c, -h)]
    return [(cx + x, cy + y, z) for x, y in pts]


def garden_material():
    g = M.G('SkyGarden')
    obj = g.coords('Object')
    n = g.noise(obj, 0.35, 6, 0.65)
    col = g.ramp(n, [(0.3, (0.05, 0.25, 0.08)), (0.55, (0.35, 0.6, 0.15)), (0.75, (1.0, 0.7, 0.3))])
    e = g.n('ShaderNodeEmission', Strength=3.5)
    g.link(col, e.inputs['Color'])
    return g.done(e.outputs[0])


def build():
    col = collection('Spire')
    core = M.window_wall('SpireGlass', cell_w=1.8, floor_h=4.5, lit=0.78, strength=4.2, mullion=0.1, office=True,
                         warm=(1.0, 0.48, 0.12), cool=(1.0, 0.64, 0.28), accent=(1.0, 0.36, 0.08), glass=(0.02, 0.012, 0.006),
                         spandrel_color=(0.06, 0.035, 0.015))
    bronze = M.metal('SpireBronze', base=(0.16, 0.1, 0.05), rough=0.38)
    dark = M.metal('SpireDark', base=(0.03, 0.03, 0.035), rough=0.3)
    node_lamp = M.emission('SpireNode', GOLD, 45.0)
    edge = M.emission('SpireEdge', GOLD, 40.0)
    garden = garden_material()
    atrium = M.window_wall('SpireAtrium', cell_w=3.0, floor_h=36.0, lit=1.0, strength=2.0, mullion=0.06, office=False,
                           warm=(1.0, 0.8, 0.55), cool=(1.0, 0.8, 0.55), accent=(1.0, 0.8, 0.55))
    stone = M.concrete('SpireStone', tone=0.09, tint=(1.0, 0.95, 0.88), panel=(3.0, 1.5), streaks=0.25)
    portal = M.emission('SpirePortal', (1.0, 0.72, 0.4), 9.0)
    water = M.paint('ReflectingPool', (0.003, 0.003, 0.004), rough=0.0)
    beacon = M.emission('SpireBeacon', (1.0, 0.04, 0.02), 90.0)
    halo = M.emission('SpireHalo', GOLD, 30.0)
    hot = M.emission('SpireCrownCore', (1.0, 0.75, 0.4), 120.0)
    mats = [core, bronze, dark, node_lamp, edge, garden, atrium, stone, portal, water, beacon, halo, hot]
    mb = MeshBuilder()

    # --- glass core with two carved sky lobbies ---
    lobbies = [(252.0, 288.0), (504.0, 540.0)]
    z = 30.0
    step = 18.0
    while z < H - 0.1:
        z1 = min(H, z + step)
        in_lobby = any(a <= z < b for a, b in lobbies)
        if in_lobby:
            mb.ring_strip(octagon(half(z), z, 8.0), octagon(half(z1), z1, 8.0), 6)
        else:
            mb.ring_strip(octagon(half(z), z), octagon(half(z1), z1), 0)
        z = z1
    for a, b in lobbies:
        # floor & ceiling slabs of the lobby, gardens inside
        for zz in (a, b - 1.5):
            mb.cap(octagon(half(zz), zz + 1.5), 2)
            mb.cap(octagon(half(zz), zz), 2, flip=True)
            mb.ring_strip(octagon(half(zz), zz), octagon(half(zz), zz + 1.5), 2)
        mb.cap(octagon(half(a) - 10.0, a + 1.6), 5)
        for i in range(10):
            ang = i * 0.63
            r = half(a) - 12.0
            px, py = CX + math.cos(ang) * r * 0.6, CY + math.sin(ang) * r * 0.6
            mb.box((px - 1.5, py - 1.5, a + 1.5), (px + 1.5, py + 1.5, a + 4.0 + (i % 3) * 3), 5)
    mb.cap(octagon(half(H), H), 2)

    # --- staggered diagrid exoskeleton ---
    levels = int(H // 18)
    nodes = []
    for L in range(levels + 1):
        zl = 30.0 + L * 18.0
        if zl > H:
            break
        ring = octagon(half(zl) + 3.2, zl)
        if L % 2 == 1:
            ring = [tuple((Vector(ring[i]) + Vector(ring[(i + 1) % 8])) / 2) for i in range(8)]
        nodes.append(ring)
    for L in range(len(nodes) - 1):
        a, b = nodes[L], nodes[L + 1]
        for i in range(8):
            if L % 2 == 0:
                mb.beam(a[i], b[i], 1.3, 1.7, 1)
                mb.beam(a[i], b[(i - 1) % 8], 1.3, 1.7, 1)
            else:
                mb.beam(a[i], b[i], 1.3, 1.7, 1)
                mb.beam(a[i], b[(i + 1) % 8], 1.3, 1.7, 1)
        if L % 2 == 0:
            for i in range(8):
                mb.beam(a[i], a[(i + 1) % 8], 0.9, 1.1, 2)
        for p in a:
            mb.box_c(p, (1.0, 1.0, 1.0), 3)
    for p in nodes[-1]:
        mb.box_c(p, (1.0, 1.0, 1.0), 3)
    # vertical edge lines up the eight chamfer corners of the core
    z = 30.0
    while z < H - 0.1:
        z1 = min(H, z + step)
        if not any(a <= z < b for a, b in lobbies):
            r0, r1 = octagon(half(z) + 0.35, z), octagon(half(z1) + 0.35, z1)
            for i in range(0, 8, 2):
                mb.beam(r0[i], r1[i], 0.25, 0.25, 4)
        z = z1

    # --- crown: four leaning blades, halo, hot core, needle ---
    zc = H - 40.0
    for k in range(4):
        ang = k * math.pi / 2
        d = Vector((math.cos(ang), math.sin(ang), 0.0))
        t = Vector((-d.y, d.x, 0.0))
        r0 = half(zc) + 2.0
        base_o = Vector((CX, CY, zc)) + d * r0
        base_i = Vector((CX, CY, zc)) + d * (r0 - 14.0)
        tip = Vector((CX, CY, H + 150.0)) + d * 5.0
        th = 1.2
        verts = []
        for off in (-th, th):
            o = t * off
            verts += [tuple(base_i + o), tuple(base_o + o), tuple(tip + o * 0.3)]
        faces = [(0, 1, 2), (5, 4, 3), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)]
        mb.add(verts, faces, 2)
        # lit outer edge
        mb.beam(base_o + d * 0.4, tip + d * 0.4, 0.5, 0.5, 4)
    mb.box_c((CX, CY, H + 22.0), (10.0, 10.0, 10.0), 12)
    # needle
    ring_pts = lambda r, z: [(CX + r * math.cos(2 * math.pi * k / 16), CY + r * math.sin(2 * math.pi * k / 16), z) for k in range(16)]
    mb.ring_strip(ring_pts(3.4, H), ring_pts(0.3, H + 280.0), 2)
    for zb in (H + 150.0, H + 210.0, H + 278.0):
        mb.box_c((CX, CY, zb), (1.6, 1.6, 1.4), 10)
    ob_main = mb.to_object('SpireTower', mats, col)

    # halo rings (separate so they can be smooth)
    h = MeshBuilder()
    for (R, r, zz) in ((40.0, 0.9, H + 55.0), (49.0, 0.45, H + 38.0)):
        seg, sides = 160, 10
        verts, faces = [], []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            for j in range(sides):
                s = 2 * math.pi * j / sides
                rr = R + r * math.cos(s)
                verts.append((CX + rr * math.cos(a), CY + rr * math.sin(a), zz + r * math.sin(s)))
        for i in range(seg):
            for j in range(sides):
                faces.append((i * sides + j, ((i + 1) % seg) * sides + j, ((i + 1) % seg) * sides + (j + 1) % sides, i * sides + (j + 1) % sides))
        h.add(verts, faces, 0)
    h.to_object('SpireHalo', [halo], col, smooth=True)

    # --- podium, portal and plaza ---
    p = MeshBuilder()
    pod_b, pod_t = octagon(62.0, 0.0), octagon(62.0, 30.0)
    p.ring_strip(pod_b, pod_t, 6)                      # glazed golden lobby levels
    p.cap(octagon(62.0, 30.0), 0)
    p.ring_strip(octagon(62.6, 28.4), octagon(62.6, 29.0), 3)
    p.ring_strip(octagon(63.0, 29.0), octagon(63.0, 31.5), 0)
    # bronze fins around the podium
    for i in range(8):
        a, b = Vector(pod_b[i]), Vector(pod_b[(i + 1) % 8])
        n = Vector((b.y - a.y, -(b.x - a.x), 0)).normalized()
        L = (b - a).length
        k = int(L // 4.2)
        for j in range(1, k):
            q = a + (b - a) * (j / k)
            p.beam(q + n * 0.6 - Vector((0, 0, 0)), q + n * 0.6 + Vector((0, 0, 28.4)), 0.5, 1.2, 2, up=(n.x, n.y, 0))
    # monumental portal: a projecting stone frame around a deep golden lobby
    py = CY - 62.0
    W2, Hp, D = 17.0, 27.0, 14.0
    p.box((CX - 25.0, py - 7.0, 0.0), (CX - W2, py + 1.0, 35.0), 0)
    p.box((CX + W2, py - 7.0, 0.0), (CX + 25.0, py + 1.0, 35.0), 0)
    p.box((CX - W2, py - 7.0, Hp), (CX + W2, py + 1.0, 35.0), 0)
    # lobby volume behind the opening
    p.box((CX - W2, py - 7.0 + 0.01, -0.02), (CX + W2, py + D, 0.06), 4, faces=(0, 0, 0, 0, 0, 1))
    p.box((CX - W2, py - 7.0, Hp - 0.01), (CX + W2, py + D, Hp), 7, faces=(0, 0, 0, 0, 1, 0))
    p.box((CX - W2 - 0.3, py - 7.0, 0.0), (CX - W2, py + D, Hp), 0, faces=(0, 1, 0, 0, 0, 0))
    p.box((CX + W2, py - 7.0, 0.0), (CX + W2 + 0.3, py + D, Hp), 0, faces=(1, 0, 0, 0, 0, 0))
    bw = MeshBuilder()
    bw.add([(CX - W2, py + D, 0.0), (CX + W2, py + D, 0.0), (CX + W2, py + D, Hp), (CX - W2, py + D, Hp)], [(0, 1, 2, 3)], 0,
           [(0, 0), (2 * W2, 0), (2 * W2, Hp), (0, Hp)])
    p.merge(bw, mat_offset=8)
    # suspended ring sculpture in the lobby
    seg, sides, R0, r0 = 96, 10, 7.5, 0.45
    rv, rf = [], []
    for i in range(seg):
        t = 2 * math.pi * i / seg
        for j in range(sides):
            u = 2 * math.pi * j / sides
            rr = R0 + r0 * math.cos(u)
            rv.append((CX + rr * math.cos(t), py + D * 0.45 + r0 * math.sin(u), 13.5 + rr * math.sin(t)))
    for i in range(seg):
        for j in range(sides):
            rf.append((i * sides + j, ((i + 1) % seg) * sides + j, ((i + 1) % seg) * sides + (j + 1) % sides, i * sides + (j + 1) % sides))
    p.add(rv, rf, 3)
    # glazing grid across the opening
    gz = MeshBuilder()
    gz.add([(CX - W2, py - 6.0, 0.0), (CX + W2, py - 6.0, 0.0), (CX + W2, py - 6.0, Hp), (CX - W2, py - 6.0, Hp)], [(0, 1, 2, 3)], 0)
    p.merge(gz, mat_offset=9)
    for k in range(7):
        x = CX - W2 + k * (2 * W2 / 6)
        p.box((x - 0.18, py - 6.3, 0.0), (x + 0.18, py - 5.9, Hp), 2)
    for zz in (4.5, 13.5, 22.5):
        p.box((CX - W2, py - 6.3, zz - 0.15), (CX + W2, py - 5.9, zz + 0.15), 2)
    # plaza paving, steps and the reflecting pool
    p.add([(CX - 160, 560.0, 0.05), (CX + 160, 560.0, 0.05), (CX + 160, 900.0, 0.05), (CX - 160, 900.0, 0.05)], [(0, 1, 2, 3)], 4)
    p.box((CX - 36.0, 568.0, 0.05), (CX + 36.0, 618.0, 0.35), 4, faces=(1, 1, 1, 1, 0, 0))
    p.add([(CX - 35.4, 568.6, 0.28), (CX + 35.4, 568.6, 0.28), (CX + 35.4, 617.4, 0.28), (CX - 35.4, 617.4, 0.28)], [(0, 1, 2, 3)], 5)
    for i in range(6):
        p.box((CX - 40.0, py - 19.0 + i * 2.0, 0.0), (CX + 40.0, py - 7.0, 0.3 + i * 0.3), 4)
    stone_walk = M.wet_paving('PlazaPaving', tile=1.2, tone=0.06)
    pod_glass = M.window_wall('SpirePodiumGlass', cell_w=4.2, floor_h=7.5, lit=0.75, strength=1.3, mullion=0.25, office=False,
                              warm=(1.0, 0.55, 0.2), cool=(1.0, 0.72, 0.42), accent=(1.0, 0.45, 0.15), spandrel=0.15)
    lobby_ceil = M.emission('SpireLobbyCeil', (1.0, 0.72, 0.42), 3.0)
    slats = M.window_wall('SpireLobbyWall', cell_w=0.9, floor_h=Hp, lit=1.0, strength=1.6, mullion=0.35, office=False,
                          warm=(1.0, 0.55, 0.18), cool=(1.0, 0.62, 0.25), accent=(1.0, 0.5, 0.15), spandrel=0.02)
    lobby_glass = M.clear_glass('SpireLobbyGlass', tint=(1.0, 0.95, 0.88), rough=0.02)
    p.to_object('SpirePodium', [stone, portal, bronze, edge, stone_walk, water, pod_glass, lobby_ceil, slats, lobby_glass], col)

    # --- searchlights from the crown, beams cutting through the haze ---
    for k in range(4):
        ang = math.radians(25 + k * 90)
        lt = bpy.data.lights.new(f'Searchlight{k}', 'SPOT')
        lt.energy = 1.2e9
        lt.color = (1.0, 0.82, 0.6)
        lt.spot_size = math.radians(3.2)
        lt.spot_blend = 0.4
        lt.shadow_soft_size = 0.4
        ob = bpy.data.objects.new(f'Searchlight{k}', lt)
        ob.location = (CX + math.cos(ang) * 12.0, CY + math.sin(ang) * 12.0, H + 4.0)
        tgt = Vector((CX + math.cos(ang) * 900.0, CY + math.sin(ang) * 900.0, H + 2200.0))
        ob.rotation_euler = (tgt - Vector(ob.location)).to_track_quat('-Z', 'Y').to_euler()
        col.objects.link(ob)
    return ob_main
