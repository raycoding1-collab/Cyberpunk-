"""Freeform architecture engine.

Towers are lofted from sculpted cross-sections that interpolate smoothly up
a spine: superelliptic plans with lobes (buttresses), twist, lean and
bulges. Facades (curtain walls, floor ribs, fins) follow the curved surface,
and parametric exoskeletons are generated as hexagonal lattices in the
surface's own parameter space, turned into structure with Blender's
Wireframe + Subdivision modifiers so the nodes flow organically."""

import math

import bpy
from mathutils import Vector

from .util import MeshBuilder

TAU = 2.0 * math.pi


def catmull(keys, t):
    """Smooth interpolation through (t, value) keys (values may be tuples)."""
    if t <= keys[0][0]:
        return keys[0][1]
    if t >= keys[-1][0]:
        return keys[-1][1]
    for i in range(len(keys) - 1):
        t0, t1 = keys[i][0], keys[i + 1][0]
        if t0 <= t <= t1:
            break
    p0 = keys[max(i - 1, 0)][1]
    p1 = keys[i][1]
    p2 = keys[i + 1][1]
    p3 = keys[min(i + 2, len(keys) - 1)][1]
    s = (t - t0) / max(t1 - t0, 1e-9)

    def cr(a, b, c, d):
        return 0.5 * ((2 * b) + (-a + c) * s + (2 * a - 5 * b + 4 * c - d) * s * s + (-a + 3 * b - 3 * c + d) * s * s * s)
    if isinstance(p1, (tuple, list)):
        return tuple(cr(a, b, c, d) for a, b, c, d in zip(p0, p1, p2, p3))
    return cr(p0, p1, p2, p3)


class Tower:
    """A sculpted tower: horizontal sections along z.

    profile: keys of (z, (a, b, n)) half-widths and superellipse exponent
    twist:   keys of (z, radians)
    lean:    keys of (z, (dx, dy))
    lobes:   (count, depth keys [(z, depth)], phase) radial buttresses
    """

    def __init__(self, cx, cy, height, profile, twist=None, lean=None, lobes=None, base_z=0.0):
        self.cx, self.cy = cx, cy
        self.h = height
        self.z0 = base_z
        self.profile = profile
        self.twist = twist or [(0.0, 0.0), (height, 0.0)]
        self.lean = lean or [(0.0, (0.0, 0.0)), (height, (0.0, 0.0))]
        self.lobes = lobes

    def section(self, z):
        a, b, n = catmull(self.profile, z)
        return max(a, 0.5), max(b, 0.5), max(n, 1.6)

    def point(self, th, z, offset=0.0):
        a, b, n = self.section(z)
        c, s = math.cos(th), math.sin(th)
        x = a * math.copysign(abs(c) ** (2.0 / n), c)
        y = b * math.copysign(abs(s) ** (2.0 / n), s)
        k = 1.0
        if self.lobes:
            cnt, depth_keys, ph = self.lobes
            d = catmull(depth_keys, z)
            k += d * (0.5 + 0.5 * math.cos(cnt * (th - ph)))
        x, y = x * k, y * k
        if offset:
            r = math.hypot(x, y) + 1e-6
            x, y = x * (1 + offset / r), y * (1 + offset / r)
        tw = catmull(self.twist, z)
        ct, st = math.cos(tw), math.sin(tw)
        x, y = x * ct - y * st, x * st + y * ct
        lx, ly = catmull(self.lean, z)
        return Vector((self.cx + lx + x, self.cy + ly + y, self.z0 + z))

    def normal(self, th, z):
        e = 1e-3
        p = self.point(th, z)
        du = self.point(th + e, z) - p
        dv = self.point(th, z + 0.5) - p
        n = du.cross(dv)
        if n.length < 1e-9:
            return Vector((math.cos(th), math.sin(th), 0.0))
        return n.normalized()

    # -- skin ---------------------------------------------------------------
    def skin(self, mb, mat, z_a, z_b, n_around=144, dz=3.0, offset=0.0):
        """Lofted surface between two heights. UV: u = metres around, v = z."""
        rows = max(2, int(math.ceil((z_b - z_a) / dz)))
        ths = [TAU * i / n_around for i in range(n_around)]
        base = mb.nv
        verts, uvs = [], []
        for r in range(rows + 1):
            z = z_a + (z_b - z_a) * r / rows
            pts = [self.point(t, z, offset) for t in ths]
            u = 0.0
            for i, p in enumerate(pts):
                if i:
                    u += (p - pts[i - 1]).length
                verts.append(tuple(p))
                uvs.append((u, self.z0 + z))
            # duplicate seam vertex so UVs don't wrap backwards
            u += (pts[0] - pts[-1]).length
            verts.append(tuple(pts[0]))
            uvs.append((u, self.z0 + z))
        w = n_around + 1
        faces = []
        for r in range(rows):
            for i in range(n_around):
                a = r * w + i
                faces.append((a, a + 1, a + 1 + w, a + w))
        mb.add(verts, faces, mat, uvs)
        return base

    def cap(self, mb, mat, z, offset=0.0, n_around=96, flip=False):
        pts = [tuple(self.point(TAU * i / n_around, z, offset)) for i in range(n_around)]
        mb.cap(pts, mat, flip=flip)

    def ribbon(self, mb, mat, z, height, out0, out1, n_around=144):
        """Horizontal band (slab edge / light line) following the plan."""
        ths = [TAU * i / n_around for i in range(n_around)]
        lo0 = [tuple(self.point(t, z, out0)) for t in ths]
        lo1 = [tuple(self.point(t, z, out1)) for t in ths]
        hi0 = [tuple(self.point(t, z + height, out0)) for t in ths]
        hi1 = [tuple(self.point(t, z + height, out1)) for t in ths]
        mb.ring_strip(lo1, hi1, mat)
        mb.ring_strip(hi0, hi1, mat) if False else None
        # top and underside
        mb.ring_strip(hi1, hi0, mat)
        mb.ring_strip(lo0, lo1, mat)

    def fins(self, mb, mat, count, z_a, z_b, depth=0.9, width=0.18, dz=4.0, phase=0.0):
        """Vertical fins that follow the surface (stepped per floor)."""
        z = z_a
        while z < z_b - 0.01:
            z1 = min(z_b, z + dz)
            for k in range(count):
                th = phase + TAU * k / count
                p0, p1 = self.point(th, z), self.point(th, z1)
                n0, n1 = self.normal(th, z), self.normal(th, z1)
                t0 = (self.point(th + 0.002, z) - p0).normalized()
                q = [p0 + n0 * 0.05 + t0 * width, p0 + n0 * depth + t0 * width, p0 + n0 * depth - t0 * width, p0 + n0 * 0.05 - t0 * width]
                q1 = [p1 + n1 * 0.05 + t0 * width, p1 + n1 * depth + t0 * width, p1 + n1 * depth - t0 * width, p1 + n1 * 0.05 - t0 * width]
                mb.ring_strip([tuple(v) for v in q], [tuple(v) for v in q1], mat)
            z = z1

    # -- exoskeleton --------------------------------------------------------
    def hex_lattice(self, name, z_a, z_b, cols=12, rows=None, offset=3.0, thickness=1.4, mats=(), col=None,
                    density=0.0, subdiv=1):
        """Hexagonal structural shell. `density` > 0 makes cells tighten with height."""
        rows = rows or int((z_b - z_a) / ((TAU * self.section(z_a)[0]) / cols * 0.9))

        def zmap(v):
            t = v / rows
            if density:
                t = (1 - math.exp(-density * t)) / (1 - math.exp(-density))
            return z_a + (z_b - z_a) * t

        idx = {}
        verts = []

        def vid(u, v):
            key = (round((u % cols) * 4) / 4, round(v * 4) / 4)
            if key not in idx:
                th = TAU * key[0] / cols
                z = zmap(key[1])
                p = self.point(th, z, offset)
                idx[key] = len(verts)
                verts.append(tuple(p))
            return idx[key]

        faces = []
        # pointy-top hexagons: width 1, row step 0.75 (in cell units)
        r = 0
        while r * 0.75 <= rows:
            v = r * 0.75
            for c in range(cols):
                u = c + 0.5 * (r % 2)
                hexv = [(u + 0.5, v - 0.25), (u + 0.5, v + 0.25), (u, v + 0.5), (u - 0.5, v + 0.25), (u - 0.5, v - 0.25), (u, v - 0.5)]
                if any(hv[1] < 0 or hv[1] > rows for hv in hexv):
                    continue
                faces.append(tuple(vid(*hv) for hv in hexv))
            r += 1
        me = bpy.data.meshes.new(name)
        me.from_pydata(verts, [], faces)
        me.update()
        for m in mats:
            me.materials.append(m)
        ob = bpy.data.objects.new(name, me)
        (col or bpy.context.scene.collection).objects.link(ob)
        wf = ob.modifiers.new('Structure', 'WIREFRAME')
        wf.thickness = thickness
        wf.use_even_offset = True
        wf.use_relative_offset = False
        wf.use_replace = True
        wf.use_boundary = True
        if subdiv:
            ss = ob.modifiers.new('Smooth', 'SUBSURF')
            ss.levels = subdiv
            ss.render_levels = subdiv
        return ob


def apply_modifiers(ob):
    """Bake modifiers into the mesh (keeps render-time cost low and lets
    later steps read the final geometry)."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    bpy.data.meshes.remove(old)
    return ob
