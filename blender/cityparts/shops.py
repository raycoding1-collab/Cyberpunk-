"""Street-level shops behind the Hive arcade, modelled as real rooms: glazing
with mullions and transoms, lit ceilings, shelving with goods, ramen
counters with lanterns, a cyber clinic, a neon bar, roller shutters on the
closed units, and the shop names in 3D lettering on the fascia."""

import math

from mathutils import Matrix, Vector

from . import materials as M
from . import signs
from .util import MeshBuilder, collection, rng

KINDS = ['shelves', 'ramen', 'clinic', 'bar', 'shelves', 'closed', 'ramen', 'shelves', 'bar', 'clinic', 'closed']
NAMES = {
    'shelves': ['24H MART', 'PHARMACY 薬局', '電脳 PARTS', 'MART 一番'],
    'ramen': ['ラーメン 一番', 'NOODLE BAR', '餃子 GYOZA', '拉麺 RAMEN'],
    'clinic': ['義体 CLINIC', '義眼 OPTICS', 'BIO-LAB'],
    'bar': ['BAR 猫', 'KARAOKE 星', 'SAKE 酒場'],
    'closed': ['PAWN 質屋', 'TATTOO 刺青'],
}
SIGN_COLORS = {
    'shelves': (0.9, 0.95, 1.0), 'ramen': (1.0, 0.25, 0.08), 'clinic': (0.1, 0.85, 1.0),
    'bar': (1.0, 0.1, 0.55), 'closed': (1.0, 0.6, 0.15),
}


def goods_material():
    g = M.G('ShopGoods')
    uv = g.coords('UV')
    br = g.n('ShaderNodeTexBrick', Scale=1.0, **{'Mortar Size': 0.012, 'Brick Width': 0.14, 'Row Height': 0.22, 'Bias': 0.0})
    br.offset = 0.37
    br.inputs['Color1'].default_value = (0, 0, 0, 1)
    br.inputs['Color2'].default_value = (1, 1, 1, 1)
    br.inputs['Mortar'].default_value = (0.02, 0.02, 0.02, 1)
    g.link(uv, br.inputs['Vector'])
    sep = g.n('ShaderNodeSeparateColor')
    g.link(br.outputs['Color'], sep.inputs[0])
    col = g.ramp(sep.outputs[0], [(0.0, (0.9, 0.12, 0.1)), (0.18, (1.0, 0.8, 0.1)), (0.32, (0.1, 0.4, 0.95)),
                                   (0.48, (0.95, 0.95, 0.92)), (0.62, (0.1, 0.7, 0.3)), (0.76, (1.0, 0.4, 0.7)), (0.88, (0.2, 0.2, 0.22))], 'CONSTANT')
    col = g.mix(br.outputs['Fac'], col, (0.03, 0.03, 0.03))
    b = g.bsdf(**{'Base Color': col, 'Roughness': 0.35, 'Emission Color': col, 'Emission Strength': 0.35})
    return g.done(b.outputs[0])


def shutter_material():
    g = M.G('RollerShutter')
    uv = g.coords('UV')
    sep = g.n('ShaderNodeSeparateXYZ')
    g.link(uv, sep.inputs[0])
    rib = g.math('SINE', g.math('MULTIPLY', sep.outputs['Y'], 2 * math.pi / 0.09))
    bump = g.n('ShaderNodeBump', Strength=0.6, Distance=0.01)
    g.link(rib, bump.inputs['Height'])
    obj = g.coords('Object')
    grime = g.noise(g.mapping(obj, (1, 1, 0.2)), 3.0, 5, 0.6)
    base = g.mix(grime, (0.12, 0.12, 0.13), (0.05, 0.05, 0.05))
    b = g.bsdf(**{'Base Color': base, 'Metallic': 0.8, 'Roughness': 0.45, 'Normal': bump.outputs[0]})
    return g.done(b.outputs[0])


def build_arcade(col, glass_x, segments, columns, height=4.6, depth=9.0, seed=8):
    """Shops along the plane x = glass_x, facing +x, between column centres."""
    R = rng(seed)
    glass = M.clear_glass('ShopGlass', tint=(0.92, 0.95, 1.0), rough=0.015)
    mull = M.metal('ShopMullion', base=(0.04, 0.04, 0.045), rough=0.3)
    floor = M.wet_paving('ShopFloor', tile=0.6, tone=0.12)
    wall = M.paint('ShopWall', (0.55, 0.52, 0.48), rough=0.6)
    goods = goods_material()
    wood = M.paint('Counter', (0.22, 0.1, 0.05), rough=0.4)
    shutter = shutter_material()
    clinic_wall = M.paint('ClinicWall', (0.85, 0.9, 0.92), rough=0.25)
    ceil = {
        'shelves': M.emission('CeilCool', (0.85, 0.92, 1.0), 9.0),
        'ramen': M.emission('CeilWarm', (1.0, 0.62, 0.3), 7.0),
        'clinic': M.emission('CeilClinic', (0.6, 0.95, 1.0), 10.0),
        'bar': M.emission('CeilBar', (1.0, 0.15, 0.5), 5.0),
        'closed': M.emission('CeilOff', (1.0, 0.7, 0.4), 0.4),
    }
    lantern = M.emission('Lantern', (1.0, 0.18, 0.06), 9.0)
    neon_bar = M.emission('BarNeon', (1.0, 0.1, 0.5), 20.0)
    cyan_line = M.emission('ClinicLine', (0.1, 0.9, 1.0), 16.0)
    mats = [glass, mull, floor, wall, goods, wood, shutter, clinic_wall,
            ceil['shelves'], ceil['ramen'], ceil['clinic'], ceil['bar'], ceil['closed'], lantern, neon_bar, cyan_line]
    I = {m.name: i for i, m in enumerate(mats)}
    mb = MeshBuilder()
    xb = glass_x - depth
    bays = []
    for (s0, s1) in segments:
        edges = [s0] + [c for c in columns if s0 + 2 < c < s1 - 2] + [s1]
        for a, b in zip(edges[:-1], edges[1:]):
            if b - a > 4.0:
                bays.append((a + 0.8, b - 0.8))
    for bi, (ya, yb) in enumerate(bays):
        kind = KINDS[(bi + seed) % len(KINDS)]
        w = yb - ya
        # room shell: floor, ceiling, partitions, back wall
        mb.box((xb, ya, -0.05), (glass_x, yb, 0.02), I['ShopFloor'], faces=(0, 0, 0, 0, 0, 1))
        mb.box((xb, ya, height), (glass_x, yb, height + 0.3), I['ShopWall'], faces=(0, 0, 0, 0, 1, 0))
        for yy, f in ((ya, (0, 0, 0, 1, 0, 0)), (yb, (0, 0, 1, 0, 0, 0))):
            mb.box((xb, yy - 0.2, 0), (glass_x, yy + 0.2, height), I['ClinicWall'] if kind == 'clinic' else I['ShopWall'], faces=f)
        mb.box((xb - 0.3, ya, 0), (xb, yb, height), I['ClinicWall'] if kind == 'clinic' else I['ShopWall'], faces=(0, 1, 0, 0, 0, 0))
        # ceiling light panels
        cm = I[ceil[kind].name]
        for k in range(3):
            xx = xb + 1.5 + k * 2.8
            mb.box((xx - 0.3, ya + 0.8, height - 0.04), (xx + 0.3, yb - 0.8, height), cm, faces=(0, 0, 0, 0, 1, 0))
        if kind == 'shelves':
            for k, xx in enumerate((xb + 0.05, xb + 3.4, xb + 5.6)):
                ext = (ya + 0.4, yb - 0.4) if k == 0 else (ya + 1.2, yb - 1.2)
                for zz in (0.15, 0.6, 1.05, 1.5, 1.95):
                    mb.box((xx, ext[0], zz), (xx + 0.5, ext[1], zz + 0.04), I['ShopMullion'])
                    gb = MeshBuilder()
                    gb.box((xx, ext[0], zz + 0.04), (xx + 0.45, ext[1], zz + 0.34), 0, faces=(1, 1, 0, 0, 0, 0))
                    mb.merge(gb, mat_offset=I['ShopGoods'])
            mb.box((glass_x - 2.4, ya + 0.6, 0), (glass_x - 1.6, ya + 3.4, 1.05), I['Counter'])
        elif kind == 'ramen':
            mb.box((xb + 2.2, ya + 0.6, 0), (xb + 3.0, yb - 0.6, 1.05), I['Counter'])
            mb.box((xb + 2.0, ya + 0.5, 1.05), (xb + 3.2, yb - 0.5, 1.1), I['Counter'])
            for k in range(int(w // 1.4)):
                yy = ya + 0.9 + k * 1.4
                cx, cz = glass_x - 2.0, height - 1.1
                ring = [(cx + 0.28 * math.cos(2 * math.pi * j / 12), yy + 0.28 * math.sin(2 * math.pi * j / 12)) for j in range(12)]
                mb.extrude_polygon(ring, cz - 0.38, cz + 0.38, I['Lantern'], I['Lantern'])
                mb.box((cx - 0.01, yy - 0.01, cz + 0.38), (cx + 0.01, yy + 0.01, height), I['ShopMullion'])
        elif kind == 'clinic':
            for zz in (0.9, 2.6):
                mb.box((xb + 0.02, ya + 0.4, zz), (xb + 0.06, yb - 0.4, zz + 0.05), I['ClinicLine'])
            mb.box((xb + 3.0, ya + w / 2 - 0.4, 0), (xb + 4.8, ya + w / 2 + 0.4, 0.75), I['ClinicWall'])
        elif kind == 'bar':
            mb.box((xb + 0.05, ya + 0.5, 1.6), (xb + 0.1, yb - 0.5, 1.65), I['BarNeon'])
            for zz in (1.8, 2.3, 2.8):
                gb = MeshBuilder()
                gb.box((xb + 0.05, ya + 0.6, zz), (xb + 0.35, yb - 0.6, zz + 0.3), 0, faces=(0, 1, 0, 0, 0, 0))
                mb.merge(gb, mat_offset=I['ShopGoods'])
            mb.box((xb + 2.2, ya + 0.5, 0), (xb + 3.0, yb - 0.5, 1.1), I['Counter'])
        # glazing with mullions, transom and a door
        gl = MeshBuilder()
        gl.add([(glass_x, yb, 0.0), (glass_x, ya, 0.0), (glass_x, ya, height), (glass_x, yb, height)], [(3, 2, 1, 0)], 0)
        mb.merge(gl, mat_offset=I['ShopGlass'])
        n_m = max(2, int(w // 2.8))
        for k in range(n_m + 1):
            yy = ya + w * k / n_m
            mb.box((glass_x - 0.06, yy - 0.05, 0), (glass_x + 0.06, yy + 0.05, height), I['ShopMullion'])
        mb.box((glass_x - 0.06, ya, 3.3), (glass_x + 0.06, yb, 3.38), I['ShopMullion'])
        mb.box((glass_x - 0.06, ya, 0), (glass_x + 0.06, yb, 0.12), I['ShopMullion'])
        if kind == 'closed':
            sh = MeshBuilder()
            drop = R.uniform(0.0, 1.4)
            sh.box((glass_x + 0.15, ya, drop), (glass_x + 0.25, yb, height), 0, faces=(0, 1, 0, 0, 0, 0))
            mb.merge(sh, mat_offset=I['RollerShutter'])
            mb.box((glass_x + 0.1, ya, height - 0.1), (glass_x + 0.5, yb, height + 0.4), I['ShopMullion'])
        # shop name in 3D lettering on the fascia
        name = R.choice(NAMES[kind])
        sc = M.emission(f'ShopSign_{kind}', SIGN_COLORS[kind], 7.0)
        signs.text_object(name, 'DelaGothicOne-Regular.ttf', 0.62, f'ShopName{bi}', col, sc,
                          location=(glass_x + 0.25, (ya + yb) / 2, height + 0.42), rotation=(math.pi / 2, 0, math.pi / 2),
                          extrude=0.05, bevel=0.012)
    mb.to_object('HiveShops', mats, col)
    return bays
