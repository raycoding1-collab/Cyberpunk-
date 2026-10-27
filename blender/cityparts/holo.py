"""Holographic koi swimming through the canyon air.

Each koi is a lofted body (elliptical sections along an S-curved spine, the
undulation growing toward the tail), with a twin-lobed caudal fin, pectoral
fins, a dorsal ridge and barbels. The material is pure light: kohaku-style
patches, a projected wireframe grid, scanlines and a bright silhouette rim,
added over transparency so the fish glows inside the haze."""

import math

from mathutils import Matrix, Vector

from . import materials as M
from .util import MeshBuilder, collection


def koi_material(name, strength=5.0):
    g = M.G(name)
    uv = g.coords('UV')
    obj = g.coords('Object')
    sep = g.n('ShaderNodeSeparateXYZ')
    g.link(uv, sep.inputs[0])
    u, v = sep.outputs['X'], sep.outputs['Y']
    # kohaku patches (vermilion on white), drifting with the body
    pat = g.noise(g.mapping(obj, (0.06, 0.06, 0.06)), 1.0, 3, 0.55)
    patch = g.ramp(pat, [(0.5, (0.75, 0.92, 1.0)), (0.56, (1.0, 0.28, 0.05))], 'LINEAR')
    # projected wire grid along and around the body
    gu = g.math('LESS_THAN', g.math('ABSOLUTE', g.math('SUBTRACT', g.math('FRACT', g.math('MULTIPLY', u, 0.55)), 0.5)), 0.035)
    gv = g.math('LESS_THAN', g.math('ABSOLUTE', g.math('SUBTRACT', g.math('FRACT', g.math('MULTIPLY', v, 18.0)), 0.5)), 0.04)
    grid = g.math('MAXIMUM', gu, gv)
    sepo = g.n('ShaderNodeSeparateXYZ')
    g.link(obj, sepo.inputs[0])
    scan = g.math('MULTIPLY_ADD', g.math('SINE', g.math('MULTIPLY', sepo.outputs['Z'], 9.0)), 0.25, 0.85)
    lw = g.n('ShaderNodeLayerWeight', Blend=0.4)
    rim = g.math('POWER', lw.outputs['Facing'], 1.4)
    amt = g.math('MULTIPLY_ADD', rim, 1.4, 0.22)
    amt = g.math('MULTIPLY_ADD', grid, 0.9, amt)
    amt = g.math('MULTIPLY', amt, scan)
    e = g.n('ShaderNodeEmission')
    g.link(patch, e.inputs['Color'])
    g.link(g.math('MULTIPLY', amt, strength), e.inputs['Strength'])
    t = g.n('ShaderNodeBsdfTransparent')
    add = g.n('ShaderNodeAddShader')
    g.link(t.outputs[0], add.inputs[0])
    g.link(e.outputs[0], add.inputs[1])
    return g.done(add.outputs[0])


def koi_mesh(length=60.0, phase=0.0, amp=0.12, rings=80, sides=28):
    """Koi in local space: head at +X, tail toward -X, up = +Z."""
    mb = MeshBuilder()
    L = length
    R = L * 0.098

    def spine(s):
        # lateral S-curve, stronger toward the tail
        y = L * amp * math.sin(2 * math.pi * (0.75 * s) + phase) * (0.15 + s * s)
        z = L * 0.025 * math.sin(2 * math.pi * 0.5 * s + phase * 0.5)
        return Vector((L * (0.5 - s), y, z))

    def radius(s):
        if s < 0.12:
            return R * (0.55 + 0.45 * math.sin(math.pi / 2 * s / 0.12))
        return R * max(0.07, math.cos(math.pi / 2 * (s - 0.12) / 0.88) ** 1.25)

    def frame(s):
        p0, p1 = spine(max(0, s - 0.01)), spine(min(1, s + 0.01))
        t = (p0 - p1).normalized()
        up = Vector((0, 0, 1))
        side = up.cross(t).normalized()
        upv = t.cross(side).normalized()
        return spine(s), t, side, upv

    verts, uvs = [], []
    for i in range(rings + 1):
        s = i / rings
        p, t, side, upv = frame(s)
        r = radius(s)
        for k in range(sides):
            a = 2 * math.pi * k / sides
            # flatter belly, taller back
            hz = 1.18 if math.sin(a) > 0 else 0.95
            off = side * math.cos(a) * r * 0.82 + upv * math.sin(a) * r * hz
            verts.append(tuple(p + off))
            uvs.append((s * L, k / sides))
    faces = []
    for i in range(rings):
        for k in range(sides):
            a = i * sides + k
            b = i * sides + (k + 1) % sides
            c = (i + 1) * sides + (k + 1) % sides
            d = (i + 1) * sides + k
            faces.append((a, b, c, d))
    mb.add(verts, faces, 0, uvs)
    # nose cap
    mb.cap([verts[k] for k in range(sides)], 0, flip=True)

    def fin(points, uvscale=1.0):
        n = len(points)
        mb.add(points, [tuple(range(n))], 0, [(p[0] * uvscale, p[2] * uvscale) for p in points])

    # caudal fin: two flowing lobes
    p, t, side, upv = frame(1.0)
    for sgn in (1, -1):
        pts = [tuple(p)]
        for j in range(9):
            a = j / 8
            reach = L * (0.26 + 0.1 * math.sin(math.pi * a))
            sweep = sgn * (0.15 + 0.85 * a) * L * 0.2
            q = p - t * reach * (0.6 + 0.4 * math.sin(math.pi * a)) + upv * sweep + side * L * 0.05 * math.sin(phase + a * 3)
            pts.append(tuple(q))
        fin(pts)
    # pectoral fins
    for sgn in (1, -1):
        p, t, side, upv = frame(0.22)
        base = p + side * sgn * radius(0.22) * 0.75 - upv * radius(0.22) * 0.5
        pts = [tuple(base), tuple(base + t * L * 0.05), tuple(base + side * sgn * L * 0.17 - t * L * 0.08 - upv * L * 0.05),
               tuple(base + side * sgn * L * 0.12 - t * L * 0.16 - upv * L * 0.03), tuple(base - t * L * 0.07)]
        fin(pts)
    # dorsal ridge
    pts = []
    for j in range(12):
        s = 0.28 + j * 0.035
        p, t, side, upv = frame(s)
        pts.append(tuple(p + upv * radius(s) * 1.15))
    for j in range(11, -1, -1):
        s = 0.28 + j * 0.035
        p, t, side, upv = frame(s)
        hgt = math.sin(math.pi * j / 11) * L * 0.045
        pts.append(tuple(p + upv * (radius(s) * 1.15 + hgt) - t * L * 0.015))
    fin(pts)
    # barbels
    p, t, side, upv = frame(0.0)
    for sgn in (1, -1):
        a = p + t * L * 0.01 + side * sgn * R * 0.3 - upv * R * 0.25
        b = a + t * L * 0.05 + side * sgn * L * 0.03 - upv * L * 0.03
        mb.beam(a, b, 0.12, 0.12, 0)
    return mb


def build():
    col = collection('Holograms')
    mat = koi_material('KoiHolo', 5.0)
    mat2 = koi_material('KoiHolo2', 4.0)
    # (length, location, heading deg, pitch deg, phase, material)
    fish = [
        (74.0, (8.0, 125.0, 96.0), 200.0, 6.0, 0.3, mat),
        (48.0, (-3.0, 345.0, 150.0), 235.0, -4.0, 2.1, mat2),
    ]
    for i, (L, loc, head, pitch, ph, m) in enumerate(fish):
        mb = koi_mesh(L, ph)
        rot = Matrix.Rotation(math.radians(head), 4, 'Z') @ Matrix.Rotation(math.radians(pitch), 4, 'Y')
        out = MeshBuilder()
        out.merge(mb, matrix=Matrix.Translation(loc) @ rot)
        out.to_object(f'Koi{i}', [m], col, smooth=True)
    return col
