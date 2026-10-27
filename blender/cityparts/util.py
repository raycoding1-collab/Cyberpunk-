"""Mesh construction helpers: accumulate geometry in numpy-friendly lists,
then emit one Blender object per logical part (one draw/BVH entry)."""

import math
import random

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector


def rng(seed):
    return random.Random(seed)


def collection(name, parent=None):
    col = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    par = parent or bpy.context.scene.collection
    if col.name not in [c.name for c in par.children]:
        par.children.link(col)
    return col


class MeshBuilder:
    """Collects polygons with per-face material slots and per-vertex UVs."""

    def __init__(self):
        self.v = []
        self.f = []
        self.mi = []
        self.uv = []

    @property
    def nv(self):
        return len(self.v)

    def add(self, verts, faces, mat=0, uvs=None):
        o = len(self.v)
        self.v.extend([tuple(p) for p in verts])
        self.f.extend([tuple(i + o for i in face) for face in faces])
        self.mi.extend([mat] * len(faces))
        if uvs is None:
            self.uv.extend([(0.0, 0.0)] * len(verts))
        else:
            self.uv.extend([tuple(u) for u in uvs])

    # -- primitives -------------------------------------------------------
    def box(self, mn, mx, mat=0, matrix=None, faces=(1, 1, 1, 1, 1, 1), uv_scale=1.0):
        """Axis-aligned box from min/max corners (optionally transformed).
        faces toggles -x,+x,-y,+y,-z,+z. UVs are metric (u along face, v up)."""
        x0, y0, z0 = mn
        x1, y1, z1 = mx
        c = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
             (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        if matrix is not None:
            c = [tuple(matrix @ Vector(p)) for p in c]
        # corners listed bottom-left, bottom-right, top-right, top-left as seen
        # from outside, so normals point outward and u runs left-to-right
        quads = [
            ((3, 0, 4, 7), (y1 - y0, z1 - z0)),  # -x
            ((1, 2, 6, 5), (y1 - y0, z1 - z0)),  # +x
            ((0, 1, 5, 4), (x1 - x0, z1 - z0)),  # -y
            ((2, 3, 7, 6), (x1 - x0, z1 - z0)),  # +y
            ((0, 3, 2, 1), (x1 - x0, y1 - y0)),  # -z
            ((4, 5, 6, 7), (x1 - x0, y1 - y0)),  # +z
        ]
        for on, (q, (w, h)) in zip(faces, quads):
            if not on:
                continue
            verts = [c[i] for i in q]
            s = uv_scale
            self.add(verts, [(0, 1, 2, 3)], mat, [(0, 0), (w * s, 0), (w * s, h * s), (0, h * s)])

    def box_c(self, center, size, mat=0, rot_z=0.0, **kw):
        cx, cy, cz = center
        sx, sy, sz = size
        m = Matrix.Translation((cx, cy, cz)) @ Matrix.Rotation(rot_z, 4, 'Z')
        self.box((-sx / 2, -sy / 2, -sz / 2), (sx / 2, sy / 2, sz / 2), mat, matrix=m, **kw)

    def beam(self, p0, p1, w, h, mat=0, up=(0, 0, 1)):
        """Rectangular beam between two points; w across, h along `up`."""
        p0, p1 = Vector(p0), Vector(p1)
        d = p1 - p0
        L = d.length
        if L < 1e-6:
            return
        x = d / L
        upv = Vector(up)
        if abs(x.dot(upv)) > 0.99:
            upv = Vector((1, 0, 0))
        y = upv.cross(x).normalized()
        z = x.cross(y).normalized()
        m = Matrix((
            (x.x, y.x, z.x, p0.x),
            (x.y, y.y, z.y, p0.y),
            (x.z, y.z, z.z, p0.z),
            (0, 0, 0, 1)))
        self.box((0, -w / 2, -h / 2), (L, w / 2, h / 2), mat, matrix=m)

    def ring_strip(self, pts_bottom, pts_top, mat=0, closed=True, u_metric=True):
        """Wall between two matching polylines (lists of xyz). UV u = arc length."""
        n = len(pts_bottom)
        o = len(self.v)
        verts, uvs = [], []
        u = 0.0
        for i in range(n):
            if i > 0:
                u += (Vector(pts_bottom[i]) - Vector(pts_bottom[i - 1])).length
            verts.append(pts_bottom[i])
            uvs.append((u, pts_bottom[i][2]))
        u = 0.0
        for i in range(n):
            if i > 0:
                u += (Vector(pts_top[i]) - Vector(pts_top[i - 1])).length
            verts.append(pts_top[i])
            uvs.append((u, pts_top[i][2]))
        faces = []
        m = n if closed else n - 1
        for i in range(m):
            j = (i + 1) % n
            faces.append((i, j, n + j, n + i))
        self.add(verts, faces, mat, uvs)
        return o

    def cap(self, pts, mat=0, flip=False):
        """Fan-triangulated cap (convex polygon)."""
        n = len(pts)
        c = tuple(sum(p[k] for p in pts) / n for k in range(3))
        verts = [c] + list(pts)
        faces = []
        for i in range(n):
            a, b = 1 + i, 1 + (i + 1) % n
            faces.append((0, b, a) if flip else (0, a, b))
        self.add(verts, faces, mat, [(p[0], p[1]) for p in verts])

    def extrude_polygon(self, pts2d, z0, z1, mat_side=0, mat_cap=0, caps=(True, True)):
        bot = [(x, y, z0) for x, y in pts2d]
        top = [(x, y, z1) for x, y in pts2d]
        self.ring_strip(bot, top, mat_side)
        if caps[0]:
            self.cap(bot, mat_cap, flip=True)
        if caps[1]:
            self.cap(top, mat_cap)

    def merge(self, other, matrix=None, mat_offset=0):
        o = len(self.v)
        if matrix is None:
            self.v.extend(other.v)
        else:
            self.v.extend([tuple(matrix @ Vector(p)) for p in other.v])
        self.f.extend([tuple(i + o for i in f) for f in other.f])
        self.mi.extend([m + mat_offset for m in other.mi])
        self.uv.extend(other.uv)

    # -- output -----------------------------------------------------------
    def to_mesh(self, name):
        me = bpy.data.meshes.new(name)
        if not self.v:
            return me
        verts = np.asarray(self.v, dtype=np.float32)
        me.vertices.add(len(verts))
        me.vertices.foreach_set('co', verts.ravel())
        sizes = np.fromiter((len(f) for f in self.f), dtype=np.int32, count=len(self.f))
        starts = np.zeros(len(sizes), dtype=np.int32)
        starts[1:] = np.cumsum(sizes)[:-1]
        loops = np.fromiter((i for f in self.f for i in f), dtype=np.int32)
        me.loops.add(len(loops))
        me.loops.foreach_set('vertex_index', loops)
        me.polygons.add(len(self.f))
        me.polygons.foreach_set('loop_start', starts)
        me.polygons.foreach_set('material_index', np.asarray(self.mi, dtype=np.int32))
        uvl = me.uv_layers.new(name='UVMap')
        uva = np.asarray(self.uv, dtype=np.float32)[loops]
        uvl.data.foreach_set('uv', uva.ravel())
        me.update(calc_edges=True)
        me.validate(clean_customdata=False)
        return me

    def to_object(self, name, materials, col=None, smooth=False):
        me = self.to_mesh(name)
        for m in materials:
            me.materials.append(m)
        if smooth:
            me.shade_smooth()
        ob = bpy.data.objects.new(name, me)
        (col or bpy.context.scene.collection).objects.link(ob)
        return ob


def instance(mesh_or_obj, name, location, rotation=(0, 0, 0), scale=(1, 1, 1), col=None):
    me = mesh_or_obj.data if isinstance(mesh_or_obj, bpy.types.Object) else mesh_or_obj
    ob = bpy.data.objects.new(name, me)
    ob.location = location
    ob.rotation_euler = rotation
    ob.scale = scale
    (col or bpy.context.scene.collection).objects.link(ob)
    return ob


def bevel_object(ob, width=0.05, segments=2, angle=math.radians(40), harden=True):
    mod = ob.modifiers.new('Bevel', 'BEVEL')
    mod.width = width
    mod.segments = segments
    mod.limit_method = 'ANGLE'
    mod.angle_limit = angle
    mod.harden_normals = harden
    return mod


def superellipse(a, b, n=4.0, count=64, rot=0.0, cx=0.0, cy=0.0):
    pts = []
    for i in range(count):
        t = 2 * math.pi * i / count
        c, s = math.cos(t), math.sin(t)
        x = a * math.copysign(abs(c) ** (2 / n), c)
        y = b * math.copysign(abs(s) ** (2 / n), s)
        xr = x * math.cos(rot) - y * math.sin(rot)
        yr = x * math.sin(rot) + y * math.cos(rot)
        pts.append((cx + xr, cy + yr))
    return pts


def offset_polygon(pts, d):
    """Offset a convex CCW polygon outward by d (miter)."""
    n = len(pts)
    out = []
    for i in range(n):
        p0, p1, p2 = Vector(pts[i - 1]), Vector(pts[i]), Vector(pts[(i + 1) % n])
        e0 = (p1 - p0).normalized()
        e1 = (p2 - p1).normalized()
        n0 = Vector((e0.y, -e0.x))
        n1 = Vector((e1.y, -e1.x))
        nm = (n0 + n1)
        if nm.length < 1e-6:
            nm = n0
        nm.normalize()
        k = d / max(0.2, nm.dot(n0))
        out.append((p1.x + nm.x * k, p1.y + nm.y * k))
    return out
