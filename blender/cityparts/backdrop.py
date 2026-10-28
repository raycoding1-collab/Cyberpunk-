"""The city around the Spire, built as haze layers (docs/inspiration.md):

* a midfield of sculpted towers whose windows shrink to pin-points, with
  neon floor bands, cantilevered crowns, tall curved LED screens and masts;
* far out, Blade Runner-scale megastructures with flared buttress bases
  that rise through the cloud deck, dark except for sparse lights;
* air traffic on lanes around the Spire, the object of known size that
  makes every view read at the right scale."""

import math

import bpy
from mathutils import Matrix, Vector

from . import materials as M
from .freeform import Tower
from .util import MeshBuilder, collection, rng

TAU = 2 * math.pi
ASSETS = __file__.rsplit('/blender/', 1)[0] + '/assets/generated/'

# camera positions whose view toward the Spire must stay clear
SIGHTLINES = [(-34.0, -118.0), (140.0, -330.0), (-120.0, -165.0), (62.0, -64.0), (18.0, -49.0)]
# towers already placed by capsule_spire.build_silhouettes
TAKEN = [(-260, 320), (220, 380), (-420, 650), (380, 700), (40, 900), (-150, 1200), (520, 1100), (-640, 980), (300, -380), (-380, -260)]


def _seg_dist(p, a, b):
    ab = (b[0] - a[0], b[1] - a[1])
    t = max(0.0, min(1.0, ((p[0] - a[0]) * ab[0] + (p[1] - a[1]) * ab[1]) / (ab[0] ** 2 + ab[1] ** 2)))
    return math.hypot(p[0] - a[0] - t * ab[0], p[1] - a[1] - t * ab[1])


def _site_ok(x, y, r, placed):
    if any(_seg_dist((x, y), c, (0.0, 0.0)) < r + 30.0 for c in SIGHTLINES):
        return False
    if any(math.hypot(x - px, y - py) < r + pr + 25.0 for px, py, pr in placed):
        return False
    return True


def _screen(mb, t, mat, th0, th1, z0, z1, off=0.7, n=10):
    """A curved LED screen hugging the tower between two angles."""
    rows = [[tuple(t.point(th0 + (th1 - th0) * i / n, z, off)) for i in range(n + 1)] for z in (z0, z1)]
    verts = rows[0] + rows[1]
    faces = [(i, i + 1, n + 2 + i, n + 1 + i) for i in range(n)]
    uvs = [(i / n, 0.0) for i in range(n + 1)] + [(i / n, 1.0) for i in range(n + 1)]
    mb.add(verts, faces, mat, uvs)


def _vstrip(mb, t, mat, th, z0, z1, w=0.04, off=0.3, n=16):
    """A vertical light strip following the tower surface."""
    zs = [z0 + (z1 - z0) * i / n for i in range(n + 1)]
    left = [tuple(t.point(th - w, z, off)) for z in zs]
    right = [tuple(t.point(th + w, z, off)) for z in zs]
    mb.add(left + right, [(i, n + 1 + i, n + 2 + i, i + 1) for i in range(n)], mat)


def midfield(col, seed=21, count=46):
    R = rng(seed)
    # small, dim windows: at this distance they must read as pin-points
    walls = [M.window_wall(f'CityWin{i}', cell_w=c, floor_h=f, lit=l, strength=s, mullion=m, office=o, zone=z, spandrel=0.42,
                           warm=(1.0, 0.66, 0.36), cool=(0.62, 0.8, 1.0), accent=(1.0, 0.3, 0.7))
             for i, (c, f, l, s, m, o, z) in enumerate([(1.0, 3.4, 0.24, 2.6, 0.5, True, 6), (1.2, 3.2, 0.3, 2.2, 0.62, False, 3),
                                                        (0.9, 3.6, 0.2, 3.0, 0.45, True, 8), (1.4, 3.3, 0.34, 2.0, 0.8, False, 2)])]
    shell = M.metal('CityCrown', base=(0.03, 0.032, 0.036), rough=0.4)
    bands = [M.emission(f'CityBand{i}', c, s) for i, (c, s) in enumerate([((0.1, 0.85, 1.0), 14.0), ((1.0, 0.1, 0.5), 16.0),
                                                                          ((1.0, 0.55, 0.15), 12.0), ((0.55, 0.3, 1.0), 14.0)])]
    soffits = [M.emission(f'CitySoffit{i}', c, 3.0) for i, c in enumerate([(0.75, 0.88, 1.0), (1.0, 0.62, 0.3), (1.0, 0.3, 0.6)])]
    red = M.emission('CityBeacon', (1.0, 0.04, 0.02), 80.0)
    posters = ['poster_dream.png', 'poster_eye.png']
    screens = [M.image_emission(f'CityScreen{i}', ASSETS + p, strength=3.5, alpha_cut=False) for i, p in enumerate(posters)]
    mats = walls + [shell] + bands + soffits + [red] + screens
    I_SHELL = len(walls)
    I_BAND = I_SHELL + 1
    I_SOFF = I_BAND + len(bands)
    I_RED = I_SOFF + len(soffits)
    I_SCR = I_RED + 1
    mb = MeshBuilder()
    placed = [(x, y, 30.0) for x, y in TAKEN]
    made = 0
    tries = 0
    while made < count and tries < 4000:
        tries += 1
        ang = R.uniform(0, TAU)
        rad = 170.0 + 520.0 * R.random() ** 0.8
        x, y = rad * math.cos(ang), rad * math.sin(ang)
        a = R.uniform(11.0, 24.0)
        if not _site_ok(x, y, a, placed):
            continue
        placed.append((x, y, a))
        made += 1
        # nearer towers stay lower so the Spire keeps the skyline
        h = R.uniform(55.0, 120.0) + (rad - 170.0) * R.uniform(0.1, 0.35)
        if rad < 400.0:
            h = min(h, 165.0)
        kind = R.random()
        a0 = R.uniform(0, TAU)
        lobes = None
        if kind < 0.4:  # slab with one or two setbacks, lit edge strips
            n, b = R.uniform(6.0, 10.0), a * R.uniform(0.35, 0.55)
            steps = sorted(R.sample([0.45, 0.6, 0.75, 0.85], R.randint(1, 2)))
            twist = [(0, a0), (h, a0)]
        elif kind < 0.7:  # stepped tower
            n, b = R.uniform(3.5, 6.0), a * R.uniform(0.7, 1.0)
            steps = [0.4, 0.65, 0.85]
            twist = [(0, a0), (h, a0)]
        else:  # sculpted: lobed and twisting
            n, b = R.uniform(2.4, 4.0), a * R.uniform(0.6, 1.0)
            steps = [R.uniform(0.5, 0.75)]
            twist = [(0, a0), (h, a0 + R.uniform(-0.6, 0.6))]
            lobes = (R.choice([3, 4, 6]), [(0, R.uniform(0.04, 0.18)), (h, 0.04)], R.uniform(0, 1))
        prof = [(0.0, (a, b, n))]
        ka, kb = a, b
        for zf in steps:
            prof.append((h * zf - 0.1, (ka, kb, n)))
            ka, kb = ka * R.uniform(0.78, 0.88), kb * R.uniform(0.8, 0.9)
            prof.append((h * zf + 0.1, (ka, kb, n)))
        prof.append((h, (ka, kb, n)))
        t = Tower(x, y, h, profile=prof, twist=twist, lobes=lobes)
        wi = R.randrange(len(walls))
        top = h - R.uniform(6.0, 12.0)
        t.skin(mb, wi, 0.0, top, n_around=48, dz=6.0)
        t.skin(mb, I_SHELL, top, h, n_around=48, dz=4.0, offset=0.4)
        t.cap(mb, I_SHELL, h, offset=0.4, n_around=48)
        crown = R.random()
        if crown < 0.35:  # cantilevered crown with a lit soffit, like the Night City slabs
            over = R.uniform(1.5, 5.0)
            t.ribbon(mb, I_SHELL, top, 1.2, 0.0, over, n_around=48)
            t.ribbon(mb, I_SOFF + R.randrange(len(soffits)), top - 0.15, 0.15, over - 0.6, over - 0.3, n_around=48)
        elif crown < 0.7:  # neon outline along the parapet
            t.ribbon(mb, I_BAND + R.randrange(len(bands)), h - 0.7, 0.3, 0.4, 0.7, n_around=48)
        if R.random() < 0.5:  # one or two neon floor bands
            floors = [k * 3.4 for k in range(3, int(top / 3.4) - 1)]
            bi = I_BAND + R.randrange(len(bands))
            for zz in R.sample(floors, min(R.randint(1, 2), len(floors))):
                t.ribbon(mb, bi, zz, 0.3, 0.0, 0.3, n_around=48)
        if kind < 0.4 and R.random() < 0.7:  # lit strips up the slab corners
            si = I_BAND + R.randrange(len(bands))
            zb = h * R.uniform(0.05, 0.3)
            for th in (0.25, 0.75, 1.25, 1.75):
                _vstrip(mb, t, si, th * math.pi, zb, top - 2.0, w=0.05)
        if R.random() < 0.45:  # tall curved screen
            th0 = math.atan2(-y, -x) + R.uniform(-0.8, 0.8)
            span = R.uniform(0.35, 0.6)
            zs = R.uniform(0.2, 0.45) * top
            _screen(mb, t, I_SCR + R.randrange(len(screens)), th0, th0 + span, zs, zs + R.uniform(22.0, 40.0))
        if R.random() < 0.5:  # mast with beacon
            mh = R.uniform(12.0, 30.0)
            mb.box((x - 0.4, y - 0.4, h), (x + 0.4, y + 0.4, h + mh), I_SHELL)
            mb.box((x - 0.7, y - 0.7, h + mh), (x + 0.7, y + 0.7, h + mh + 1.2), I_RED)
    return mb.to_object('MidfieldCity', mats, col)


def megastructures(col):
    """Kilometre-scale buttressed slabs fading into the haze and cloud."""
    body = M.concrete('MegaConcrete', tone=0.09, tint=(0.9, 0.95, 1.0), panel=(9.0, 6.0), streaks=0.6)
    lights = M.window_wall('MegaLights', cell_w=4.0, floor_h=7.0, lit=0.08, strength=6.0, mullion=3.2, office=False, zone=6,
                           spandrel=0.8, spandrel_color=(0.02, 0.02, 0.024), warm=(1.0, 0.7, 0.4), cool=(0.7, 0.85, 1.0))
    strip = M.emission('MegaStrip', (1.0, 0.62, 0.3), 9.0)
    red = M.emission('MegaBeacon', (1.0, 0.04, 0.02), 140.0)
    mats = [body, lights, strip, red]
    mb = MeshBuilder()
    for (x, y, w, d, h, rot) in [(-520.0, 1350.0, 150.0, 95.0, 980.0, 0.3), (420.0, 1150.0, 110.0, 80.0, 860.0, -0.5),
                                 (1150.0, 1500.0, 170.0, 110.0, 1100.0, 0.9), (-1250.0, 820.0, 130.0, 90.0, 900.0, 1.4),
                                 (1450.0, 450.0, 140.0, 100.0, 940.0, 2.1), (-1500.0, -150.0, 160.0, 120.0, 1000.0, 0.2)]:
        prof = [(0.0, (w * 1.7, d * 1.5, 3.2)), (h * 0.12, (w * 1.05, d * 1.0, 4.0)), (h * 0.5, (w * 0.82, d * 0.8, 5.0)), (h, (w * 0.5, d * 0.55, 6.0))]
        t = Tower(x, y, h, profile=prof, twist=[(0, rot), (h, rot + 0.15)])
        t.skin(mb, 0, 0.0, h * 0.12, n_around=48, dz=12.0)
        t.skin(mb, 1, h * 0.12, h, n_around=48, dz=14.0)
        t.cap(mb, 0, h, n_around=32)
        for k in range(4):
            th = rot + k * TAU / 4 + 0.4
            for z in (h * 0.18, h * 0.32, h * 0.46):
                p = t.point(th, z, 2.0)
                mb.box((p.x - 1.4, p.y - 1.4, z), (p.x + 1.4, p.y + 1.4, z + 2.4), 3)
        for zz in (h * 0.12, h * 0.3):
            t.ribbon(mb, 2, zz, 1.2, 0.0, 1.0, n_around=48)
    ob = mb.to_object('Megastructures', mats, col)
    ob.visible_shadow = False
    return ob


def _spinner_mesh(mats_idx):
    """A compact air-car: lofted body, canopy, head- and tail-light blades."""
    body_i, glass_i, head_i, tail_i, under_i = mats_idx
    mb = MeshBuilder()
    L, W, H = 4.8, 2.0, 1.1
    rings = []
    for i in range(17):
        t = i / 16
        k = math.sin(math.pi * min(1.0, 0.05 + 0.95 * t)) ** 0.45
        w = W / 2 * (0.45 + 0.55 * k)
        h = H / 2 * (0.4 + 0.6 * k) * (1 - 0.35 * max(0.0, t - 0.6))
        x = -L / 2 + L * t
        rings.append([(x, w * math.copysign(abs(math.cos(a)) ** 0.6, math.cos(a)), h * math.copysign(abs(math.sin(a)) ** 0.6, math.sin(a)) * (0.7 if math.sin(a) < 0 else 1.0))
                      for a in [TAU * j / 20 for j in range(20)]])
    for i in range(16):
        mb.ring_strip(rings[i], rings[i + 1], body_i)
    mb.cap(rings[0], body_i, flip=True)
    mb.cap(rings[-1], body_i)
    mb.box((-0.6, -0.62, 0.42), (1.0, 0.62, 0.78), glass_i)
    mb.box((L / 2 - 0.2, -0.75, 0.0), (L / 2 + 0.02, 0.75, 0.12), head_i)
    mb.box((-L / 2 - 0.02, -0.85, 0.05), (-L / 2 + 0.15, 0.85, 0.16), tail_i)
    mb.box((-1.6, -0.5, -0.42), (1.6, 0.5, -0.38), under_i)
    return mb


def traffic(col, seed=33):
    R = rng(seed)
    body = M.paint('SpinnerBody', (0.05, 0.05, 0.06), rough=0.25, metallic=0.6)
    glass = M.clear_glass('SpinnerGlass', tint=(0.3, 0.35, 0.45), rough=0.05)
    head = M.emission('SpinnerHead', (0.9, 0.95, 1.0), 90.0)
    tail = M.emission('SpinnerTail', (1.0, 0.03, 0.04), 70.0)
    under = M.emission('SpinnerUnder', (0.1, 0.75, 1.0), 25.0)
    mesh = _spinner_mesh((0, 1, 2, 3, 4)).to_mesh('Spinner')
    for m in (body, glass, head, tail, under):
        mesh.materials.append(m)
    lanes = [  # (radius, height, direction, count)
        (95.0, 74.0, 1, 7), (130.0, 118.0, -1, 8), (170.0, 160.0, 1, 7), (230.0, 96.0, -1, 8), (320.0, 140.0, 1, 9), (460.0, 210.0, -1, 9)]
    obs = []
    for li, (rad, z, d, n) in enumerate(lanes):
        base = R.uniform(0, TAU)
        for k in range(n):
            a = base + TAU * k / n + R.uniform(-0.25, 0.25)
            r = rad + R.uniform(-8.0, 8.0)
            p = Vector((r * math.cos(a), r * math.sin(a) * 1.12, z + R.uniform(-6.0, 6.0)))
            heading = a + d * math.pi / 2
            ob = bpy.data.objects.new(f'Spinner{li}_{k}', mesh)
            ob.matrix_world = Matrix.Translation(p) @ Matrix.Rotation(heading, 4, 'Z') @ Matrix.Rotation(R.uniform(-0.06, 0.06), 4, 'X')
            col.objects.link(ob)
            obs.append(ob)
    # headlight beams in the haze for a handful of the near ones
    for ob in sorted(obs, key=lambda o: o.matrix_world.translation.length)[:7]:
        lt = bpy.data.lights.new(ob.name + 'Beam', 'SPOT')
        lt.energy = 2.0e5
        lt.color = (0.85, 0.92, 1.0)
        lt.spot_size = math.radians(16)
        lt.spot_blend = 0.6
        lt.shadow_soft_size = 0.2
        lo = bpy.data.objects.new(ob.name + 'Beam', lt)
        fwd = ob.matrix_world.to_3x3() @ Vector((1, 0, 0))
        lo.location = ob.matrix_world.translation + fwd * 2.5
        lo.rotation_euler = (fwd + Vector((0, 0, -0.18))).to_track_quat('-Z', 'Y').to_euler()
        col.objects.link(lo)
    return obs


def carpet_material():
    """The low city seen from above: a street grid lined with sodium lamps,
    blocks speckled with lit windows and signs, wet enough to mirror."""
    g = M.G('CityCarpet')
    obj = g.coords('Object')
    rot = g.n('ShaderNodeVectorRotate', rotation_type='Z_AXIS')
    rot.inputs['Angle'].default_value = 0.32
    g.link(obj, rot.inputs['Vector'])
    sep = g.n('ShaderNodeSeparateXYZ')
    g.link(rot.outputs[0], sep.inputs[0])
    x, y = sep.outputs['X'], sep.outputs['Y']
    fx, fy = g.math('FRACT', g.math('DIVIDE', x, 84.0)), g.math('FRACT', g.math('DIVIDE', y, 58.0))
    street = g.math('MAXIMUM', g.math('LESS_THAN', fx, 0.12), g.math('LESS_THAN', fy, 0.16))
    lamps = g.math('MAXIMUM', g.math('LESS_THAN', g.math('ABSOLUTE', g.math('SUBTRACT', fx, 0.06)), 0.008),
                   g.math('LESS_THAN', g.math('ABSOLUTE', g.math('SUBTRACT', fy, 0.08)), 0.011))
    cell = g.n('ShaderNodeCombineXYZ')
    g.link(g.math('FLOOR', g.math('DIVIDE', x, 4.0)), cell.inputs[0])
    g.link(g.math('FLOOR', g.math('DIVIDE', y, 4.0)), cell.inputs[1])
    wn = g.n('ShaderNodeTexWhiteNoise')
    wn.noise_dimensions = '3D'
    g.link(cell.outputs[0], wn.inputs['Vector'])
    dens = g.noise(g.mapping(obj, (0.004, 0.004, 0.004)), 1.0, 2, 0.5)
    lit = g.math('GREATER_THAN', wn.outputs['Value'], g.math('MULTIPLY_ADD', dens, -0.25, 0.97))
    lit = g.math('MULTIPLY', lit, g.math('SUBTRACT', 1.0, street))
    hue = g.math('FRACT', g.math('MULTIPLY', wn.outputs['Value'], 37.0))
    lcol = g.ramp(hue, [(0.0, (1.0, 0.62, 0.32)), (0.55, (0.62, 0.8, 1.0)), (0.8, (1.0, 0.25, 0.6)), (0.92, (0.2, 0.9, 1.0))], 'CONSTANT')
    sodium = g.mix(lamps, (0, 0, 0), (1.0, 0.5, 0.18))
    emis = g.mix(lit, sodium, lcol)
    strength = g.math('MULTIPLY_ADD', lit, 2.5, g.math('MULTIPLY', lamps, 3.0))
    b = g.bsdf(**{'Base Color': (0.018, 0.018, 0.02), 'Roughness': 0.3, 'Emission Color': emis, 'Emission Strength': strength})
    return g.done(b.outputs[0])


def ground_lights(col):
    mat = carpet_material()
    mb = MeshBuilder()
    n = 96
    for r0, r1 in ((95.0, 400.0), (400.0, 3000.0)):
        inner = [(r0 * math.cos(TAU * i / n), r0 * math.sin(TAU * i / n), 0.03) for i in range(n)]
        outer = [(r1 * math.cos(TAU * i / n), r1 * math.sin(TAU * i / n), 0.03) for i in range(n)]
        mb.add(inner + outer, [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)], 0)
    ob = mb.to_object('CityCarpet', [mat], col)
    ob.visible_shadow = False
    return ob


def build():
    col = collection('Backdrop')
    ground_lights(col)
    midfield(col)
    megastructures(col)
    traffic(col)
    return col
