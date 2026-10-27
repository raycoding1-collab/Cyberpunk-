"""THE HIVE: a terraced capsule megastructure on the west side of the canyon.

Design: four freestanding concrete pylons (service cores with glass lift
shafts) carry six receding terraces. Each terrace band is a frame into which
prefabricated capsule homes are plugged (Nakagin-style portholes, louvred
studio windows, balcony units). Terrace slabs are drawn with continuous light
lines; slab soffits wash the capsule fronts with grazing downlight. At street
level a monumental colonnaded arcade holds the shops."""

import math

import bmesh
import bpy

from . import materials as M
from . import shops
from .util import MeshBuilder, collection, rng, superellipse

CAP_W, CAP_H, CAP_D = 3.0, 3.1, 5.4
PITCH_Y, PITCH_Z = 3.25, 3.3

HIVE_Y0, HIVE_Y1 = 10.0, 250.0
HIVE_BACK = -150.0
PODIUM_H = 14.0
BAND_H = 36.0
BANDS = 6
CORES_Y = [46.0, 98.0, 150.0, 202.0]
CORE_HALF = 7.0
CORE_X0, CORE_X1 = -34.0, -19.0
CORE_TOP = 286.0


def face_x(k):
    return -20.0 - 7.0 * k


# ---------------------------------------------------------------------------
# Capsule module meshes (front faces +X, back at x=0, centred on y, z from 0)
# ---------------------------------------------------------------------------

def _outline(x, a, b, n=5.0, count=48, cy=0.0, cz=0.0):
    pts = superellipse(a, b, n, count)
    return [(x, cy + py, cz + pz) for py, pz in pts]


def _plate_with_hole(mb, outer, inner, mat):
    n = len(outer)
    verts = list(outer) + list(inner)
    faces = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    mb.add(verts, faces, mat, [(p[1], p[2]) for p in verts])


def _tube(mb, ring_a, ring_b, mat):
    """Wall between two rings; normals point toward the ring axis when a is in front."""
    mb.ring_strip(ring_a, ring_b, mat)


def _torus_x(mb, x, cy, cz, R, r, mat, seg=40, sides=8):
    verts, faces = [], []
    for i in range(seg):
        t = 2 * math.pi * i / seg
        for j in range(sides):
            s = 2 * math.pi * j / sides
            rr = R + r * math.cos(s)
            verts.append((x + r * math.sin(s), cy + rr * math.cos(t), cz + rr * math.sin(t)))
    for i in range(seg):
        for j in range(sides):
            a = i * sides + j
            b = ((i + 1) % seg) * sides + j
            c = ((i + 1) % seg) * sides + (j + 1) % sides
            d = i * sides + (j + 1) % sides
            faces.append((a, d, c, b))
    mb.add(verts, faces, mat)


def capsule_mesh(variant, name):
    mb = MeshBuilder()
    W, H, D = CAP_W, CAP_H, CAP_D
    a, b = W / 2, H / 2
    back = _outline(0.0, a, b, 5.0, 48, 0.0, b)
    front = _outline(D, a, b, 5.0, 48, 0.0, b)
    mb.ring_strip(back, front, 0)          # shell (rounded section)
    mb.cap(back, 0, flip=True)
    # recessed front plate with the opening
    inset = _outline(D - 0.06, a - 0.07, b - 0.07, 5.0, 48, 0.0, b)
    mb.ring_strip(front, inset, 0)         # small chamfer step into the plate
    if variant == 'porthole':
        hole_c = (0.0, b + 0.12)
        hole = [(D - 0.06, hole_c[0] + 0.78 * math.cos(2 * math.pi * i / 48), hole_c[1] + 0.78 * math.sin(2 * math.pi * i / 48)) for i in range(48)]
        hole_in = [(D - 0.5, p[1], p[2]) for p in hole]
        _torus_x(mb, D + 0.0, hole_c[0], hole_c[1], 0.84, 0.075, 1)
        _torus_x(mb, D - 0.06, hole_c[0], hole_c[1], 0.79, 0.03, 1)
    elif variant == 'louvre':
        hc = (0.0, b + 0.2)
        pts = superellipse(1.12, 0.6, 6.0, 48)
        hole = [(D - 0.06, hc[0] + y, hc[1] + z) for y, z in pts]
        hole_in = [(D - 0.45, p[1], p[2]) for p in hole]
        for i in range(5):
            z = hc[1] - 0.48 + i * 0.24
            mb.box((D - 0.02, -1.1, z - 0.035), (D + 0.12, 1.1, z + 0.035), 1)
        mb.box((D - 0.05, -1.25, hc[1] - 0.72), (D + 0.16, 1.25, hc[1] - 0.64), 1)  # sill
    else:  # balcony
        hc = (0.0, 1.32)
        pts = superellipse(0.62, 1.08, 6.0, 48)
        hole = [(D - 0.06, hc[0] + y, hc[1] + z) for y, z in pts]
        hole_in = [(D - 0.4, p[1], p[2]) for p in hole]
        # grated balcony shelf and railing
        mb.box((D - 0.05, -1.32, 0.02), (D + 0.95, 1.32, 0.14), 1)
        mb.box((D + 0.88, -1.32, 1.02), (D + 0.95, 1.32, 1.08), 1)
        mb.box((D + 0.88, -1.32, 0.45), (D + 0.93, 1.32, 0.48), 1)
        for y in (-1.3, -0.65, 0.0, 0.65, 1.3):
            mb.box((D + 0.89, y - 0.025, 0.14), (D + 0.94, y + 0.025, 1.04), 1)
    _plate_with_hole(mb, inset, hole, 0)
    _tube(mb, hole, hole_in, 1)
    mb.cap(hole_in, 2)                     # glass pane
    # room behind the glass: lamp strip + softly lit back wall
    mb.box((0.6, -0.5, H - 0.32), (D - 1.0, 0.5, H - 0.22), 3)
    mb.box((0.25, -a + 0.35, 0.5), (0.3, a - 0.35, H - 0.5), 3, faces=(0, 1, 0, 0, 0, 0))
    # drip edge, vent grille and a status LED
    mb.box((D - 0.1, -a + 0.3, H - 0.16), (D + 0.22, a - 0.3, H - 0.08), 1)
    mb.box((D + 0.02, -0.8, H - 0.165), (D + 0.16, 0.8, H - 0.16), 4, faces=(0, 0, 0, 0, 1, 0))
    mb.box((D - 0.06, 0.62, 0.32), (D + 0.03, 1.2, 0.72), 1)
    for i in range(4):
        z = 0.38 + i * 0.09
        mb.box((D + 0.02, 0.64, z), (D + 0.07, 1.18, z + 0.03), 1)
    return mb


# ---------------------------------------------------------------------------
# The structure
# ---------------------------------------------------------------------------

def build(seed=4):
    R = rng(seed)
    col = collection('Hive')
    caps_col = collection('HiveCapsules', col)

    conc = M.concrete('HiveConcrete', tone=0.15, tint=(1.0, 0.97, 0.93), panel=(3.6, 1.2), streaks=0.45)
    conc_dark = M.concrete('HiveInner', tone=0.06, tint=(0.95, 0.95, 1.0), panel=(3.25, 3.3), streaks=0.3)
    steel = M.metal('HiveSteel', base=(0.05, 0.05, 0.055), rough=0.35)
    shops_glz = M.window_wall('HiveMezz', cell_w=2.5, floor_h=4.5, lit=0.7, strength=1.3, mullion=0.16, office=False,
                          warm=(1.0, 0.66, 0.38), cool=(0.85, 0.9, 1.0), accent=(1.0, 0.35, 0.55))
    terrace_led = M.emission('HiveTerraceLED', (1.0, 0.72, 0.45), 18.0)
    soffit = M.emission('HiveSoffit', (1.0, 0.82, 0.62), 12.0)
    glass = M.clear_glass('HiveGlass', tint=(0.8, 0.9, 0.95))
    cabin = M.emission('LiftCabin', (1.0, 0.8, 0.55), 9.0)
    slot_cols = [(1.0, 0.08, 0.45), (0.05, 0.75, 1.0), (1.0, 0.45, 0.08), (0.55, 0.2, 1.0)]
    slots = [M.emission(f'CoreSlot{i}', c, 28.0) for i, c in enumerate(slot_cols)]
    beacon = M.emission('Beacon', (1.0, 0.04, 0.02), 60.0)
    mats = [conc, conc_dark, steel, shops_glz, terrace_led, soffit, glass, cabin, beacon] + slots
    S = {m.name: i for i, m in enumerate(mats)}

    mb = MeshBuilder()

    def in_core(y, margin=0.0):
        return any(abs(y - c) < CORE_HALF + margin for c in CORES_Y)

    # ---- podium arcade --------------------------------------------------
    mb.box((HIVE_BACK, HIVE_Y0, 0), (-35.0, HIVE_Y1, PODIUM_H - 4), S['HiveConcrete'], faces=(1, 0, 1, 1, 0, 0))
    mb.box((-35.0, HIVE_Y0, 4.6), (-26.0, HIVE_Y1, 10.0), S['HiveConcrete'], faces=(0, 0, 1, 1, 1, 0))
    # dark fascia band carrying the shop names, mezzanine glazing above
    mb.box((-26.0, HIVE_Y0, 4.6), (-25.85, HIVE_Y1, 5.5), S['HiveSteel'])
    sf = MeshBuilder()
    sf.add([(-26.0, HIVE_Y1, 5.5), (-26.0, HIVE_Y0, 5.5), (-26.0, HIVE_Y0, 10.0), (-26.0, HIVE_Y1, 10.0)], [(3, 2, 1, 0)], 0,
           [(0, 0), (HIVE_Y1 - HIVE_Y0, 0), (HIVE_Y1 - HIVE_Y0, 4.5), (0, 4.5)])
    mb.merge(sf, mat_offset=S['HiveMezz'])
    cols_y = []
    y = HIVE_Y0 + 6.0
    while y < HIVE_Y1 - 3:
        if not in_core(y, 2.0):
            cols_y.append(y)
        y += 10.0
    free, cur = [], HIVE_Y0
    for cy in CORES_Y:
        free.append((cur, cy - CORE_HALF - 0.3))
        cur = cy + CORE_HALF + 0.3
    free.append((cur, HIVE_Y1))
    # pylon bases close the arcade between shop runs
    shops.build_arcade(col, -26.0, free, cols_y)
    # arcade soffit and fascia
    mb.box((-26.0, HIVE_Y0, 10.0), (-18.0, HIVE_Y1, PODIUM_H), S['HiveConcrete'])
    for xs in (-24.2, -20.4):
        mb.box((xs - 0.12, HIVE_Y0 + 1, 9.96), (xs + 0.12, HIVE_Y1 - 1, 10.0), S['HiveSoffit'])
    y = HIVE_Y0 + 6.0
    while y < HIVE_Y1 - 3:
        if not in_core(y, 2.0):
            # chamfered column
            pts = [(-19.6 + 0.8 * math.cos(math.pi / 8 + i * math.pi / 4), y + 0.8 * math.sin(math.pi / 8 + i * math.pi / 4)) for i in range(8)]
            mb.extrude_polygon(pts, 0.0, 10.0, S['HiveConcrete'], S['HiveConcrete'])
        y += 10.0
    # south face of the podium: shop glazing
    sp = MeshBuilder()
    sp.add([(HIVE_BACK, HIVE_Y0 - 0.01, 0.0), (-18.0, HIVE_Y0 - 0.01, 0.0), (-18.0, HIVE_Y0 - 0.01, 10.0), (HIVE_BACK, HIVE_Y0 - 0.01, 10.0)],
           [(0, 1, 2, 3)], 0, [(0, 0), (132, 0), (132, 10), (0, 10)])
    mb.merge(sp, mat_offset=S['HiveMezz'])

    # ---- terrace bands --------------------------------------------------
    capsule_slots = []   # (x_front, y, z, facing)
    back_faces = []
    for k in range(BANDS):
        z0 = PODIUM_H + BAND_H * k
        z1 = z0 + BAND_H
        fx = face_x(k)
        inner = fx - CAP_D - 0.2
        # mass behind the capsules (south capsules plug into its south wall)
        south_in = HIVE_Y0 + CAP_D + 0.4
        mb.box((HIVE_BACK, south_in, z0), (inner, HIVE_Y1, z1 - 2.6), S['HiveInner'], faces=(0, 1, 1, 0, 0, 0))
        bk = MeshBuilder()
        bk.box((HIVE_BACK, south_in, z0), (inner, HIVE_Y1, z1 - 2.6), 0, faces=(1, 0, 0, 1, 0, 0))
        back_faces.append(bk)
        # mega slab (terrace floor of the band above) with light line and soffit wash
        slab_front = fx + 1.3
        mb.box((HIVE_BACK, HIVE_Y0 - 1.2, z1 - 2.6), (slab_front, HIVE_Y1 + 0.5, z1), S['HiveConcrete'])
        mb.box((slab_front, HIVE_Y0 - 1.2, z1 - 1.45), (slab_front + 0.05, HIVE_Y1 + 0.5, z1 - 1.25), S['HiveTerraceLED'])
        mb.box((HIVE_BACK, HIVE_Y0 - 1.25, z1 - 1.45), (slab_front, HIVE_Y0 - 1.2, z1 - 1.25), S['HiveTerraceLED'])
        mb.box((fx - 1.1, HIVE_Y0, z1 - 2.64), (fx - 0.5, HIVE_Y1, z1 - 2.6), S['HiveSoffit'])
        # grazing uplight washing the capsule fronts from the terrace below
        mb.box((fx + 0.3, HIVE_Y0, z0 + 0.02), (fx + 0.7, HIVE_Y1, z0 + 0.06), S['HiveSoffit'], faces=(0, 0, 0, 0, 0, 1))
        # glass balustrade with steel rail along the terrace edge
        if k < BANDS - 1:
            mb.box((slab_front - 0.5, HIVE_Y0 - 1.0, z1), (slab_front - 0.46, HIVE_Y1, z1 + 1.1), S['HiveGlass'])
            mb.box((slab_front - 0.56, HIVE_Y0 - 1.0, z1 + 1.1), (slab_front - 0.4, HIVE_Y1, z1 + 1.18), S['HiveSteel'])
            # planter run on the terrace
            mb.box((face_x(k + 1) + 2.2, HIVE_Y0 + 2, z1), (face_x(k + 1) + 3.6, HIVE_Y1 - 2, z1 + 0.9), S['HiveConcrete'])
        # structural links from the slab out to the pylons
        for cy in CORES_Y:
            if slab_front < CORE_X0:
                mb.box((slab_front, cy - 4.5, z1 - 2.6), (CORE_X0, cy + 4.5, z1), S['HiveConcrete'])
                mb.box((slab_front, cy - 4.55, z1 - 1.45), (CORE_X0, cy - 4.5, z1 - 1.25), S['HiveTerraceLED'])
                mb.box((slab_front, cy + 4.5, z1 - 1.45), (CORE_X0, cy + 4.55, z1 - 1.25), S['HiveTerraceLED'])
        # capsule slots on the canyon face
        rows = int((BAND_H - 2.8) // PITCH_Z)
        y = HIVE_Y0 + 2.0
        while y < HIVE_Y1 - 2.0:
            if not in_core(y, 1.9):
                for r in range(rows):
                    z = z0 + 0.15 + r * PITCH_Z
                    capsule_slots.append((inner, y, z, 'E', k))
            y += PITCH_Y
        # uplight grazing the south capsule fronts
        mb.box((HIVE_BACK + 1.0, HIVE_Y0 - 0.7, z0 + 0.02), (inner - 0.5, HIVE_Y0 - 0.3, z0 + 0.06), S['HiveSoffit'], faces=(0, 0, 0, 0, 0, 1))
        mb.box((HIVE_BACK + 1.0, HIVE_Y0 - 0.9, z1 - 2.64), (inner - 0.5, HIVE_Y0 - 0.3, z1 - 2.6), S['HiveSoffit'])
        # capsule slots on the south face (toward the street camera)
        x = HIVE_BACK + 3.0
        while x < inner - 2.0:
            for r in range(rows):
                z = z0 + 0.15 + r * PITCH_Z
                capsule_slots.append((x, south_in, z, 'S', k))
            x += PITCH_Y
    top = PODIUM_H + BAND_H * BANDS
    # glazed back and north faces of the mass
    for bk in back_faces:
        mb.merge(bk, mat_offset=len(mats))
    # roof crown: mechanical louvre band and parapet
    mb.box((HIVE_BACK, HIVE_Y0, top), (face_x(BANDS - 1) - 2, HIVE_Y1, top + 6.0), S['HiveConcrete'])
    for i in range(int((HIVE_Y1 - HIVE_Y0) / 1.2)):
        yy = HIVE_Y0 + 0.6 + i * 1.2
        mb.box((face_x(BANDS - 1) - 2.2, yy, top + 6.0), (face_x(BANDS - 1) - 1.9, yy + 0.25, top + 11.0), S['HiveSteel'])

    # ---- service cores / pylons ---------------------------------------
    for ci, cy in enumerate(CORES_Y):
        y0, y1 = cy - CORE_HALF, cy + CORE_HALF
        mb.box((CORE_X0, y0, 0.0), (CORE_X1, y1, CORE_TOP), S['HiveConcrete'])
        # recessed light slots on the canyon face
        for ys in (y0 + 1.4, y1 - 1.4):
            mb.box((CORE_X1, ys - 0.18, PODIUM_H), (CORE_X1 + 0.06, ys + 0.18, CORE_TOP - 8), len(mats) - 4 + ci)
        # glass lift shaft with steel frame and two cabins
        gx0, gx1 = CORE_X1, CORE_X1 + 2.8
        mb.box((gx0, cy - 2.6, PODIUM_H), (gx1, cy + 2.6, CORE_TOP - 6), S['HiveGlass'], faces=(0, 1, 1, 1, 0, 0))
        zz = PODIUM_H
        while zz < CORE_TOP - 6:
            mb.box((gx1 - 0.05, cy - 2.7, zz), (gx1 + 0.12, cy + 2.7, zz + 0.25), S['HiveSteel'])
            zz += 4.0
        for yy in (cy - 2.65, cy + 2.55):
            mb.box((gx0, yy, PODIUM_H), (gx1 + 0.12, yy + 0.1, CORE_TOP - 6), S['HiveSteel'])
        for cz in (R.uniform(30, 120), R.uniform(140, 260)):
            mb.box((gx0 + 0.4, cy - 1.0, cz), (gx1 - 0.4, cy + 1.0, cz + 2.8), S['LiftCabin'])
        # crown: louvred cap, mast and beacon
        mb.box((CORE_X0 - 1, y0 - 1, CORE_TOP), (CORE_X1 + 1, y1 + 1, CORE_TOP + 1.2), S['HiveSteel'])
        mast_h = R.uniform(22, 40)
        mb.box((-27.3, cy - 0.35, CORE_TOP), (-26.6, cy + 0.35, CORE_TOP + mast_h), S['HiveSteel'])
        mb.box((-27.5, cy - 0.55, CORE_TOP + mast_h), (-26.4, cy + 0.55, CORE_TOP + mast_h + 1.1), S['Beacon'])

    back_rooms = M.window_wall('HiveBackRooms', cell_w=3.25, floor_h=3.3, lit=0.45, strength=2.2, mullion=0.5, office=False, zone=2)
    ob = mb.to_object('HiveStructure', mats + [back_rooms], col)

    # ---- capsules ---------------------------------------------------------
    variants = {
        'porthole': capsule_mesh('porthole', 'CapPort'),
        'louvre': capsule_mesh('louvre', 'CapLouvre'),
        'balcony': capsule_mesh('balcony', 'CapBalc'),
    }
    cap_mats = [M.capsule_shell(), steel, M.clear_glass('CapGlass', tint=(0.92, 0.95, 1.0), rough=0.03), M.capsule_interior(), M.capsule_porch()]
    meshes = {}
    for kname, b in variants.items():
        meshes[kname] = b.to_mesh(f'Capsule_{kname}')
        for m in cap_mats:
            meshes[kname].materials.append(m)
    count = 0
    for (x, y, z, facing, k) in capsule_slots:
        if R.random() < 0.09:
            continue
        v = R.choices(['porthole', 'louvre', 'balcony'], [0.55, 0.3, 0.15])[0]
        jitter = R.choice([0.0, 0.0, 0.35, 0.7, 1.15])
        o = bpy.data.objects.new('Cap', meshes[v])
        if facing == 'E':
            o.location = (x + jitter, y, z)
            o.rotation_euler = (0, 0, 0)
        else:
            o.location = (x, y - jitter, z)
            o.rotation_euler = (0, 0, -math.pi / 2)
        caps_col.objects.link(o)
        count += 1
    print(f'[hive] {count} capsules')
    return {'structure': ob, 'capsules': count}
