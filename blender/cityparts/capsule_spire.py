"""THE CAPSULE SPIRE — one piece of the cyberpunk world, detailed throughout.

A freestanding residential megastructure on a rain-soaked corner. A sculpted
concrete core (four buttress lobes, a quarter twist, tapering) carries
hundreds of capsule homes plugged in three helical bands; between the bands
the core's own slit windows show. Glass lift shafts climb two valleys of the
core, tied back by bridges. A steel hexagonal exoskeleton wraps the upper
third, the crown carries holographic halos, and a holographic koi circles
the tower. At its foot a podium holds real shops behind a canopy, a glazed
restaurant level and the tower's name in 3D neon; a hover-car waits at the
curb of a wet plaza."""

import math

import bpy
from mathutils import Matrix, Vector

from . import materials as M
from . import shops, signs
from . import spire_details as D
from .freeform import TAU, Tower
from .hive import capsule_mesh
from .holo import koi_material, koi_mesh
from .util import MeshBuilder, collection, rng

H = 205.0
CORE_Z0 = 24.0
POD = 30.0


def core_tower():
    return Tower(0.0, 0.0, H - CORE_Z0,
                 profile=[(0.0, (13.0, 13.0, 2.6)), (60.0, (12.0, 12.0, 2.5)), (120.0, (10.5, 10.5, 2.4)),
                          (H - CORE_Z0, (8.0, 8.0, 2.3))],
                 twist=[(0.0, 0.0), (H - CORE_Z0, math.radians(90))],
                 lobes=(4, [(0.0, 0.42), (90.0, 0.36), (H - CORE_Z0, 0.22)], 0.0),
                 base_z=CORE_Z0)


def car_paint(name, color):
    g = M.G(name)
    obj = g.coords('Object')
    flake = g.noise(obj, 220.0, 2, 0.5)
    b = g.bsdf(**{'Base Color': color, 'Metallic': 0.75, 'Roughness': g.math('MULTIPLY_ADD', flake, 0.12, 0.18),
                  'Coat Weight': 1.0, 'Coat Roughness': 0.03})
    return g.done(b.outputs[0])


def hover_car(col, origin=(12.0, -41.5, 0.0), heading=0.0):
    """A sleek two-seat hover-car: lofted monocoque, tinted canopy, four
    thruster pods with glowing rings, light blades front and rear."""
    body = car_paint('CarPaint', (0.62, 0.03, 0.06))
    glass = M.paint('CarCanopy', (0.005, 0.006, 0.008), rough=0.04, metallic=0.2)
    dark = M.metal('CarTrim', base=(0.02, 0.02, 0.022), rough=0.35)
    head = M.emission('CarHead', (0.85, 0.92, 1.0), 40.0)
    tail = M.emission('CarTail', (1.0, 0.03, 0.05), 30.0)
    ring = M.emission('CarThruster', (0.1, 0.8, 1.0), 25.0)
    under = M.emission('CarUnder', (0.2, 0.5, 1.0), 6.0)
    mats = [body, glass, dark, head, tail, ring, under]
    mb = MeshBuilder()
    L, W, Hh = 5.4, 2.05, 1.05
    hz = 0.75   # hover height of the hull bottom

    def sec(t):
        # t: 0 = tail, 1 = nose
        k = math.sin(math.pi * min(1.0, max(0.0, 0.08 + t * 0.92))) ** 0.45
        w = W / 2 * (0.55 + 0.45 * k) * (0.9 if t > 0.85 else 1.0)
        h = Hh / 2 * (0.35 + 0.65 * k) * (1.0 - 0.35 * max(0.0, t - 0.6))
        n = 3.2
        zc = hz + Hh / 2 - 0.25 * max(0.0, t - 0.7)
        return w, h, n, zc
    rings = []
    steps = 28
    for i in range(steps + 1):
        t = i / steps
        w, h, n, zc = sec(t)
        x = -L / 2 + L * t
        pts = []
        for j in range(32):
            a = TAU * j / 32
            c, s = math.cos(a), math.sin(a)
            y = w * math.copysign(abs(c) ** (2 / n), c)
            z = h * math.copysign(abs(s) ** (2 / n), s) * (0.75 if s < 0 else 1.0)
            pts.append((x, y, zc + z))
        rings.append(pts)
    for i in range(steps):
        mb.ring_strip(rings[i], rings[i + 1], 0)
    mb.cap(rings[0], 0, flip=True)
    mb.cap(rings[-1], 0)
    # canopy: a teardrop of tinted glass set into the body
    cr = []
    for i in range(15):
        t = i / 14
        x = -0.9 + 2.6 * t
        k = math.sin(math.pi * t) ** 0.7
        pts = []
        for j in range(17):
            a = math.pi * j / 16
            pts.append((x, math.cos(a) * 0.78 * k, hz + Hh * 0.82 + math.sin(a) * 0.48 * k))
        cr.append(pts)
    for i in range(14):
        for j in range(16):
            a, b, c, d = cr[i][j], cr[i][j + 1], cr[i + 1][j + 1], cr[i + 1][j]
            mb.add([a, b, c, d], [(0, 3, 2, 1)], 1)
    # thruster pods with glowing rings and underglow
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = sx * L * 0.32, sy * (W / 2 + 0.22)
            pod = [(cx + 0.42 * math.cos(TAU * k / 20), cy + 0.42 * math.sin(TAU * k / 20)) for k in range(20)]
            mb.extrude_polygon(pod, hz - 0.05, hz + 0.32, 2, 2)
            rr = [(cx + 0.36 * math.cos(TAU * k / 20), cy + 0.36 * math.sin(TAU * k / 20)) for k in range(20)]
            mb.extrude_polygon(rr, hz - 0.09, hz - 0.05, 5, 5)
            mb.beam((cx, cy - sy * 0.15, hz + 0.15), (cx * 0.7, cy - sy * 0.55, hz + 0.3), 0.18, 0.12, 2)
    mb.box((-L * 0.3, -0.6, hz - 0.02), (L * 0.3, 0.6, hz), 6, faces=(0, 0, 0, 0, 1, 0))
    # light blades
    mb.box((L / 2 - 0.55, -0.85, hz + 0.42), (L / 2 - 0.35, 0.85, hz + 0.5), 3)
    mb.box((-L / 2 - 0.02, -0.9, hz + 0.55), (-L / 2 + 0.1, 0.9, hz + 0.62), 4)
    me_ob = mb.to_object('HoverCar', mats, col, smooth=False)
    me_ob.matrix_world = Matrix.Translation(origin) @ Matrix.Rotation(heading, 4, 'Z')
    return me_ob


def build(seed=31):
    R = rng(seed)
    col = collection('CapsuleSpire')
    caps_col = collection('SpireCapsules', col)
    T = core_tower()

    conc = M.concrete('CoreConcrete', tone=0.15, tint=(1.0, 0.97, 0.93), panel=(2.4, 1.2), streaks=0.5)
    core_rooms = M.window_wall('CoreSlits', cell_w=1.1, floor_h=3.3, lit=0.4, strength=2.4, mullion=0.62, office=False,
                               zone=2, spandrel=0.5, spandrel_color=(0.11, 0.105, 0.1))
    steel = M.metal('ExoSteel', base=(0.07, 0.07, 0.075), rough=0.3)
    glass = M.clear_glass('ShaftGlass', tint=(0.85, 0.95, 1.0), rough=0.03)
    cabin = M.emission('ShaftCabin', (1.0, 0.78, 0.5), 10.0)
    cyan = M.emission('SpireCyan', (0.1, 0.8, 1.0), 22.0)
    magenta = M.emission('SpireMagenta', (1.0, 0.08, 0.45), 26.0)
    warm = M.emission('SpireWarm', (1.0, 0.72, 0.45), 14.0)
    beacon = M.emission('SpireRed', (1.0, 0.04, 0.02), 70.0)
    mats = [conc, core_rooms, steel, glass, cabin, cyan, magenta, warm, beacon]
    mb = MeshBuilder()

    # --- sculpted core: room skin with concrete crown and light lines ---
    T.skin(mb, 1, 0.0, H - CORE_Z0, n_around=160, dz=2.5)
    T.cap(mb, 0, H - CORE_Z0, n_around=96)
    for zz in range(12, int(H - CORE_Z0), 24):
        T.ribbon(mb, 7, float(zz), 0.25, 0.0, 0.35)

    shaft_angles = [math.pi / 4 + 0.2, math.pi * 5 / 4 + 0.2]

    mb.to_object('SpireCore', mats, col)

    # --- exoskeleton on the upper third ---
    exo = T.hex_lattice('SpireExoskeleton', 100.0, H - CORE_Z0, cols=14, offset=8.6, thickness=0.55,
                        mats=[steel], col=col, density=1.4, subdiv=1)
    exo.data.shade_smooth()

    # --- capsules in three helical bands ---
    variants = {k: capsule_mesh(k, f'SpireCap_{k}') for k in ('porthole', 'louvre', 'balcony')}
    cap_mats = [M.capsule_shell(), steel, M.clear_glass('CapGlass2', tint=(0.92, 0.95, 1.0), rough=0.03),
                M.capsule_interior(), M.capsule_porch()]
    meshes = {}
    for k, b in variants.items():
        meshes[k] = b.to_mesh(f'SpireCapsule_{k}')
        for m in cap_mats:
            meshes[k].materials.append(m)
    n = 0
    z = CORE_Z0 + 4.0
    while z < H - 8.0:
        zl = z - CORE_Z0
        # circumference at this height
        pts = [T.point(TAU * i / 180, zl) for i in range(180)]
        circ = sum((pts[i] - pts[i - 1]).length for i in range(180))
        cnt = int(circ // 3.35)
        off = 0.5 * (int(round((z - CORE_Z0) / 3.3)) % 2)   # staggered rows: scales
        for i in range(cnt):
            th = TAU * (i + off) / cnt
            band = ((3 * th / TAU) - (z / 64.0)) % 1.0
            if band > 0.6:
                continue
            if any(abs(((th - sa + math.pi) % TAU) - math.pi) < 0.32 for sa in shaft_angles):
                continue
            if R.random() < 0.06:
                continue
            p = T.point(th, zl, -0.4)
            nrm = T.normal(th, zl)
            nh = Vector((nrm.x, nrm.y, 0.0)).normalized()
            v = R.choices(['porthole', 'louvre', 'balcony'], [0.5, 0.32, 0.18])[0]
            o = bpy.data.objects.new('Cap', meshes[v])
            jit = R.choice([0.0, 0.0, 0.4, 0.8])
            o.location = (p.x + nh.x * jit, p.y + nh.y * jit, z)
            o.rotation_euler = (0.0, math.radians(9.0), math.atan2(nh.y, nh.x) + math.radians(7.0))
            caps_col.objects.link(o)
            n += 1
        z += 3.3
    print(f'[capsule spire] {n} capsules')
    D.spiral_currents(col, T, CORE_Z0, H)
    D.spinal_shafts(col, T, shaft_angles, CORE_Z0, H)
    D.lotus_crown(col, T, CORE_Z0, H, target=(4.0, -46.0, 118.0))

    # --- architectural floodlights on the podium roof, grazing up the tower ---
    for k in range(8):
        th = TAU * k / 8 + 0.39
        base = T.point(th, 0.0, 9.0)
        lt = bpy.data.lights.new(f'Uplight{k}', 'SPOT')
        lt.energy = 1.4e6
        lt.color = (1.0, 0.78, 0.55) if k % 2 == 0 else (0.55, 0.8, 1.0)
        lt.spot_size = math.radians(22)
        lt.spot_blend = 0.6
        lt.shadow_soft_size = 0.6
        lo = bpy.data.objects.new(f'Uplight{k}', lt)
        lo.location = (base.x, base.y, CORE_Z0 + 0.6)
        aim = T.point(th, 120.0, 2.0)
        lo.rotation_euler = (aim - Vector(lo.location)).to_track_quat('-Z', 'Y').to_euler()
        col.objects.link(lo)

    # --- podium -------------------------------------------------------------
    build_podium(col)
    build_plaza(col)
    D.hover_car(col)
    koi = koi_mesh(46.0, 1.3)
    km = MeshBuilder()
    km.merge(koi, matrix=Matrix.Translation((4.0, -46.0, 118.0)) @ Matrix.Rotation(math.radians(178), 4, 'Z') @ Matrix.Rotation(math.radians(-6), 4, 'Y'))
    km.to_object('SpireKoi', [koi_material('SpireKoiHolo', 4.5)], col, smooth=True)
    build_silhouettes(col)
    return col


def build_podium(col):
    conc = M.concrete('PodiumConcrete', tone=0.12, panel=(3.0, 1.0), streaks=0.4)
    glaze = M.window_wall('PodiumRestaurant', cell_w=1.6, floor_h=5.0, lit=0.45, strength=1.5, mullion=0.1, office=False, zone=3,
                          warm=(1.0, 0.5, 0.2), cool=(1.0, 0.62, 0.32), accent=(1.0, 0.25, 0.55), spandrel=0.12, glass=(0.006, 0.006, 0.008))
    steel = M.metal('PodiumSteel', base=(0.04, 0.04, 0.045), rough=0.3)
    down = M.emission('CanopyDown', (1.0, 0.85, 0.65), 10.0)
    line = M.emission('PodiumLine', (0.1, 0.8, 1.0), 18.0)
    mats = [conc, glaze, steel, down, line]
    mb = MeshBuilder()
    P = POD
    mb.box((-P, -P + 9, 0.0), (P - 9, P, 6.0), 0, faces=(1, 0, 0, 1, 0, 0))   # mass behind the shops
    mb.box((P - 9, -P, 0.0), (P, -P + 9, 6.0), 0)                             # corner pier
    mb.box((-P, -P, 6.0), (P, P, 7.0), 0)
    # glazed restaurant level with mullion fins
    rest = MeshBuilder()
    rest.box((-P + 1.5, -P + 1.5, 7.0), (P - 1.5, P - 1.5, 12.0), 0, faces=(1, 1, 1, 1, 0, 0))
    mb.merge(rest, mat_offset=1)
    for t in range(-14, 15):
        x = t * 2.0
        mb.box((x - 0.06, -P + 1.2, 7.0), (x + 0.06, -P + 1.6, 12.0), 2)
        mb.box((P - 1.6, x - 0.06, 7.0), (P - 1.2, x + 0.06, 12.0), 2)
    # upper band: ribbed concrete crown of the podium
    mb.box((-P, -P, 12.0), (P, P, 24.0), 0)
    for zz in (12.0, 24.0):
        mb.box((-P - 0.5, -P - 0.5, zz - 0.25), (P + 0.5, P + 0.5, zz + 0.05), 0)
        mb.box((-P - 0.52, -P - 0.52, zz - 0.18), (P + 0.52, -P - 0.5, zz - 0.1), 4)
        mb.box((P + 0.5, -P - 0.52, zz - 0.18), (P + 0.52, P + 0.52, zz - 0.1), 4)
    mb.to_object('Podium', mats, col)
    D.canopy_wave(col, P)
    D.kanji_screens(col, P)

    # shops: east face built in place, south face built in the same frame and rotated
    shops.build_arcade(col, P, [(-P + 9.0, P - 1.0)], [-12.0, 0.0, 12.0], height=5.0, depth=9.0, seed=2)
    tmp = collection('PodiumSouthShops', col)
    before = set(bpy.data.objects)
    shops.build_arcade(tmp, P, [(-P + 1.0, P - 9.0)], [-12.0, 0.0, 12.0], height=5.0, depth=9.0, seed=5)
    rot = Matrix.Rotation(-math.pi / 2, 4, 'Z')
    for ob in set(bpy.data.objects) - before:
        ob.matrix_world = rot @ ob.matrix_world

    # the tower's name in 3D neon on the podium crown + a blade at the corner
    red = M.neon('PodiumNeonRed', (1.0, 0.1, 0.25), 9.0)
    white = M.neon('PodiumNeonWhite', (0.85, 0.95, 1.0), 7.0)
    panel = M.metal('BladePanel2', base=(0.02, 0.02, 0.025), rough=0.4)
    cyan = M.neon('CornerBladeNeon', (0.1, 0.85, 1.0), 14.0)
    glyph = M.emission('CornerBladeGlyph', (0.1, 0.85, 1.0), 1.8)
    b = MeshBuilder()
    x0, y0 = P + 0.6, -P - 0.6
    b.box((x0, y0 - 0.3, 26.0), (x0 + 6.5, y0 + 0.3, 50.0), 0)
    for zz in (27.0, 49.0):
        b.box((P - 0.2, y0 - 0.15, zz - 0.2), (x0, y0 + 0.15, zz + 0.2), 0)
    for f in (-1, 1):
        yy = y0 + f * 0.36
        signs.tube_outline(b, [(x0 + 0.4, yy, 26.4), (x0 + 6.1, yy, 26.4), (x0 + 6.1, yy, 49.6), (x0 + 0.4, yy, 49.6)], 0.06, 1)
    b.to_object('CornerBlade', [panel, cyan], col)
    for f in (-1, 1):
        signs.text_object('夢見', 'DelaGothicOne-Regular.ttf', 5.0, f'CornerBladeText{f}', col, glyph,
                          location=(x0 + 3.25, y0 + f * 0.38, 38.0), rotation=(math.pi / 2, 0, 0 if f < 0 else math.pi),
                          extrude=0.05, bevel=0.015, vertical=True)


def build_plaza(col):
    asphalt = M.wet_asphalt()
    paving = M.wet_paving('PlazaStone', tile=1.0, tone=0.075)
    curb = M.concrete('PlazaCurb', tone=0.13, panel=(2.0, 0.3), streaks=0.1)
    rail = M.emission('PlazaRail', (0.1, 0.75, 1.0), 9.0)
    amber = M.emission('PlazaAmber', (1.0, 0.5, 0.12), 6.0)
    mats = [asphalt, paving, curb, rail, amber]
    mb = MeshBuilder()
    mb.add([(-3000, -3000, 0), (3000, -3000, 0), (3000, 3000, 0), (-3000, 3000, 0)], [(0, 1, 2, 3)], 0)
    # plaza paving around the podium, raised one step, with a light rail at its edge
    mb.box((-70.0, -38.0, 0.0), (70.0, 90.0, 0.18), 1, faces=(1, 1, 1, 1, 0, 1))
    mb.box((-70.0, -38.2, 0.06), (70.0, -38.0, 0.1), 4)
    mb.box((-70.0, -38.0, 0.18), (70.0, -37.7, 0.2), 2)
    # street along the south side: lane rails and a zebra crossing
    y = -1000.0
    for yy in (-47.0, -55.0):
        x = -600.0
        while x < 600.0:
            mb.box((x, yy - 0.06, -0.01), (x + 5.0, yy + 0.06, 0.012), 3)
            x += 9.0
    for k in range(10):
        x = -36.0 + k * 1.4
        mb.box((x, -60.5, -0.01), (x + 0.7, -38.2, 0.01), 2)
    mb.to_object('Plaza', mats, col)
    D.koi_pond(col)
    D.steam_vents(col)
    D.flow_rails(col)


def build_silhouettes(col, seed=9):
    """Distant sculpted towers that the haze reduces to light and shape."""
    R = rng(seed)
    walls = [M.window_wall(f'FarTower{i}', cell_w=c, floor_h=f, lit=l, strength=s, office=o)
             for i, (c, f, l, s, o) in enumerate([(1.5, 4.0, 0.35, 3.0, True), (2.6, 3.3, 0.5, 2.6, False), (1.2, 4.2, 0.3, 3.4, True)])]
    crowns = [M.emission(f'FarCrown{i}', c, 16.0) for i, c in enumerate([(1.0, 0.1, 0.45), (0.1, 0.8, 1.0), (1.0, 0.55, 0.15), (0.6, 0.25, 1.0)])]
    mats = walls + crowns
    mb = MeshBuilder()
    spots = [(-260, 320), (220, 380), (-420, 650), (380, 700), (40, 900), (-150, 1200), (520, 1100), (-640, 980), (300, -380), (-380, -260)]
    for i, (x, y) in enumerate(spots):
        h = R.uniform(160, 380)
        a = R.uniform(14, 26)
        t = Tower(x, y, h, profile=[(0, (a, a * R.uniform(0.6, 1.0), R.uniform(2.2, 4.0))), (h * 0.55, (a * R.uniform(0.75, 1.1), a * 0.7, 2.6)), (h, (a * 0.45, a * 0.4, 2.2))],
                  twist=[(0, 0), (h, math.radians(R.uniform(-60, 60)))],
                  lobes=(R.choice([3, 4, 6]), [(0, R.uniform(0.0, 0.3)), (h, 0.05)], R.uniform(0, 1)) if R.random() < 0.6 else None)
        t.skin(mb, i % len(walls), 0.0, h, n_around=64, dz=6.0)
        t.cap(mb, i % len(walls), h, n_around=48)
        for zz in (h * 0.5, h - 4.0):
            t.ribbon(mb, len(walls) + (i % len(crowns)), zz, 0.6, 0.0, 0.4, n_around=64)
    mb.to_object('DistantTowers', mats, col)
