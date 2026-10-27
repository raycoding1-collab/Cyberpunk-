"""Signature details of the Capsule Spire.

Each piece replaces a primitive with a designed element: light currents that
run up the capsule spiral, spinal lift shafts with vertebrae and bead cabins,
tendon catwalks hung with lanterns, a lotus crown of cantilevered petals
whose tips project the koi, a wave canopy of curved lit ribs, perforated
kanji screens glowing on the podium, a raised black koi pond with
holographic lilies, steam vents, flowing light rails, and a Syd Mead-style
hover-car with articulated thruster nacelles."""

import math
import os

import bpy
from mathutils import Vector
from PIL import Image, ImageDraw, ImageFont

from . import materials as M
from .freeform import TAU
from .signs import FONTS, GEN
from .util import MeshBuilder, collection, rng

UP = Vector((0.0, 0.0, 1.0))


# ---------------------------------------------------------------------------
# geometry helpers
# ---------------------------------------------------------------------------

def sweep(mb, path, profile_fn, mat, closed=True, up=UP, caps=False):
    """Sweep a 2D profile (x = side, y = up) along a 3D path. UV u = metres along the path."""
    n = len(path)
    L = [0.0]
    for i in range(1, n):
        L.append(L[-1] + (path[i] - path[i - 1]).length)
    verts, uvs = [], []
    m = 0
    for i, p in enumerate(path):
        t = (path[min(i + 1, n - 1)] - path[max(i - 1, 0)]).normalized()
        s = up.cross(t)
        if s.length < 1e-5:
            s = Vector((1.0, 0.0, 0.0)).cross(t)
        s.normalize()
        u = t.cross(s)
        prof = profile_fn(i / (n - 1) if n > 1 else 0.0)
        m = len(prof)
        for j, (x, y) in enumerate(prof):
            verts.append(tuple(p + s * x + u * y))
            uvs.append((L[i], j / m))
    seg = m if closed else m - 1
    faces = []
    for i in range(n - 1):
        for j in range(seg):
            a, b = i * m + j, i * m + (j + 1) % m
            faces.append((a, b, (i + 1) * m + (j + 1) % m, (i + 1) * m + j))
    base = mb.nv
    mb.add(verts, faces, mat, uvs)
    if caps and closed:
        mb.cap([verts[j] for j in range(m)], mat, flip=True)
        mb.cap([verts[(n - 1) * m + j] for j in range(m)], mat)
    return base


def circle(r, k=10):
    return lambda t: [(r * math.cos(TAU * j / k), r * math.sin(TAU * j / k)) for j in range(k)]


def rect(w, h):
    return lambda t: [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]


def bezier(p0, p1, p2, p3, n=24):
    out = []
    for i in range(n + 1):
        t = i / n
        a = (1 - t) ** 3
        b = 3 * (1 - t) ** 2 * t
        c = 3 * (1 - t) * t * t
        d = t ** 3
        out.append(p0 * a + p1 * b + p2 * c + p3 * d)
    return out


def sphere(mb, c, r, mat, rings=10, seg=18):
    for i in range(rings):
        a0 = -math.pi / 2 + math.pi * i / rings
        a1 = -math.pi / 2 + math.pi * (i + 1) / rings
        r0 = [(c.x + r * math.cos(a0) * math.cos(TAU * j / seg), c.y + r * math.cos(a0) * math.sin(TAU * j / seg), c.z + r * math.sin(a0)) for j in range(seg)]
        r1 = [(c.x + r * math.cos(a1) * math.cos(TAU * j / seg), c.y + r * math.cos(a1) * math.sin(TAU * j / seg), c.z + r * math.sin(a1)) for j in range(seg)]
        mb.ring_strip(r0, r1, mat)


def ring_path(c, r, n=32):
    pts = [c + Vector((r * math.cos(TAU * j / n), r * math.sin(TAU * j / n), 0.0)) for j in range(n)]
    return pts + [pts[0]]


# ---------------------------------------------------------------------------
# materials
# ---------------------------------------------------------------------------

@M.cached
def pulse(name, color, base=2.5, peak=45.0, spacing=18.0, phase=0.0):
    """Emission with bright heads travelling along the strip (UV u = metres)."""
    g = M.G(name)
    uv = g.coords('UV')
    sep = g.n('ShaderNodeSeparateXYZ')
    g.link(uv, sep.inputs[0])
    f = g.math('FRACT', g.math('ADD', g.math('DIVIDE', sep.outputs['X'], spacing), phase))
    head = g.math('MULTIPLY', g.math('POWER', f, 14.0), peak)
    e = g.n('ShaderNodeEmission')
    e.inputs['Color'].default_value = (*color, 1)
    g.link(g.math('ADD', head, base), e.inputs['Strength'])
    return g.done(e.outputs[0])


@M.cached
def livery(name='CarLivery'):
    """Two-tone Syd Mead livery: lacquer red over graphite, cyan pinstripe, panel seams."""
    g = M.G(name)
    obj = g.coords('Object')
    sep = g.n('ShaderNodeSeparateXYZ')
    g.link(obj, sep.inputs[0])
    upper = g.math('GREATER_THAN', sep.outputs['Z'], 1.18)
    col = g.mix(upper, (0.03, 0.032, 0.036), (0.55, 0.02, 0.04))
    stripe = g.math('LESS_THAN', g.math('ABSOLUTE', g.math('SUBTRACT', sep.outputs['Z'], 1.18)), 0.018)
    seam_x = g.math('LESS_THAN', g.math('ABSOLUTE', g.math('SUBTRACT', g.math('FRACT', g.math('DIVIDE', sep.outputs['X'], 1.35)), 0.5)), 0.006)
    seam_z = g.math('LESS_THAN', g.math('ABSOLUTE', g.math('SUBTRACT', sep.outputs['Z'], 0.92)), 0.006)
    seams = g.math('MAXIMUM', seam_x, seam_z)
    col = g.mix(seams, col, (0.005, 0.005, 0.005))
    bump = g.n('ShaderNodeBump', Strength=0.6, Distance=0.004)
    g.link(g.math('MULTIPLY', seams, -1.0), bump.inputs['Height'])
    flake = g.noise(obj, 260.0, 2, 0.5)
    b = g.bsdf(**{'Base Color': col, 'Metallic': 0.7, 'Roughness': g.math('MULTIPLY_ADD', flake, 0.1, 0.16),
                  'Coat Weight': 1.0, 'Coat Roughness': 0.03, 'Normal': bump.outputs[0],
                  'Emission Color': (0.1, 0.85, 1.0), 'Emission Strength': g.math('MULTIPLY', stripe, 18.0)})
    return g.done(b.outputs[0])


@M.cached
def pond_water(name='PondWater'):
    g = M.G(name)
    obj = g.coords('Object')
    n = g.noise(obj, 2.5, 3, 0.5)
    rip = g.n('ShaderNodeTexWave', Scale=1.4, Distortion=6.0, Detail=3.0)
    rip.wave_type = 'RINGS'
    g.link(obj, rip.inputs['Vector'])
    bump = g.n('ShaderNodeBump', Strength=0.08, Distance=0.02)
    g.link(g.math('MULTIPLY_ADD', rip.outputs['Fac'], 0.5, n), bump.inputs['Height'])
    b = g.bsdf(**{'Base Color': (0.002, 0.002, 0.003), 'Roughness': 0.02, 'Normal': bump.outputs[0], 'Specular IOR Level': 0.8})
    return g.done(b.outputs[0])


@M.cached
def steam(name='Steam'):
    g = M.G(name)
    gen = g.coords('Generated')
    obj = g.coords('Object')
    n = g.noise(g.mapping(obj, (0.9, 0.9, 0.5)), 1.2, 6, 0.65)
    sep = g.n('ShaderNodeSeparateXYZ')
    g.link(gen, sep.inputs[0])
    fade = g.ramp(sep.outputs['Z'], [(0.0, (1, 1, 1)), (1.0, (0, 0, 0))])
    rad = g.math('SUBTRACT', 1.0, g.math('MULTIPLY', 2.0, g.math('SQRT', g.math('ADD', g.math('POWER', g.math('SUBTRACT', sep.outputs['X'], 0.5), 2.0), g.math('POWER', g.math('SUBTRACT', sep.outputs['Y'], 0.5), 2.0)))))
    sf = g.n('ShaderNodeSeparateColor')
    g.link(fade, sf.inputs[0])
    dens = g.math('MULTIPLY', g.math('MULTIPLY', g.math('MAXIMUM', g.math('SUBTRACT', n, 0.38), 0.0), sf.outputs[0]), g.math('MAXIMUM', rad, 0.0))
    v = g.n('ShaderNodeVolumePrincipled')
    v.inputs['Color'].default_value = (0.95, 0.85, 0.95, 1)
    v.inputs['Anisotropy'].default_value = 0.3
    g.link(g.math('MULTIPLY', dens, 2.6), v.inputs['Density'])
    g.link(v.outputs[0], g.out.inputs['Volume'])
    return g.m


def screen_texture(path, w_m, h_m, text_big, text_small, ppm=40, hole=0.32, seed=1):
    """Perforated metal screen with large kanji knocked out (alpha 0 = open)."""
    W, Hh = int(w_m * ppm), int(h_m * ppm)
    a = Image.new('L', (W, Hh), 255)
    d = ImageDraw.Draw(a)
    step = int(hole * ppm)
    for y in range(step // 2, Hh, step):
        off = (y // step % 2) * step // 2
        for x in range(step // 2 + off, W, step):
            r = step * 0.22
            d.ellipse((x - r, y - r, x + r, y + r), fill=0)
    fb = ImageFont.truetype(os.path.join(FONTS, 'DelaGothicOne-Regular.ttf'), int(Hh * 0.78))
    d.text((int(W * 0.05), Hh // 2), text_big, font=fb, fill=0, anchor='lm')
    fs = ImageFont.truetype(os.path.join(FONTS, 'Orbitron-Black.ttf'), int(Hh * 0.16))
    d.text((int(W * 0.95), int(Hh * 0.72)), text_small, font=fs, fill=0, anchor='rm')
    img = Image.merge('RGBA', (Image.new('L', (W, Hh), 40), Image.new('L', (W, Hh), 40), Image.new('L', (W, Hh), 44), a))
    img.save(path)
    return path


def cutout_metal(name, image_path):
    g = M.G(name)
    uv = g.coords('UV')
    img = bpy.data.images.load(image_path, check_existing=True)
    tex = g.n('ShaderNodeTexImage')
    tex.image = img
    tex.interpolation = 'Closest'
    g.link(uv, tex.inputs['Vector'])
    obj = g.coords('Object')
    n = g.noise(obj, 3.0, 5, 0.6)
    b = g.bsdf(**{'Base Color': g.mix(n, (0.03, 0.03, 0.035), (0.08, 0.075, 0.07)), 'Metallic': 0.85, 'Roughness': 0.42})
    t = g.n('ShaderNodeBsdfTransparent')
    mx = g.n('ShaderNodeMixShader')
    g.link(tex.outputs['Alpha'], mx.inputs[0])
    g.link(t.outputs[0], mx.inputs[1])
    g.link(b.outputs[0], mx.inputs[2])
    return g.done(mx.outputs[0])


@M.cached
def glow_panel(name='ScreenGlow'):
    g = M.G(name)
    obj = g.coords('Object')
    sep = g.n('ShaderNodeSeparateXYZ')
    g.link(obj, sep.inputs[0])
    n = g.noise(obj, 0.35, 4, 0.5)
    t = g.math('MULTIPLY_ADD', n, 0.4, g.math('DIVIDE', g.math('SUBTRACT', sep.outputs['Z'], 12.0), 12.0))
    col = g.ramp(t, [(0.15, (1.0, 0.45, 0.12)), (0.55, (1.0, 0.1, 0.45)), (0.95, (0.45, 0.15, 1.0))])
    e = g.n('ShaderNodeEmission', Strength=7.0)
    g.link(col, e.inputs['Color'])
    return g.done(e.outputs[0])


# ---------------------------------------------------------------------------
# tower pieces
# ---------------------------------------------------------------------------

def spiral_currents(col, T, z0, H, bands=3, pitch=64.0):
    """Light currents tracing the edges of the capsule bands, pulses running upward."""
    mb = MeshBuilder()
    mats = [pulse('CurrentCyan', (0.1, 0.85, 1.0), 2.0, 60.0, 22.0), pulse('CurrentMagenta', (1.0, 0.1, 0.5), 2.0, 60.0, 26.0, 0.4)]
    for k in range(bands):
        for e, mi in ((0.0, 0), (0.6, 1)):
            path = []
            z = z0 + 3.0
            while z < H - 6.0:
                th = TAU / bands * (k + e + z / pitch)
                path.append(T.point(th, z - z0, 0.7))
                z += 0.8
            sweep(mb, path, circle(0.13, 8), mi)
    return mb.to_object('SpiralCurrents', mats, col, smooth=True)


def spinal_shafts(col, T, angles, z0, H, seed=4):
    R = rng(seed)
    glass = M.clear_glass('SpineGlass', tint=(0.85, 0.95, 1.0), rough=0.04)
    bone = M.metal('SpineVertebra', base=(0.16, 0.15, 0.14), rough=0.28)
    dark = M.metal('SpineDark', base=(0.04, 0.04, 0.045), rough=0.35)
    under = M.emission('SpineGlowCyan', (0.1, 0.8, 1.0), 16.0)
    bead = M.emission('SpineBead', (1.0, 0.72, 0.42), 9.0)
    lantern = M.emission('CatwalkLantern', (1.0, 0.22, 0.08), 14.0)
    deck_m = M.metal('CatwalkDeck', base=(0.07, 0.065, 0.06), rough=0.45)
    beacon = M.emission('SpineBeacon', (1.0, 0.04, 0.02), 70.0)
    mats = [glass, bone, dark, under, bead, lantern, deck_m, beacon]
    mb = MeshBuilder()
    for sa in angles:
        p = T.point(sa, 70.0, 7.5)
        c0 = Vector((p.x, p.y, 0.0))
        inward = Vector((-p.x, -p.y, 0.0)).normalized()
        side = UP.cross(inward).normalized()
        ring = lambda r, z: [(c0.x + r * math.cos(TAU * j / 28), c0.y + r * math.sin(TAU * j / 28), z) for j in range(28)]
        mb.ring_strip(ring(2.25, 4.0), ring(2.25, H + 2.0), 0)
        z = 6.0
        i = 0
        while z < H:
            # vertebra: chunky ring + two spinous fins reaching for the core
            sweep(mb, ring_path(Vector((c0.x, c0.y, z)), 2.7, 32), rect(0.55, 0.36), 1)
            for sgn in (-1, 1):
                d = (inward * math.cos(0.5) + side * sgn * math.sin(0.5)).normalized()
                a = Vector((c0.x, c0.y, z)) + d * 2.85
                path = [a + d * (1.9 * t) + UP * (0.35 * t * t) for t in (0.0, 0.25, 0.5, 0.75, 1.0)]
                sweep(mb, path, lambda t: [(-0.12, -0.3 * (1 - t) - 0.04), (0.12, -0.3 * (1 - t) - 0.04), (0.12, 0.3 * (1 - t) + 0.04), (-0.12, 0.3 * (1 - t) + 0.04)], 1, caps=True)
            if i % 2 == 0:
                sweep(mb, ring_path(Vector((c0.x, c0.y, z - 0.22)), 2.7, 32), rect(0.12, 0.05), 3)
            z += 3.2
            i += 1
        # bead cabins
        for cz in (R.uniform(30, 85), R.uniform(105, 170)):
            sphere(mb, Vector((c0.x, c0.y, cz)), 1.55, 4)
            sweep(mb, ring_path(Vector((c0.x, c0.y, cz)), 1.6, 32), rect(0.25, 0.3), 2)
        # tendon catwalks hung with lanterns
        for zz in range(int(z0) + 12, int(H) - 6, 20):
            q = T.point(sa, zz - z0, 0.0)
            q = Vector((q.x, q.y, zz))
            c = Vector((c0.x, c0.y, zz)) + (q - Vector((c0.x, c0.y, zz))).normalized() * 2.4
            bow = (q - c).cross(UP).normalized()
            path = [c.lerp(q, s) - UP * (1.6 * math.sin(math.pi * s)) + bow * (0.9 * math.sin(math.pi * s)) for s in [k / 20 for k in range(21)]]
            deck = [(-0.85, 0.0), (0.85, 0.0), (0.85, 0.38), (0.74, 0.38), (0.74, 0.1), (-0.74, 0.1), (-0.74, 0.38), (-0.85, 0.38)]
            sweep(mb, path, lambda t: deck, 6)
            for sx in (-0.8, 0.8):
                rail = [pp + (path[min(k + 1, 20)] - path[max(k - 1, 0)]).cross(UP).normalized() * sx + UP * 1.1 for k, pp in enumerate(path)]
                sweep(mb, rail, circle(0.035, 6), 2)
            for k in range(2, 20, 4):
                hp = path[k] - UP * 0.75
                mb.beam(path[k], hp + UP * 0.25, 0.02, 0.02, 2)
                sphere(mb, hp, 0.24, 5, rings=6, seg=10)
        mb.box((c0.x - 0.35, c0.y - 0.35, H + 2.0), (c0.x + 0.35, c0.y + 0.35, H + 3.0), 7)
    return mb.to_object('SpinalShafts', mats, col, smooth=True)


def lotus_crown(col, T, z0, H, target, petals=8):
    """Cantilevered petals with lit edges; their tips carry projectors aimed at the koi."""
    dark = M.metal('PetalMetal', base=(0.06, 0.055, 0.06), rough=0.25)
    cyan = M.emission('PetalEdgeCyan', (0.1, 0.85, 1.0), 26.0)
    mag = M.emission('PetalEdgeMagenta', (1.0, 0.08, 0.45), 28.0)
    lens = M.emission('ProjectorLens', (0.6, 0.95, 1.0), 60.0)
    collar_glow = M.emission('CrownCollar', (1.0, 0.1, 0.45), 18.0)
    red = M.emission('NeedleBeacon', (1.0, 0.04, 0.02), 80.0)
    mats = [dark, cyan, mag, lens, collar_glow, red]
    mb = MeshBuilder()
    zc = H - 9.0
    sweep(mb, [T.point(TAU * j / 64, zc - z0, 0.4) for j in range(65)], rect(1.4, 1.2), 0)
    sweep(mb, [T.point(TAU * j / 64, zc - 0.9 - z0, 0.9) for j in range(65)], rect(0.15, 0.12), 4)
    tips = []
    for k in range(petals):
        a = TAU * k / petals + 0.2
        base = T.point(a, zc - z0, 0.0)
        out = Vector((base.x, base.y, 0.0)).normalized()
        p0 = Vector(base)
        pts = bezier(p0, p0 + out * 6 + UP * 1.5, p0 + out * 15 + UP * 7, p0 + out * 19 + UP * 21, 26)

        def width(t):
            return 3.4 * (1 - t) ** 0.55 + 0.25

        def lensp(t):
            w, th = width(t), 0.34 * (1 - t) + 0.07
            return [(w * math.cos(TAU * j / 12), th * math.sin(TAU * j / 12)) for j in range(12)]
        sweep(mb, pts, lensp, 0, caps=True)
        em = 1 if k % 2 else 2
        for sgn in (-1, 1):
            edge = []
            for i, pp in enumerate(pts):
                t = i / (len(pts) - 1)
                tan = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
                s = UP.cross(tan).normalized()
                edge.append(pp + s * sgn * (width(t) + 0.02))
            sweep(mb, edge, circle(0.07, 6), em)
        tip = pts[-1]
        tips.append(tip)
        sphere(mb, tip + UP * 0.3, 0.55, 3, rings=6, seg=12)
    # finned needle
    nr = lambda r, z: [(r * math.cos(TAU * j / 16), r * math.sin(TAU * j / 16), z) for j in range(16)]
    mb.ring_strip(nr(2.4, H), nr(0.2, H + 62.0), 0)
    for k in range(4):
        a = TAU * k / 4
        d = Vector((math.cos(a), math.sin(a), 0.0))
        t = Vector((-d.y, d.x, 0.0)) * 0.12
        v = [Vector((0, 0, H + 2)) + d * 2.0, Vector((0, 0, H + 2)) + d * 6.5, Vector((0, 0, H + 34)) + d * 0.6]
        verts = [tuple(p + t) for p in v] + [tuple(p - t) for p in v]
        mb.add(verts, [(0, 1, 2), (5, 4, 3), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)], 0)
        mb.beam(v[1], v[2], 0.1, 0.1, 1 if k % 2 else 2)
    for zb in (H + 36.0, H + 61.0):
        sphere(mb, Vector((0, 0, zb)), 0.6, 5, rings=6, seg=10)
    ob = mb.to_object('LotusCrown', mats, col, smooth=True)
    for i, tip in enumerate(tips):
        lt = bpy.data.lights.new(f'Projector{i}', 'SPOT')
        lt.energy = 9.0e4
        lt.color = (0.45, 0.9, 1.0)
        lt.spot_size = math.radians(9)
        lt.spot_blend = 0.5
        lt.shadow_soft_size = 0.3
        lo = bpy.data.objects.new(f'Projector{i}', lt)
        lo.location = tip + UP * 0.3
        lo.rotation_euler = (Vector(target) - lo.location).to_track_quat('-Z', 'Y').to_euler()
        col.objects.link(lo)
    return ob


# ---------------------------------------------------------------------------
# podium pieces
# ---------------------------------------------------------------------------

def canopy_wave(col, P=30.0):
    rib_m = M.metal('CanopyRib', base=(0.09, 0.07, 0.05), rough=0.3)
    lit = M.emission('CanopyRibLight', (1.0, 0.8, 0.58), 16.0)
    beam_m = M.metal('CanopyBeam', base=(0.04, 0.04, 0.045), rough=0.35)
    mb = MeshBuilder()
    faces = [(lambda s: Vector((s, -P, 6.4)), Vector((0, -1, 0))), (lambda s: Vector((P, s, 6.4)), Vector((1, 0, 0)))]
    for base_fn, outn in faces:
        s = -P - 4.0
        while s <= P + 4.0:
            d = 4.3 + 1.7 * math.sin(s * 0.19) + 0.6 * math.sin(s * 0.071 + 1.0)
            b = base_fn(s)
            path = [b + outn * (d * t) + UP * (-1.0 * t * t + 0.35 * math.sin(math.pi * t)) for t in [k / 12 for k in range(13)]]
            sweep(mb, path, lambda t: [(-0.06, -0.5 * (1 - 0.65 * t)), (0.06, -0.5 * (1 - 0.65 * t)), (0.06, 0.06), (-0.06, 0.06)], 0, caps=True)
            low = [pp - UP * (0.5 * (1 - 0.65 * (i / 12)) + 0.01) for i, pp in enumerate(path)]
            sweep(mb, low[1:], rect(0.05, 0.02), 1)
            s += 1.1
        e0, e1 = base_fn(-P - 4.0), base_fn(P + 4.0)
        mb.beam(e0 + outn * 0.3, e1 + outn * 0.3, 0.6, 0.7, 2)
    return mb.to_object('CanopyWave', [rib_m, lit, beam_m], col, smooth=True)


def kanji_screens(col, P=30.0):
    os.makedirs(GEN, exist_ok=True)
    faces = [  # (texture name, big, small, plane fn(u in -P..P, z) for the screen, glow offset dir)
        ('south', '蜂巣塔', 'CAPSULE SPIRE', lambda u, z, o: (u, -P - o, z)),
        ('east', '夢見る光', 'HACHISU-TO', lambda u, z, o: (P + o, u, z)),
        ('north', '雨の街', 'SECTOR 7', lambda u, z, o: (-u, P + o, z)),
        ('west', '光の巣', 'NEO KOWLOON', lambda u, z, o: (-P - o, -u, z)),
    ]
    mats = [cutout_metal(f'Screen_{n}', screen_texture(os.path.join(GEN, f'screen_{n}.png'), 60.0, 11.0, big, small))
            for n, big, small, _ in faces]
    mats += [glow_panel(), M.metal('ScreenFrame', base=(0.05, 0.05, 0.055), rough=0.3)]
    GLOW, FRAME = len(faces), len(faces) + 1
    mb = MeshBuilder()
    z0, z1 = 12.5, 23.5
    for i, (_, _, _, f) in enumerate(faces):
        q = lambda u, z, o: f(u, z, o)
        mb.add([q(-P, z0, 0.25), q(P, z0, 0.25), q(P, z1, 0.25), q(-P, z1, 0.25)], [(0, 1, 2, 3)], GLOW)
        mb.add([q(-P, z0, 1.1), q(P, z0, 1.1), q(P, z1, 1.1), q(-P, z1, 1.1)], [(0, 1, 2, 3)], i, [(0, 0), (1, 0), (1, 1), (0, 1)])
        for t in range(-6, 7):
            u = t * 5.0
            a, b = Vector(q(u - 0.1, z0, 0.25)), Vector(q(u + 0.1, z1, 1.3))
            mb.box(tuple(min(a[k], b[k]) for k in range(3)), tuple(max(a[k], b[k]) for k in range(3)), FRAME)
        for zz in (z0 - 0.2, z1):
            a, b = Vector(q(-P - 1.3, zz, 0.9)), Vector(q(P + 1.3, zz + 0.2, 1.3))
            mb.box(tuple(min(a[k], b[k]) for k in range(3)), tuple(max(a[k], b[k]) for k in range(3)), FRAME)
    return mb.to_object('KanjiScreens', mats, col)


# ---------------------------------------------------------------------------
# plaza pieces
# ---------------------------------------------------------------------------

def koi_pond(col, center=(-50.0, -12.0), a=12.0, b=18.0, seed=12):
    from .holo import koi_material, koi_mesh
    from .util import superellipse
    R = rng(seed)
    stone = M.concrete('PondStone', tone=0.1, panel=(1.2, 0.6), streaks=0.15)
    water = pond_water()
    pad = M.hologram('LilyPad', (0.15, 0.95, 0.75), 4.0, 3.0)
    flower = M.emission('LilyFlower', (1.0, 0.25, 0.62), 5.0)
    mats = [stone, water, pad, flower]
    mb = MeshBuilder()
    cx, cy = center
    out = superellipse(a, b, 2.6, 72, 0.3, cx, cy)
    path = [Vector((x, y, 0.5)) for x, y in out] + [Vector((out[0][0], out[0][1], 0.5))]
    sweep(mb, path, lambda t: [(-0.45, -0.32), (0.45, -0.32), (0.45, 0.18), (0.3, 0.32), (-0.45, 0.32)], 0)
    mb.cap([(x, y, 0.45) for x, y in superellipse(a - 0.3, b - 0.3, 2.6, 72, 0.3, cx, cy)], 1)
    for i in range(11):
        r = R.uniform(0.45, 1.1)
        px, py = cx + R.uniform(-a * 0.6, a * 0.6), cy + R.uniform(-b * 0.6, b * 0.6)
        notch = R.uniform(0, TAU)
        pts = [(px + r * math.cos(notch + 0.35 + (TAU - 0.7) * j / 20), py + r * math.sin(notch + 0.35 + (TAU - 0.7) * j / 20), 0.48) for j in range(21)]
        mb.cap(pts, 2)
        if i % 3 == 0:
            # lotus: two whorls of cupped petals, each a small lofted shell
            for whorl, (n, rr, hh, tilt) in enumerate(((8, 0.3, 0.32, 0.55), (6, 0.2, 0.36, 0.25))):
                for k in range(n):
                    ang = TAU * k / n + whorl * 0.4
                    d = Vector((math.cos(ang), math.sin(ang), 0.0))
                    side = UP.cross(d)
                    c = Vector((px, py, 0.5))
                    rows = []
                    for t in (0.0, 0.3, 0.6, 0.85, 1.0):
                        w = 0.1 * math.sin(math.pi * (0.15 + 0.7 * t)) + 0.01
                        ctr = c + d * (rr * t * (1 + tilt)) + UP * (hh * t)
                        rows.append([tuple(ctr + side * w * math.cos(math.pi * q / 4) + d * (0.03 * math.sin(math.pi * q / 4))) for q in range(5)])
                    for a in range(4):
                        mb.ring_strip(rows[a], rows[a + 1], 3, closed=False)
    ob = mb.to_object('KoiPond', mats, col, smooth=True)
    km = koi_material('PondKoi', 6.0)
    from mathutils import Matrix
    for i in range(4):
        k = koi_mesh(1.6, R.uniform(0, 3))
        kb = MeshBuilder()
        kb.merge(k, matrix=Matrix.Translation((cx + R.uniform(-5, 5), cy + R.uniform(-8, 8), 0.3)) @ Matrix.Rotation(R.uniform(0, TAU), 4, 'Z'))
        kb.to_object(f'PondKoi{i}', [km], col, smooth=True)
    return ob


def steam_vents(col, spots=((-14.0, -36.0), (24.0, -35.5), (34.5, 6.0))):
    grate = M.metal('VentGrate', base=(0.05, 0.05, 0.055), rough=0.5)
    vol = steam()
    for i, (x, y) in enumerate(spots):
        mb = MeshBuilder()
        mb.box((x - 1.0, y - 0.6, 0.12), (x + 1.0, y + 0.6, 0.2), 0, faces=(1, 1, 1, 1, 0, 0))
        for k in range(9):
            xx = x - 0.9 + k * 0.225
            mb.box((xx - 0.03, y - 0.55, 0.14), (xx + 0.03, y + 0.55, 0.2), 0)
        mb.to_object(f'VentGrate{i}', [grate], col)
        import bmesh
        me = bpy.data.meshes.new(f'Steam{i}')
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts:
            v.co.x *= 3.4
            v.co.y *= 3.4
            v.co.z = (v.co.z + 0.5) * 9.0
        bm.to_mesh(me)
        bm.free()
        me.materials.append(vol)
        ob = bpy.data.objects.new(f'Steam{i}', me)
        ob.location = (x, y, 0.15)
        col.objects.link(ob)


def flow_rails(col):
    mats = [pulse('FlowCyan', (0.1, 0.8, 1.0), 1.5, 30.0, 9.0)]
    mb = MeshBuilder()
    for k in range(6):
        y0 = -36.0 + k * 1.6
        path = []
        for i in range(60):
            t = i / 59
            x = -68.0 + t * 37.5
            y = y0 + 6.0 * t * t + 1.2 * math.sin(t * 7.0 + k * 0.6)
            path.append(Vector((x, y, 0.185)))
        sweep(mb, path, rect(0.09, 0.012), 0)
    return mb.to_object('FlowRails', mats, col)


# ---------------------------------------------------------------------------
# the hover-car
# ---------------------------------------------------------------------------

def hover_car(col, origin=(12.0, -41.5, 0.0), heading=0.0):
    from mathutils import Matrix
    body = livery()
    canopy = M.clear_glass('CarGlass', tint=(0.35, 0.4, 0.5), rough=0.03)
    trim = M.metal('CarTrim2', base=(0.02, 0.02, 0.022), rough=0.3)
    chrome = M.metal('CarChrome', base=(0.6, 0.6, 0.62), rough=0.12)
    head = M.emission('CarHead2', (0.85, 0.92, 1.0), 45.0)
    tail = M.emission('CarTail2', (1.0, 0.03, 0.05), 32.0)
    thr = M.emission('CarThrust', (0.1, 0.8, 1.0), 30.0)
    dash = M.emission('CarDash', (0.15, 0.9, 1.0), 6.0)
    seat = M.paint('CarSeat', (0.08, 0.05, 0.04), rough=0.6)
    mats = [body, canopy, trim, chrome, head, tail, thr, dash, seat]
    mb = MeshBuilder()
    L, W, Hh, hz = 5.6, 2.1, 1.0, 0.82

    def section(t):
        k = math.sin(math.pi * min(1.0, 0.06 + t * 0.94)) ** 0.42
        w = W / 2 * (0.5 + 0.5 * k) * (0.88 if t > 0.86 else 1.0)
        h = Hh / 2 * (0.32 + 0.68 * k) * (1.0 - 0.4 * max(0.0, t - 0.62))
        zc = hz + Hh / 2 - 0.28 * max(0.0, t - 0.68)
        return w, h, zc
    spine = [Vector((-L / 2 + L * i / 32, 0.0, 0.0)) for i in range(33)]
    rings = []
    for i, p in enumerate(spine):
        w, h, zc = section(i / 32)
        ring = []
        for j in range(36):
            a = TAU * j / 36
            c, s = math.cos(a), math.sin(a)
            y = w * math.copysign(abs(c) ** (2 / 3.4), c)
            z = h * math.copysign(abs(s) ** (2 / 3.4), s) * (0.72 if s < 0 else 1.0)
            ring.append((p.x, y, zc + z))
        rings.append(ring)
    for i in range(32):
        mb.ring_strip(rings[i], rings[i + 1], 0)
    mb.cap(rings[0], 0, flip=True)
    mb.cap(rings[-1], 0)
    # canopy bubble, with a glowing dash and two seats inside
    cr = []
    for i in range(17):
        t = i / 16
        x = -1.1 + 2.9 * t
        k = math.sin(math.pi * t) ** 0.65
        cr.append([(x, math.cos(math.pi * j / 18) * 0.8 * k, hz + Hh * 0.8 + math.sin(math.pi * j / 18) * 0.52 * k) for j in range(19)])
    for i in range(16):
        for j in range(18):
            mb.add([cr[i][j], cr[i][j + 1], cr[i + 1][j + 1], cr[i + 1][j]], [(0, 3, 2, 1)], 1)
    mb.box((1.15, -0.62, hz + Hh * 0.78), (1.35, 0.62, hz + Hh * 0.84), 7)
    for sy in (-0.34, 0.34):
        mb.box((-0.5, sy - 0.24, hz + Hh * 0.55), (0.1, sy + 0.24, hz + Hh * 0.75), 8)
        mb.box((-0.62, sy - 0.24, hz + Hh * 0.7), (-0.45, sy + 0.24, hz + Hh * 1.12), 8)
    # articulated thruster nacelles on swing arms
    for sx in (-1, 1):
        for sy in (-1, 1):
            hub = Vector((sx * L * 0.3, sy * (W / 2 - 0.1), hz + 0.45))
            pod = Vector((sx * L * 0.36, sy * (W / 2 + 0.55), hz + 0.05))
            sphere(mb, hub, 0.2, 3, rings=6, seg=10)
            arm = [hub.lerp(pod, t) + UP * (0.15 * math.sin(math.pi * t)) for t in (0, 0.25, 0.5, 0.75, 1.0)]
            sweep(mb, arm, lambda t: [(-0.09, -0.14 * (1 - 0.4 * t)), (0.09, -0.14 * (1 - 0.4 * t)), (0.09, 0.14 * (1 - 0.4 * t)), (-0.09, 0.14 * (1 - 0.4 * t))], 2, caps=True)
            nac = [pod + Vector((0.95 * (t - 0.5), 0.0, 0.0)) for t in [k / 10 for k in range(11)]]
            sweep(mb, nac, lambda t: [((0.34 * math.sin(math.pi * min(1, 0.08 + t * 0.92)) ** 0.5) * math.cos(TAU * j / 16), (0.3 * math.sin(math.pi * min(1, 0.08 + t * 0.92)) ** 0.5) * math.sin(TAU * j / 16)) for j in range(16)], 0, caps=True)
            sweep(mb, ring_path(pod - UP * 0.3, 0.24, 20), rect(0.05, 0.04), 6)
            mb.cap([(pod.x + 0.2 * math.cos(TAU * j / 16), pod.y + 0.2 * math.sin(TAU * j / 16), pod.z - 0.31) for j in range(16)], 6, flip=True)
            sweep(mb, ring_path(pod + Vector((0.47, 0, 0)), 0.2, 16), rect(0.03, 0.05), 3)
    # light blades following the nose and tail, tail fin
    nose = [Vector((L / 2 - 0.45 - 0.2 * abs(math.sin(a)), 0.86 * math.sin(a), hz + 0.46)) for a in [(-1.1 + 2.2 * k / 16) for k in range(17)]]
    sweep(mb, nose, rect(0.04, 0.06), 4)
    tailp = [Vector((-L / 2 + 0.12, 0.9 * math.sin(a), hz + 0.58)) for a in [(-1.2 + 2.4 * k / 16) for k in range(17)]]
    sweep(mb, tailp, rect(0.05, 0.05), 5)
    fin = [Vector((-L / 2 + 0.3, 0, hz + Hh * 0.95)), Vector((-L / 2 + 1.2, 0, hz + Hh * 0.95)), Vector((-L / 2 + 0.1, 0, hz + Hh * 1.55))]
    t = Vector((0, 0.04, 0))
    mb.add([tuple(p + t) for p in fin] + [tuple(p - t) for p in fin], [(0, 1, 2), (5, 4, 3), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)], 0)
    ob = mb.to_object('HoverCar', mats, col, smooth=True)
    ob.matrix_world = Matrix.Translation(origin) @ Matrix.Rotation(heading, 4, 'Z')
    for nm, off, colr, en, size in (('CarKey', (-2.5, 7.0, 5.5), (1.0, 0.35, 0.7), 2600.0, 4.0), ('CarRim', (5.0, -7.0, 4.5), (0.35, 0.8, 1.0), 2200.0, 3.0)):
        kl = bpy.data.lights.new(nm, 'AREA')
        kl.energy, kl.color, kl.size = en, colr, size
        ko = bpy.data.objects.new(nm, kl)
        ko.location = (origin[0] + off[0], origin[1] + off[1], off[2])
        ko.rotation_euler = (Vector(origin) + Vector((0, 0, 1.2)) - ko.location).to_track_quat('-Z', 'Y').to_euler()
        col.objects.link(ko)
    lt = bpy.data.lights.new('CarUnderglow', 'AREA')
    lt.energy = 900.0
    lt.color = (0.2, 0.6, 1.0)
    lt.size = 3.5
    lo = bpy.data.objects.new('CarUnderglow', lt)
    lo.location = (origin[0], origin[1], hz - 0.1)
    lo.rotation_euler = (math.pi, 0.0, 0.0)
    col.objects.link(lo)
    return ob
