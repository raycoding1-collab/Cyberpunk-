"""Signage: 3D neon lettering, blade signs on the Hive pylons, and the poster
artwork for the large LED media walls (generated with Pillow)."""

import math
import os

import bpy
from mathutils import Matrix, Vector
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import materials as M
from .util import MeshBuilder, collection

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FONTS = os.path.join(ROOT, 'assets', 'fonts')
GEN = os.path.join(ROOT, 'assets', 'generated')


def font(name):
    path = os.path.join(FONTS, name)
    return bpy.data.fonts.load(path, check_existing=True)


def text_object(text, fontfile, size, name, col, mat, location=(0, 0, 0), rotation=(0, 0, 0),
                extrude=0.15, bevel=0.03, align='CENTER', vertical=False, spacing=1.0):
    """Real 3D lettering converted to a mesh (so it renders as geometry)."""
    cu = bpy.data.curves.new(name, 'FONT')
    cu.body = text if not vertical else '\n'.join(text)
    cu.font = font(fontfile)
    cu.size = size
    cu.extrude = extrude
    cu.bevel_depth = bevel
    cu.bevel_resolution = 2
    cu.align_x = align
    cu.align_y = 'CENTER'
    cu.space_line = 0.92 if vertical else 1.0
    cu.space_character = spacing
    tmp = bpy.data.objects.new(name + '_tmp', cu)
    col.objects.link(tmp)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    bpy.data.objects.remove(tmp, do_unlink=True)
    me.materials.clear()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    ob.location = location
    ob.rotation_euler = rotation
    col.objects.link(ob)
    return ob


def tube_outline(mb, pts, radius, mat, closed=True, sides=8):
    """Neon tube along a polyline (list of xyz)."""
    n = len(pts)
    segs = n if closed else n - 1
    for i in range(segs):
        a, b = Vector(pts[i]), Vector(pts[(i + 1) % n])
        d = b - a
        L = d.length
        if L < 1e-6:
            continue
        x = d / L
        up = Vector((0, 0, 1)) if abs(x.z) < 0.9 else Vector((1, 0, 0))
        y = up.cross(x).normalized()
        z = x.cross(y)
        ring0, ring1 = [], []
        for k in range(sides):
            t = 2 * math.pi * k / sides
            off = y * math.cos(t) * radius + z * math.sin(t) * radius
            ring0.append(tuple(a + off))
            ring1.append(tuple(b + off))
        mb.ring_strip(ring0, ring1, mat)


# ---------------------------------------------------------------------------
# Generated artwork
# ---------------------------------------------------------------------------

def _f(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), size)


def _vgrad(w, h, stops):
    img = Image.new('RGB', (w, h))
    px = img.load()
    for y in range(h):
        t = y / (h - 1)
        for i in range(len(stops) - 1):
            if stops[i][0] <= t <= stops[i + 1][0]:
                a, b = stops[i], stops[i + 1]
                k = (t - a[0]) / max(1e-6, b[0] - a[0])
                c = tuple(int(a[1][j] + (b[1][j] - a[1][j]) * k) for j in range(3))
                break
        for x in range(w):
            px[x, y] = c
    return img


def _seigaiha(d, x0, y0, w, h, r, color, width=3):
    """Traditional overlapping-wave pattern."""
    rows = int(h / (r * 0.5)) + 2
    cols = int(w / (r * 2)) + 2
    for j in range(rows):
        y = y0 + j * r * 0.5
        off = (j % 2) * r
        for i in range(-1, cols):
            x = x0 + i * 2 * r + off
            for k in range(4):
                rr = r * (1 - k * 0.24)
                d.arc((x - rr, y - rr, x + rr, y + rr), 180, 360, fill=color, width=width)


def poster_dream(path, w=1536, h=2048):
    """Portrait ad for the Monolith media wall: a cut red sun over seigaiha
    waves, a column of calligraphy and the YUREI brand."""
    img = _vgrad(w, h, [(0, (8, 3, 26)), (0.38, (46, 6, 74)), (0.62, (150, 14, 92)), (0.8, (40, 4, 60)), (1.0, (6, 2, 18))])
    # sun glow
    glow = Image.new('RGB', (w, h), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    cx, cy, r = int(w * 0.44), int(h * 0.47), int(w * 0.34)
    gd.ellipse((cx - r * 1.25, cy - r * 1.25, cx + r * 1.25, cy + r * 1.25), fill=(255, 40, 90))
    glow = glow.filter(ImageFilter.GaussianBlur(90))
    img = Image.fromarray(__import__('numpy').clip(__import__('numpy').asarray(img, dtype='int32') + __import__('numpy').asarray(glow, dtype='int32') * 0.8, 0, 255).astype('uint8'))
    d = ImageDraw.Draw(img)
    for yy in range(cy - r, cy + r):
        dy = yy - cy
        half = int(math.sqrt(max(0, r * r - dy * dy)))
        t = (yy - (cy - r)) / (2 * r)
        col = (255, int(215 - 175 * t), int(70 + 40 * t))
        band = 10 + 26 * max(0.0, t - 0.5)
        cut = t > 0.5 and ((yy - cy) % int(band * 2)) < band * (t - 0.45) * 1.6
        if not cut:
            d.line((cx - half, yy, cx + half, yy), fill=col)
    # waves across the lower third
    wave = Image.new('RGB', (w, int(h * 0.36)), (6, 10, 40))
    wd = ImageDraw.Draw(wave)
    _seigaiha(wd, 0, 0, w, wave.size[1], 64, (40, 220, 255), 4)
    img.paste(wave, (0, int(h * 0.64)))
    d = ImageDraw.Draw(img)
    d.rectangle((0, int(h * 0.64) - 6, w, int(h * 0.64)), fill=(255, 255, 255))
    # calligraphy column
    fk = _f('YujiSyuku-Regular.ttf', int(w * 0.16))
    for i, ch in enumerate('夢を見る'):
        x, y = int(w * 0.85), int(h * 0.1 + i * w * 0.18)
        d.text((x + 6, y + 6), ch, font=fk, fill=(30, 0, 30), anchor='mm')
        d.text((x, y), ch, font=fk, fill=(255, 255, 255), anchor='mm')
    # seal stamp
    d.rectangle((int(w * 0.79), int(h * 0.56), int(w * 0.91), int(h * 0.56) + int(w * 0.12)), fill=(220, 20, 40))
    fs2 = _f('DelaGothicOne-Regular.ttf', int(w * 0.05))
    d.text((int(w * 0.85), int(h * 0.56) + int(w * 0.06)), '影森', font=fs2, fill=(255, 235, 235), anchor='mm')
    fb = _f('Orbitron-Black.ttf', int(w * 0.15))
    d.text((int(w * 0.40), int(h * 0.09)), 'YUREI', font=fb, fill=(255, 245, 252), anchor='mm')
    fs = _f('Rajdhani-Bold.ttf', int(w * 0.055))
    d.text((int(w * 0.40), int(h * 0.165)), 'DREAM IN COLOR', font=fs, fill=(255, 130, 200), anchor='mm')
    fsm = _f('BebasNeue-Regular.ttf', int(w * 0.048))
    d.rectangle((0, int(h * 0.93), w, h), fill=(8, 2, 20))
    d.text((int(w * 0.42), int(h * 0.965)), 'NEURAL SLEEP   ·   8K LUCID   ·', font=fsm, fill=(255, 220, 240), anchor='mm')
    d.text((int(w * 0.83), int(h * 0.965)), '影森重工', font=_f('DelaGothicOne-Regular.ttf', int(w * 0.04)), fill=(255, 220, 240), anchor='mm')
    img.save(path)
    return path


def poster_eye(path, w=1024, h=1536):
    """Tall ad: a synthetic iris, MIRAI optics."""
    img = _vgrad(w, h, [(0, (2, 8, 20)), (1.0, (0, 2, 6))])
    d = ImageDraw.Draw(img)
    cx, cy, s = w // 2, int(h * 0.42), int(w * 0.42)
    eye = [(cx + s * 1.1 * math.cos(t), cy + s * 0.55 * math.sin(t) * (1 if math.sin(t) > 0 else 0.9)) for t in [i * 2 * math.pi / 120 for i in range(120)]]
    d.polygon(eye, fill=(225, 232, 240))
    mask = Image.new('L', (w, h), 0)
    ImageDraw.Draw(mask).polygon(eye, fill=255)
    iris = Image.new('RGB', (w, h), (0, 0, 0))
    di = ImageDraw.Draw(iris)
    ir = int(s * 0.5)
    for k in range(ir, 0, -1):
        t = k / ir
        col = (int(10 + 20 * t), int(80 + 160 * (1 - t) ** 0.5), int(200 + 55 * (1 - t)))
        di.ellipse((cx - k, cy - k, cx + k, cy + k), fill=col)
    for i in range(120):
        a = i / 120 * 2 * math.pi
        di.line((cx + math.cos(a) * ir * 0.3, cy + math.sin(a) * ir * 0.3, cx + math.cos(a) * ir, cy + math.sin(a) * ir), fill=(140, 255, 255), width=2)
    di.ellipse((cx - ir * 0.3, cy - ir * 0.3, cx + ir * 0.3, cy + ir * 0.3), fill=(0, 0, 0))
    di.ellipse((cx - ir * 0.45, cy - ir * 0.5, cx - ir * 0.2, cy - ir * 0.25), fill=(255, 255, 255))
    circ = Image.new('L', (w, h), 0)
    ImageDraw.Draw(circ).ellipse((cx - ir, cy - ir, cx + ir, cy + ir), fill=255)
    img.paste(iris, (0, 0), Image.composite(circ, Image.new('L', (w, h), 0), mask))
    d = ImageDraw.Draw(img)
    d.line(eye[:61], fill=(255, 40, 140), width=10)
    fb = _f('Orbitron-Black.ttf', int(w * 0.16))
    d.text((cx, int(h * 0.74)), 'MIRAI', font=fb, fill=(255, 255, 255), anchor='mm')
    fs = _f('Rajdhani-Bold.ttf', int(w * 0.06))
    d.text((cx, int(h * 0.81)), 'SEE MORE THAN HUMAN', font=fs, fill=(40, 230, 255), anchor='mm')
    fk = _f('DelaGothicOne-Regular.ttf', int(w * 0.09))
    d.text((cx, int(h * 0.89)), '義眼', font=fk, fill=(255, 40, 140), anchor='mm')
    img.save(path)
    return path


def ensure_art():
    os.makedirs(GEN, exist_ok=True)
    arts = {
        'dream': os.path.join(GEN, 'poster_dream.png'),
        'eye': os.path.join(GEN, 'poster_eye.png'),
    }
    poster_dream(arts['dream'])
    poster_eye(arts['eye'])
    return arts


# ---------------------------------------------------------------------------
# Blade signs mounted on the Hive pylons
# ---------------------------------------------------------------------------

BLADES = [
    # (pylon y, bottom z, text, colour, side)
    (46.0, 30.0, '蜂巣', (1.0, 0.08, 0.42), -1),
    (98.0, 70.0, '電脳市場', (0.1, 0.8, 1.0), -1),
    (150.0, 24.0, '義体', (1.0, 0.45, 0.06), -1),
    (202.0, 52.0, '夢', (0.65, 0.25, 1.0), -1),
    (98.0, 150.0, '九龍', (1.0, 0.15, 0.2), 1),
]


def build_blades():
    col = collection('Signs')
    panel = M.metal('BladePanel', base=(0.02, 0.02, 0.025), rough=0.4)
    for i, (cy, z0, text, color, side) in enumerate(BLADES):
        n = len(text)
        size = 7.5 if n <= 2 else 5.6
        hgt = n * size * 0.98 + 4.0
        neon = M.neon(f'BladeNeon{i}', color, 16.0)
        glyph = M.emission(f'BladeGlyph{i}', color, 1.6)
        # dark panel perpendicular to the canyon face, facing down the street (-y)
        x0, x1 = -18.6, -10.2
        y = cy + side * 7.4
        mb = MeshBuilder()
        mb.box((x0, y - 0.35, z0), (x1, y + 0.35, z0 + hgt), 0)
        # brackets into the pylon
        for zz in (z0 + 1.0, z0 + hgt - 1.0):
            mb.box((-19.2, y - 0.2, zz - 0.25), (x0, y + 0.2, zz + 0.25), 0)
        # neon border tube on both faces
        for f in (-1, 1):
            yy = y + f * 0.42
            pts = [(x0 + 0.5, yy, z0 + 0.5), (x1 - 0.5, yy, z0 + 0.5), (x1 - 0.5, yy, z0 + hgt - 0.5), (x0 + 0.5, yy, z0 + hgt - 0.5)]
            tube_outline(mb, pts, 0.07, 1)
        ob = mb.to_object(f'Blade{i}', [panel, neon], col)
        # characters on both faces
        cxp = (x0 + x1) / 2
        for f in (-1, 1):
            rot = (math.pi / 2, 0, 0 if f < 0 else math.pi)
            text_object(text, 'DelaGothicOne-Regular.ttf', size, f'BladeText{i}{f}', col, glyph,
                        location=(cxp, y + f * 0.45, z0 + hgt / 2), rotation=rot, extrude=0.06, bevel=0.02, vertical=True)
    return col


def build_media_tower(art):
    """Slender steel mast on the plaza carrying a double-sided LED panel."""
    col = collection('Signs')
    steel = M.metal('MastSteel', base=(0.06, 0.06, 0.065), rough=0.3)
    w, h, z0 = 15.0, 22.5, 34.0
    scr = M.led_screen('EyeScreen', art['eye'], strength=2.6, pixel_pitch=0.06, size=(w, h))
    rim = M.emission('MastRim', (0.1, 0.85, 1.0), 12.0)
    x, y = 36.0, 112.0
    mb = MeshBuilder()
    mb.box((x - 0.9, y - 0.9, 0.0), (x + 0.9, y + 0.9, z0 + h + 14.0), 0)
    mb.box((x - w / 2 - 0.6, y - 0.6, z0 - 0.6), (x + w / 2 + 0.6, y + 0.6, z0 + h + 0.6), 0)
    for sgn in (-1, 1):
        yy = y + sgn * 0.62
        q = MeshBuilder()
        quad = [(x - w / 2, yy, z0), (x + w / 2, yy, z0), (x + w / 2, yy, z0 + h), (x - w / 2, yy, z0 + h)]
        uvq = [(0, 0), (1, 0), (1, 1), (0, 1)]
        if sgn > 0:
            quad = [quad[1], quad[0], quad[3], quad[2]]
        q.add(quad, [(0, 1, 2, 3)], 0, uvq)
        mb.merge(q, mat_offset=1)
        for zz in (z0 - 0.7, z0 + h + 0.5):
            mb.box((x - w / 2 - 0.6, yy - 0.05 * sgn, zz), (x + w / 2 + 0.6, yy + 0.05 * sgn, zz + 0.2), 2)
    mb.box((x - 0.25, y - 0.25, z0 + h + 14.0), (x + 0.25, y + 0.25, z0 + h + 15.0), 2)
    return mb.to_object('MediaTower', [steel, scr, rim], col)


def build_roof_sign():
    """Giant rooftop kanji on a steel truss above the Hive, facing the canyon."""
    col = collection('Signs')
    steel = M.metal('TrussSteel', base=(0.05, 0.05, 0.055), rough=0.35)
    red = M.neon('HiveRoofNeon', (1.0, 0.1, 0.18), 10.0)
    x, y0, z0 = -60.0, 108.0, 236.0
    mb = MeshBuilder()
    for yy in (y0 - 22, y0, y0 + 22):
        mb.beam((x - 3, yy, z0), (x, yy, z0 + 30), 0.5, 0.5, 0)
        mb.beam((x - 8, yy, z0), (x - 3, yy, z0 + 30), 0.4, 0.4, 0)
    for zz in (z0 + 2, z0 + 15, z0 + 28):
        mb.beam((x - 0.5, y0 - 26, zz), (x - 0.5, y0 + 26, zz), 0.4, 0.4, 0)
    mb.to_object('HiveRoofTruss', [steel], col)
    text_object('蜂巣', 'DelaGothicOne-Regular.ttf', 24.0, 'HiveRoofKanji', col, red,
                location=(x + 0.4, y0, z0 + 15.5), rotation=(math.pi / 2, 0, math.pi / 2), extrude=0.6, bevel=0.12, spacing=1.05)


def build():
    art = ensure_art()
    build_blades()
    build_roof_sign()
