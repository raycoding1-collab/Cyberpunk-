"""THE MONOLITH: a brutalist media slab on the east side of the canyon.

Design: a 250 m board-formed concrete slab whose canyon face is a deep
egg-crate of fins and floor ledges; rooms glow at the back of every cell.
A colossal LED wall is hung proud of the grid, framed by a black bezel.
The building lands on giant pilotis over a glazed lobby and is capped by a
crown that cantilevers out over the street, lit from beneath."""

from . import materials as M
from . import signs
from .util import MeshBuilder, collection

X0, X1 = 18.0, 124.0
Y0, Y1 = 172.0, 334.0
TOP = 232.0
FIN_PITCH = 7.2
FLOOR = 4.2
DEPTH = 3.6
LOBBY = 14.0

SCREEN = dict(y0=207.0, y1=297.0, z0=66.0, z1=186.0)


def build():
    col = collection('Monolith')
    art = signs.ensure_art()
    conc = M.concrete('MonoConcrete', tone=0.13, tint=(0.97, 0.97, 1.0), panel=(2.4, 1.2), streaks=0.55)
    rooms = M.window_wall('MonoRooms', cell_w=FIN_PITCH, floor_h=FLOOR, lit=0.5, strength=3.0, mullion=0.25, office=True,
                          warm=(1.0, 0.6, 0.3), cool=(0.7, 0.85, 1.0), accent=(0.2, 0.9, 1.0))
    lobby = M.window_wall('MonoLobby', cell_w=3.6, floor_h=LOBBY, lit=0.9, strength=1.2, mullion=0.2, office=False,
                          warm=(1.0, 0.78, 0.55), cool=(1.0, 0.85, 0.65), accent=(1.0, 0.8, 0.6))
    bezel = M.metal('Bezel', base=(0.012, 0.012, 0.014), rough=0.28)
    screen = M.led_screen('MediaWall', art['dream'], strength=3.2, pixel_pitch=0.09,
                          size=(SCREEN['y1'] - SCREEN['y0'], SCREEN['z1'] - SCREEN['z0']))
    down = M.emission('CrownDownlight', (0.85, 0.9, 1.0), 16.0)
    mats = [conc, rooms, lobby, bezel, screen, down]
    eye_scr = M.led_screen('EyeScreen', art['eye'], strength=2.4, pixel_pitch=0.08, size=(40.0, 60.0))
    mb = MeshBuilder()

    # main mass behind the egg-crate; its back faces are glazed too
    mb.box((X0 + DEPTH, Y0 + DEPTH, LOBBY), (X1, Y1, TOP), 0, faces=(0, 0, 0, 0, 0, 1))
    back = MeshBuilder()
    back.box((X0 + DEPTH, Y0 + DEPTH, LOBBY), (X1, Y1, TOP), 0, faces=(0, 1, 0, 1, 0, 0))
    back.uv = [(uu, vv - LOBBY) for uu, vv in back.uv]
    mb.merge(back, mat_offset=1)
    # window walls at the back of the cells (canyon face and south face)
    wall = MeshBuilder()
    # UVs aligned so every egg-crate bay frames whole windows
    H = TOP - LOBBY
    wall.add([(X0 + DEPTH, Y1, LOBBY), (X0 + DEPTH, Y0 + DEPTH, LOBBY), (X0 + DEPTH, Y0 + DEPTH, TOP), (X0 + DEPTH, Y1, TOP)],
             [(3, 2, 1, 0)], 0, [(Y1 - Y0, 0), (DEPTH, 0), (DEPTH, H), (Y1 - Y0, H)])
    wall.add([(X0 + DEPTH, Y0 + DEPTH, LOBBY), (X1, Y0 + DEPTH, LOBBY), (X1, Y0 + DEPTH, TOP), (X0 + DEPTH, Y0 + DEPTH, TOP)],
             [(0, 1, 2, 3)], 0, [(DEPTH, 0), (X1 - X0, 0), (X1 - X0, H), (DEPTH, H)])
    mb.merge(wall, mat_offset=1)
    # egg-crate: vertical fins + floor ledges on the canyon face
    y = Y0
    while y <= Y1 + 0.01:
        mb.box((X0, y - 0.55, LOBBY), (X0 + DEPTH, y + 0.55, TOP), 0)
        y += FIN_PITCH
    z = LOBBY + FLOOR
    while z < TOP - 0.1:
        mb.box((X0 + 0.5, Y0, z - 0.35), (X0 + DEPTH, Y1, z + 0.35), 0)
        z += FLOOR
    # egg-crate on the south face
    x = X0
    while x <= X1 + 0.01:
        mb.box((x - 0.55, Y0, LOBBY), (x + 0.55, Y0 + DEPTH, TOP), 0)
        x += FIN_PITCH
    z = LOBBY + FLOOR
    while z < TOP - 0.1:
        mb.box((X0, Y0 + 0.5, z - 0.35), (X1, Y0 + DEPTH, z + 0.35), 0)
        z += FLOOR
    # pilotis and the lobby glass
    lob = MeshBuilder()
    lob.add([(X0 + 9, Y1, 0), (X0 + 9, Y0 + 9, 0), (X0 + 9, Y0 + 9, LOBBY), (X0 + 9, Y1, LOBBY)], [(3, 2, 1, 0)], 0,
            [(0, 0), (Y1 - Y0, 0), (Y1 - Y0, LOBBY), (0, LOBBY)])
    lob.add([(X0 + 9, Y0 + 9, 0), (X1, Y0 + 9, 0), (X1, Y0 + 9, LOBBY), (X0 + 9, Y0 + 9, LOBBY)], [(0, 1, 2, 3)], 0,
            [(0, 0), (X1 - X0, 0), (X1 - X0, LOBBY), (0, LOBBY)])
    mb.merge(lob, mat_offset=2)
    mb.box((X0, Y0, LOBBY - 1.6), (X1, Y1, LOBBY), 0)            # transfer slab
    y = Y0 + FIN_PITCH
    while y < Y1:
        mb.box((X0 + 0.6, y - 1.3, 0), (X0 + 3.2, y + 1.3, LOBBY - 1.6), 0)
        y += FIN_PITCH * 2
    x = X0 + FIN_PITCH * 2
    while x < X1:
        mb.box((x - 1.3, Y0 + 0.6, 0), (x + 1.3, Y0 + 3.2, LOBBY - 1.6), 0)
        x += FIN_PITCH * 2
    for i in range(int((Y1 - Y0) / 3.6)):
        yy = Y0 + 1.8 + i * 3.6
        mb.box((X0 + 1.0, yy - 0.1, LOBBY - 1.62), (X0 + 8.5, yy + 0.1, LOBBY - 1.6), 5)

    # the media wall: screen proud of the grid in a heavy bezel
    s = SCREEN
    mb.box((X0 - 1.6, s['y0'] - 1.8, s['z0'] - 1.8), (X0 - 0.2, s['y1'] + 1.8, s['z1'] + 1.8), 3)
    scr = MeshBuilder()
    scr.add([(X0 - 1.62, s['y1'], s['z0']), (X0 - 1.62, s['y0'], s['z0']), (X0 - 1.62, s['y0'], s['z1']), (X0 - 1.62, s['y1'], s['z1'])],
            [(0, 1, 2, 3)], 0, [(0, 0), (1, 0), (1, 1), (0, 1)])
    mb.merge(scr, mat_offset=4)
    for zz in (s['z0'] + 25, s['z1'] - 25):
        for yy in (s['y0'] + 10, s['y1'] - 10):
            mb.box((X0 - 0.2, yy - 0.6, zz - 0.6), (X0 + 0.6, yy + 0.6, zz + 0.6), 3)

    # second media wall on the south face, toward the street
    ex0, ex1, ez0, ez1 = 52.0, 92.0, 70.0, 130.0
    mb.box((ex0 - 1.5, Y0 - 1.6, ez0 - 1.5), (ex1 + 1.5, Y0 - 0.2, ez1 + 1.5), 3)
    eye = MeshBuilder()
    eye.add([(ex0, Y0 - 1.62, ez0), (ex1, Y0 - 1.62, ez0), (ex1, Y0 - 1.62, ez1), (ex0, Y0 - 1.62, ez1)], [(0, 1, 2, 3)], 0,
            [(0, 0), (1, 0), (1, 1), (0, 1)])
    mb.merge(eye, mat_offset=len(mats))

    # crown cantilevering over the canyon, lit from below
    c0 = TOP
    mb.box((X0 - 11.0, Y0 - 6.0, c0), (X1, Y1, c0 + 24.0), 0)
    gy = Y0 - 4.0
    while gy < Y1 - 2:
        mb.box((X0 - 10.0, gy, c0 - 0.02), (X0 - 1.0, gy + 0.35, c0), 5)
        gy += 4.5
    mb.box((X0 - 11.05, Y0 - 6.0, c0 + 3.5), (X0 - 11.0, Y1, c0 + 3.8), 5)
    mb.box((X0 - 11.05, Y0 - 6.0, c0 + 20.2), (X0 - 11.0, Y1, c0 + 20.5), 5)
    # roof: parapet light line, glass sky-lounge, louvred plant, helipad, masts
    rt = c0 + 24.0
    mb.box((X0 - 11.0, Y0 - 6.0, rt), (X1, Y1, rt + 1.2), 0, faces=(1, 1, 1, 1, 0, 0))
    mb.box((X0 - 11.05, Y0 - 6.05, rt + 0.7), (X1 + 0.05, Y0 - 5.95, rt + 0.85), 5)
    mb.box((X0 - 11.05, Y0 - 6.0, rt + 0.7), (X0 - 10.95, Y1, rt + 0.85), 5)
    lounge = MeshBuilder()
    lounge.box((X0 - 6.0, Y0 + 4.0, rt), (X0 + 30.0, Y0 + 30.0, rt + 7.5), 0, faces=(1, 1, 1, 1, 0, 0))
    mb.merge(lounge, mat_offset=2)
    mb.box((X0 - 7.0, Y0 + 3.0, rt + 7.5), (X0 + 31.0, Y0 + 31.0, rt + 8.3), 3)
    for i in range(14):
        yy = Y0 + 50 + i * 2.2
        mb.box((X0 + 40.0, yy, rt), (X0 + 70.0, yy + 0.4, rt + 9.0), 3)
    mb.box((X0 + 40.0, Y0 + 49.0, rt), (X0 + 70.0, Y0 + 82.0, rt + 0.6), 3)
    hx, hy = X0 + 55.0, Y1 - 40.0
    import math as _m
    pad = [(hx + 13.0 * _m.cos(2 * _m.pi * k / 8 + _m.pi / 8), hy + 13.0 * _m.sin(2 * _m.pi * k / 8 + _m.pi / 8)) for k in range(8)]
    mb.extrude_polygon(pad, rt, rt + 2.2, 3, 0)
    for k in range(16):
        a = 2 * _m.pi * k / 16
        mb.box((hx + 11.8 * _m.cos(a) - 0.25, hy + 11.8 * _m.sin(a) - 0.25, rt + 2.2), (hx + 11.8 * _m.cos(a) + 0.25, hy + 11.8 * _m.sin(a) + 0.25, rt + 2.35), 5)
    for (mx, my, mh) in ((X1 - 10, Y0 + 20, 46.0), (X1 - 18, Y0 + 30, 34.0), (X1 - 8, Y1 - 90, 58.0)):
        for dx, dy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            mb.beam((mx + dx * 1.6, my + dy * 1.6, rt), (mx + dx * 0.3, my + dy * 0.3, rt + mh), 0.25, 0.25, 3)
        for k in range(int(mh // 4)):
            zz = rt + 2 + k * 4
            t = (zz - rt) / mh
            r_ = 1.6 * (1 - t) + 0.3 * t
            mb.box((mx - r_, my - r_, zz), (mx + r_, my + r_, zz + 0.15), 3)
        mb.box((mx - 0.5, my - 0.5, rt + mh), (mx + 0.5, my + 0.5, rt + mh + 0.9), 7)
    ob = mb.to_object('MonolithStructure', mats + [eye_scr, M.emission('MonoBeacon', (1.0, 0.04, 0.02), 70.0)], col)

    # crown lettering
    neon = M.neon('MonoNeon', (0.85, 0.95, 1.0), 26.0)
    import math
    signs.text_object('ZENITH', 'Orbitron-Black.ttf', 13.0, 'MonoBrand', col, neon,
                      location=(X0 - 11.3, (Y0 + Y1) / 2, c0 + 12.0), rotation=(math.pi / 2, 0, -math.pi / 2),
                      extrude=0.35, bevel=0.06, spacing=1.15)
    return ob
