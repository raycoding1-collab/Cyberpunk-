"""Cycles material library. All materials are procedural (no texture files
except generated LED/sign imagery) so the scene stays self-contained."""

import bpy

_cache = {}


class G:
    """Tiny node-graph helper."""

    def __init__(self, name):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        self.m = m
        self.nt = m.node_tree
        self.nt.nodes.clear()
        self.out = self.nt.nodes.new('ShaderNodeOutputMaterial')

    def n(self, kind, **inputs):
        node = self.nt.nodes.new(kind)
        for k, v in inputs.items():
            if k.startswith('_'):
                setattr(node, k[1:], v)
            else:
                node.inputs[k].default_value = v
        return node

    def link(self, a, b):
        self.nt.links.new(a, b)

    def math(self, op, a, b=None, c=None, clamp=False):
        node = self.nt.nodes.new('ShaderNodeMath')
        node.operation = op
        node.use_clamp = clamp
        for i, v in enumerate((a, b, c)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                node.inputs[i].default_value = v
            else:
                self.link(v, node.inputs[i])
        return node.outputs[0]

    def mix(self, fac, a, b, blend='MIX', data='RGBA'):
        node = self.nt.nodes.new('ShaderNodeMix')
        node.data_type = data
        node.blend_type = blend
        ia, ib, io = (6, 7, 2) if data == 'RGBA' else (2, 3, 0)
        for sock, v in ((node.inputs[0], fac), (node.inputs[ia], a), (node.inputs[ib], b)):
            if isinstance(v, (int, float, tuple, list)):
                sock.default_value = v if not isinstance(v, (tuple, list)) or len(v) == 4 or data != 'RGBA' else (*v, 1.0)
            else:
                self.link(v, sock)
        return node.outputs[io]

    def ramp(self, fac, stops, interp='LINEAR'):
        node = self.nt.nodes.new('ShaderNodeValToRGB')
        cr = node.color_ramp
        cr.interpolation = interp
        while len(cr.elements) > 1:
            cr.elements.remove(cr.elements[-1])
        cr.elements[0].position = stops[0][0]
        cr.elements[0].color = (*stops[0][1], 1.0) if len(stops[0][1]) == 3 else stops[0][1]
        for pos, col in stops[1:]:
            e = cr.elements.new(pos)
            e.color = (*col, 1.0) if len(col) == 3 else col
        self.link(fac, node.inputs[0])
        return node.outputs[0]

    def coords(self, kind='Object'):
        tc = self.nt.nodes.get('_tc') or self.n('ShaderNodeTexCoord')
        tc.name = '_tc'
        return tc.outputs[kind]

    def mapping(self, vec, scale=(1, 1, 1), loc=(0, 0, 0)):
        node = self.n('ShaderNodeMapping')
        node.inputs['Scale'].default_value = scale
        node.inputs['Location'].default_value = loc
        self.link(vec, node.inputs['Vector'])
        return node.outputs[0]

    def noise(self, vec, scale=1.0, detail=4.0, rough=0.5, out='Fac', dims='3D'):
        node = self.n('ShaderNodeTexNoise', Scale=scale, Detail=detail, Roughness=rough)
        node.noise_dimensions = dims
        self.link(vec, node.inputs['Vector'])
        return node.outputs[out]

    def bsdf(self, **kw):
        node = self.n('ShaderNodeBsdfPrincipled')
        for k, v in kw.items():
            sock = node.inputs[k]
            if isinstance(v, (int, float)):
                sock.default_value = v
            elif isinstance(v, tuple):
                sock.default_value = (*v, 1.0) if len(v) == 3 and sock.type == 'RGBA' else v
            else:
                self.link(v, sock)
        return node

    def done(self, surface, volume=None):
        self.link(surface, self.out.inputs['Surface'])
        if volume is not None:
            self.link(volume, self.out.inputs['Volume'])
        return self.m


def cached(fn):
    def wrap(*a, **kw):
        key = (fn.__name__, a, tuple(sorted(kw.items())))
        if key not in _cache:
            _cache[key] = fn(*a, **kw)
        return _cache[key]
    return wrap


# ---------------------------------------------------------------------------
# Structural materials
# ---------------------------------------------------------------------------

@cached
def concrete(name='Concrete', tone=0.16, tint=(1.0, 0.98, 0.95), panel=(3.0, 1.5), wet=0.35, streaks=0.4):
    g = G(name)
    obj = g.coords('Object')
    uv = g.coords('UV')
    # board-formed panels with fine seams
    brick = g.n('ShaderNodeTexBrick', Scale=1.0, **{'Mortar Size': 0.025, 'Brick Width': panel[0], 'Row Height': panel[1], 'Mortar Smooth': 0.3})
    brick.offset = 0.0
    brick.inputs['Color1'].default_value = (0.92, 0.92, 0.92, 1)
    brick.inputs['Color2'].default_value = (1.08, 1.08, 1.08, 1)
    g.link(uv, brick.inputs['Vector'])
    # large-scale mottling and vertical rain streaks
    mott = g.noise(obj, 0.35, 6, 0.6)
    streak = g.noise(g.mapping(obj, (0.9, 0.9, 0.035)), 3.0, 3, 0.6)
    streak_m = g.ramp(streak, [(0.45, (1, 1, 1)), (0.62, (1 - streaks, 1 - streaks, 1 - streaks))])
    base = g.mix(mott, (tone * tint[0] * 0.75, tone * tint[1] * 0.75, tone * tint[2] * 0.75), (tone * tint[0] * 1.2, tone * tint[1] * 1.2, tone * tint[2] * 1.2))
    base = g.mix(1.0, base, brick.outputs['Color'], 'MULTIPLY')
    base = g.mix(1.0, base, streak_m, 'MULTIPLY')
    rough = g.math('MULTIPLY_ADD', streak, -wet, 0.92)
    fine = g.noise(obj, 18.0, 8, 0.7)
    bump = g.n('ShaderNodeBump', Strength=0.25, Distance=0.02)
    seam = g.math('MULTIPLY_ADD', brick.outputs['Fac'], -0.6, fine)
    g.link(seam, bump.inputs['Height'])
    b = g.bsdf(**{'Base Color': base, 'Roughness': rough, 'Normal': bump.outputs[0]})
    return g.done(b.outputs[0])


@cached
def metal(name='DarkMetal', base=(0.035, 0.035, 0.04), rough=0.32, aniso=0.0):
    g = G(name)
    obj = g.coords('Object')
    n = g.noise(obj, 2.0, 6, 0.6)
    r = g.math('MULTIPLY_ADD', n, 0.25, rough - 0.1)
    b = g.bsdf(**{'Base Color': base, 'Metallic': 1.0, 'Roughness': r, 'Anisotropic': aniso})
    return g.done(b.outputs[0])


@cached
def paint(name, color, rough=0.45, metallic=0.0):
    g = G(name)
    obj = g.coords('Object')
    n = g.noise(obj, 4.0, 5, 0.6)
    r = g.math('MULTIPLY_ADD', n, 0.2, rough - 0.1)
    b = g.bsdf(**{'Base Color': color, 'Roughness': r, 'Metallic': metallic})
    return g.done(b.outputs[0])


@cached
def emission(name, color, strength=10.0):
    g = G(name)
    e = g.n('ShaderNodeEmission', Strength=strength)
    e.inputs['Color'].default_value = (*color, 1.0)
    return g.done(e.outputs[0])


@cached
def neon(name, color, strength=40.0):
    """Glass tube with a hot core: emission plus a thin glossy skin."""
    g = G(name)
    e = g.n('ShaderNodeEmission', Strength=strength)
    e.inputs['Color'].default_value = (*color, 1.0)
    lw = g.n('ShaderNodeLayerWeight', Blend=0.35)
    core = g.mix(lw.outputs['Facing'], (1.0, 1.0, 1.0), color)
    g.link(core, e.inputs['Color'])
    return g.done(e.outputs[0])


@cached
def clear_glass(name='ClearGlass', tint=(0.85, 0.9, 1.0), rough=0.02):
    g = G(name)
    t = g.n('ShaderNodeBsdfTransparent')
    t.inputs['Color'].default_value = (*tint, 1)
    gl = g.n('ShaderNodeBsdfGlossy', Roughness=rough)
    fr = g.n('ShaderNodeFresnel', IOR=1.5)
    mx = g.n('ShaderNodeMixShader')
    g.link(fr.outputs[0], mx.inputs[0])
    g.link(t.outputs[0], mx.inputs[1])
    g.link(gl.outputs[0], mx.inputs[2])
    return g.done(mx.outputs[0])


# ---------------------------------------------------------------------------
# Curtain walls with lit interiors (per-window random via Brick texture)
# ---------------------------------------------------------------------------

@cached
def window_wall(name, cell_w=1.6, floor_h=4.0, lit=0.45, strength=5.0, mullion=0.12, office=True,
                warm=(1.0, 0.62, 0.30), cool=(0.72, 0.84, 1.0), accent=(1.0, 0.25, 0.6), glass=(0.012, 0.014, 0.02),
                spandrel=None, zone=4, spandrel_color=(0.025, 0.025, 0.03)):
    """Curtain wall in metric UV space. Lit windows cluster into office zones
    and floors (like a real tower at night) instead of random pixels; frames
    are drawn with thin mullions and deep spandrel bands; some windows have
    blinds half drawn; every room is brighter toward its ceiling."""
    g = G(name)
    uv = g.coords('UV')
    sep = g.n('ShaderNodeSeparateXYZ')
    g.link(uv, sep.inputs[0])
    u, v = sep.outputs['X'], sep.outputs['Y']
    cu = g.math('DIVIDE', u, cell_w)
    cv = g.math('DIVIDE', v, floor_h)
    iu, iv = g.math('FLOOR', cu), g.math('FLOOR', cv)
    fx, fy = g.math('FRACT', cu), g.math('FRACT', cv)

    def white(x, y, z):
        c = g.n('ShaderNodeCombineXYZ')
        for i, val in enumerate((x, y, z)):
            if isinstance(val, (int, float)):
                c.inputs[i].default_value = val
            else:
                g.link(val, c.inputs[i])
        w = g.n('ShaderNodeTexWhiteNoise')
        w.noise_dimensions = '3D'
        g.link(c.outputs[0], w.inputs['Vector'])
        return w.outputs['Value']

    r_cell = white(iu, iv, 3.0)
    r_zone = white(g.math('FLOOR', g.math('DIVIDE', iu, float(zone))), iv, 11.0)
    r_floor = white(0.0, iv, 29.0)
    r_blind = white(iu, iv, 47.0)
    score = g.math('MULTIPLY_ADD', r_zone, 0.6, g.math('MULTIPLY_ADD', r_floor, 0.25 if office else 0.1, g.math('MULTIPLY', r_cell, 0.15 if office else 0.3)))
    if not office:
        score = g.math('DIVIDE', score, 1.0)
    thresh = 1.0 - lit
    span = 0.6 + (0.25 if office else 0.1) + (0.15 if office else 0.3)
    on = g.math('GREATER_THAN', g.math('DIVIDE', score, span), thresh)
    # colour temperature mostly per zone, accents rare
    col = g.ramp(g.math('MULTIPLY_ADD', r_zone, 0.85, g.math('MULTIPLY', r_cell, 0.15)), [
        (0.0, warm), (0.5, cool), (0.78, (warm[0], min(1.0, warm[1] * 1.2), min(1.0, warm[2] * 1.5))), (0.94, accent)], 'CONSTANT')
    level = g.math('MULTIPLY_ADD', r_cell, 0.8, 0.45)
    # frame: thin mullions + spandrel band at the slab
    sp = spandrel if spandrel is not None else (0.24 if office else 0.32)
    mw = mullion / (2.0 * cell_w)
    mull = g.math('LESS_THAN', g.math('MINIMUM', fx, g.math('SUBTRACT', 1.0, fx)), mw)
    span_m = g.math('LESS_THAN', fy, sp)
    head = g.math('GREATER_THAN', fy, 0.97)
    frame = g.math('MAXIMUM', g.math('MAXIMUM', mull, span_m), head)
    # room depth cue: brighter toward the ceiling; blinds pulled half way on some
    fyw = g.math('DIVIDE', g.math('SUBTRACT', fy, sp), 1.0 - sp)
    grad = g.ramp(fyw, [(0.0, (0.55, 0.55, 0.55)), (0.8, (1.0, 1.0, 1.0)), (1.0, (1.45, 1.45, 1.45))])
    blind_on = g.math('GREATER_THAN', r_blind, 0.72)
    blind_level = g.math('MULTIPLY_ADD', g.math('FRACT', g.math('MULTIPLY', r_blind, 13.0)), 0.5, 0.35)
    blinded = g.math('MULTIPLY', blind_on, g.math('GREATER_THAN', fyw, blind_level))
    blind_k = g.math('MULTIPLY_ADD', blinded, -0.55, 1.0)
    inten = g.math('MULTIPLY', g.math('MULTIPLY', level, on), blind_k)
    inten = g.math('MULTIPLY', inten, g.math('SUBTRACT', 1.0, frame))
    emis = g.mix(1.0, col, grad, 'MULTIPLY')
    emis = g.mix(1.0, emis, inten, 'MULTIPLY')
    basec = g.mix(frame, glass, spandrel_color)
    rough = g.mix(frame, 0.035, 0.35, data='FLOAT')
    metal_v = g.mix(frame, 0.0, 0.6, data='FLOAT')
    b = g.bsdf(**{'Base Color': basec, 'Roughness': rough, 'Metallic': metal_v, 'Emission Color': emis, 'Emission Strength': strength})
    return g.done(b.outputs[0])


# ---------------------------------------------------------------------------
# Capsule modules (Hive)
# ---------------------------------------------------------------------------

@cached
def capsule_shell(name='CapsuleShell'):
    g = G(name)
    obj = g.coords('Object')
    uv = g.coords('UV')
    oi = g.n('ShaderNodeObjectInfo')
    # mostly enamel white-grey, some muted teal / rust / charcoal capsules
    paintc = g.ramp(oi.outputs['Random'], [
        (0.0, (0.52, 0.53, 0.52)), (0.55, (0.62, 0.61, 0.58)), (0.78, (0.16, 0.30, 0.31)),
        (0.86, (0.38, 0.16, 0.09)), (0.93, (0.06, 0.06, 0.07))], 'CONSTANT')
    grime = g.noise(g.mapping(g.coords('Generated'), (1.0, 1.0, 0.25)), 6.0, 6, 0.65)
    gm = g.ramp(grime, [(0.35, (1, 1, 1)), (0.75, (0.45, 0.42, 0.40))])
    col = g.mix(1.0, paintc, gm, 'MULTIPLY')
    seams = g.n('ShaderNodeTexBrick', Scale=1.0, **{'Mortar Size': 0.02, 'Brick Width': 1.6, 'Row Height': 1.1, 'Mortar Smooth': 0.2})
    seams.offset = 0.5
    g.link(uv, seams.inputs['Vector'])
    bump = g.n('ShaderNodeBump', Strength=0.35, Distance=0.02)
    fine = g.noise(obj, 30.0, 4, 0.6)
    g.link(g.math('MULTIPLY_ADD', seams.outputs['Fac'], -1.0, g.math('MULTIPLY', fine, 0.15)), bump.inputs['Height'])
    rough = g.math('MULTIPLY_ADD', grime, 0.35, 0.22)
    b = g.bsdf(**{'Base Color': col, 'Roughness': rough, 'Normal': bump.outputs[0], 'Coat Weight': 0.25, 'Coat Roughness': 0.15})
    return g.done(b.outputs[0])


@cached
def capsule_interior(name='CapsuleInterior'):
    """Room glow behind the porthole; colour and level vary per capsule."""
    g = G(name)
    oi = g.n('ShaderNodeObjectInfo')
    r = oi.outputs['Random']
    r2 = g.math('FRACT', g.math('MULTIPLY', r, 13.37))
    col = g.ramp(r2, [
        (0.0, (0.004, 0.004, 0.005)), (0.36, (1.0, 0.52, 0.22)), (0.70, (1.0, 0.74, 0.46)),
        (0.86, (0.70, 0.82, 1.0)), (0.95, (1.0, 0.3, 0.5)), (0.975, (0.2, 0.8, 1.0))], 'CONSTANT')
    gen = g.coords('Generated')
    sep = g.n('ShaderNodeSeparateXYZ')
    g.link(gen, sep.inputs[0])
    grad = g.ramp(sep.outputs['Z'], [(0.0, (0.35, 0.35, 0.35)), (1.0, (1.4, 1.4, 1.4))])
    strength = g.math('MULTIPLY_ADD', g.math('FRACT', g.math('MULTIPLY', r, 71.3)), 7.0, 4.0)
    c = g.mix(1.0, col, grad, 'MULTIPLY')
    e = g.n('ShaderNodeEmission')
    g.link(c, e.inputs['Color'])
    g.link(strength, e.inputs['Strength'])
    return g.done(e.outputs[0])


@cached
def capsule_porch(name='CapsulePorch'):
    """Small warm downlight under each capsule's drip edge (on for ~3/4 of them)."""
    g = G(name)
    oi = g.n('ShaderNodeObjectInfo')
    r = g.math('FRACT', g.math('MULTIPLY', oi.outputs['Random'], 31.7))
    on = g.math('GREATER_THAN', r, 0.25)
    e = g.n('ShaderNodeEmission')
    e.inputs['Color'].default_value = (1.0, 0.78, 0.55, 1)
    g.link(g.math('MULTIPLY', on, g.math('MULTIPLY_ADD', r, 10.0, 8.0)), e.inputs['Strength'])
    return g.done(e.outputs[0])


# ---------------------------------------------------------------------------
# Ground
# ---------------------------------------------------------------------------

@cached
def wet_asphalt(name='WetAsphalt'):
    g = G(name)
    obj = g.coords('Object')
    large = g.noise(obj, 0.045, 5, 0.55)
    mid = g.noise(obj, 0.4, 4, 0.5)
    pud = g.math('MULTIPLY_ADD', mid, 0.25, large)
    puddle = g.ramp(pud, [(0.56, (0, 0, 0)), (0.6, (1, 1, 1))])
    grain = g.noise(obj, 25.0, 6, 0.7)
    base = g.mix(grain, (0.018, 0.018, 0.02), (0.045, 0.044, 0.046))
    base = g.mix(puddle, base, (0.01, 0.01, 0.012))
    sepp = g.n('ShaderNodeSeparateColor')
    g.link(puddle, sepp.inputs[0])
    rough = g.mix(sepp.outputs[0], g.math('MULTIPLY_ADD', grain, 0.25, 0.16), 0.015, data='FLOAT')
    bump = g.n('ShaderNodeBump', Strength=0.35, Distance=0.01)
    g.link(g.math('MULTIPLY', grain, g.math('SUBTRACT', 1.0, sepp.outputs[0])), bump.inputs['Height'])
    b = g.bsdf(**{'Base Color': base, 'Roughness': rough, 'Normal': bump.outputs[0], 'Specular IOR Level': 0.6})
    return g.done(b.outputs[0])


@cached
def wet_paving(name='WetPaving', tile=0.9, tone=0.07):
    g = G(name)
    obj = g.coords('Object')
    br = g.n('ShaderNodeTexBrick', Scale=1.0, **{'Mortar Size': 0.012, 'Brick Width': tile * 1.6, 'Row Height': tile, 'Mortar Smooth': 0.2, 'Bias': 0.0})
    br.inputs['Color1'].default_value = (tone * 0.8, tone * 0.8, tone * 0.82, 1)
    br.inputs['Color2'].default_value = (tone * 1.3, tone * 1.25, tone * 1.2, 1)
    br.inputs['Mortar'].default_value = (0.01, 0.01, 0.01, 1)
    g.link(obj, br.inputs['Vector'])
    large = g.noise(obj, 0.06, 5, 0.55)
    puddle = g.ramp(large, [(0.55, (0, 0, 0)), (0.6, (1, 1, 1))])
    sp = g.n('ShaderNodeSeparateColor')
    g.link(puddle, sp.inputs[0])
    rough = g.mix(sp.outputs[0], g.math('MULTIPLY_ADD', br.outputs['Fac'], 0.5, 0.18), 0.02, data='FLOAT')
    bump = g.n('ShaderNodeBump', Strength=0.4, Distance=0.01)
    g.link(g.math('MULTIPLY', br.outputs['Fac'], -1.0), bump.inputs['Height'])
    b = g.bsdf(**{'Base Color': br.outputs['Color'], 'Roughness': rough, 'Normal': bump.outputs[0]})
    return g.done(b.outputs[0])


# ---------------------------------------------------------------------------
# Screens & holograms
# ---------------------------------------------------------------------------

def led_screen(name, image_path, strength=4.0, pixel_pitch=0.25, size=(100.0, 100.0)):
    g = G(name)
    uv = g.coords('UV')
    img = bpy.data.images.load(image_path, check_existing=True)
    tex = g.n('ShaderNodeTexImage')
    tex.image = img
    tex.interpolation = 'Cubic'
    g.link(uv, tex.inputs['Vector'])
    # LED pixel grid (visible only up close)
    sep = g.n('ShaderNodeSeparateXYZ')
    g.link(uv, sep.inputs[0])
    px = g.math('FRACT', g.math('MULTIPLY', sep.outputs['X'], size[0] / pixel_pitch))
    py = g.math('FRACT', g.math('MULTIPLY', sep.outputs['Y'], size[1] / pixel_pitch))
    gx = g.math('SMOOTH_MIN', g.math('MULTIPLY', px, 8.0), g.math('MULTIPLY', g.math('SUBTRACT', 1.0, px), 8.0), 0.4)
    gy = g.math('SMOOTH_MIN', g.math('MULTIPLY', py, 8.0), g.math('MULTIPLY', g.math('SUBTRACT', 1.0, py), 8.0), 0.4)
    grid = g.math('MINIMUM', g.math('MINIMUM', gx, gy), 1.0)
    grid = g.math('MULTIPLY_ADD', grid, 0.55, 0.45)
    col = g.mix(1.0, tex.outputs['Color'], grid, 'MULTIPLY')
    b = g.bsdf(**{'Base Color': (0.005, 0.005, 0.006), 'Roughness': 0.18, 'Emission Color': col, 'Emission Strength': strength})
    return g.done(b.outputs[0])


@cached
def hologram(name, color, strength=6.0, scan=1.6):
    g = G(name)
    obj = g.coords('Object')
    sep = g.n('ShaderNodeSeparateXYZ')
    g.link(obj, sep.inputs[0])
    lines = g.math('SINE', g.math('MULTIPLY', sep.outputs['Z'], scan * 6.2832))
    lines = g.math('MULTIPLY_ADD', lines, 0.35, 0.75)
    lw = g.n('ShaderNodeLayerWeight', Blend=0.45)
    rim = g.math('POWER', lw.outputs['Facing'], 1.6)
    amt = g.math('MULTIPLY', g.math('MULTIPLY_ADD', rim, 1.0, 0.18), lines)
    e = g.n('ShaderNodeEmission')
    e.inputs['Color'].default_value = (*color, 1)
    g.link(g.math('MULTIPLY', amt, strength), e.inputs['Strength'])
    t = g.n('ShaderNodeBsdfTransparent')
    add = g.n('ShaderNodeAddShader')
    g.link(t.outputs[0], add.inputs[0])
    g.link(e.outputs[0], add.inputs[1])
    return g.done(add.outputs[0])


def image_emission(name, image_path, strength=3.0, alpha_cut=True):
    """Emissive printed panel (lightbox sign) with transparent background."""
    g = G(name)
    uv = g.coords('UV')
    img = bpy.data.images.load(image_path, check_existing=True)
    tex = g.n('ShaderNodeTexImage')
    tex.image = img
    tex.interpolation = 'Cubic'
    g.link(uv, tex.inputs['Vector'])
    e = g.n('ShaderNodeEmission', Strength=strength)
    g.link(tex.outputs['Color'], e.inputs['Color'])
    if not alpha_cut:
        return g.done(e.outputs[0])
    t = g.n('ShaderNodeBsdfTransparent')
    mx = g.n('ShaderNodeMixShader')
    g.link(tex.outputs['Alpha'], mx.inputs[0])
    g.link(t.outputs[0], mx.inputs[1])
    g.link(e.outputs[0], mx.inputs[2])
    return g.done(mx.outputs[0])
