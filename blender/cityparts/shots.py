"""Camera compositions for the stills."""

import bpy

from . import scene

# name: (location, target, lens mm, extra)
SHOTS = {
    '01_canyon_hero': dict(loc=(7.0, 30.0, 1.6), tgt=(-4.0, 400.0, 205.0), lens=15, rain=True),
    '02_koi_overhead': dict(loc=(12.0, 96.0, 1.7), tgt=(-4.0, 142.0, 78.0), lens=14, rain=True),
    '03_media_wall': dict(loc=(-12.0, 150.0, 40.0), tgt=(18.0, 250.0, 120.0), lens=22),
    '04_capsule_wall': dict(loc=(-6.0, 66.0, 74.0), tgt=(-25.0, 92.0, 66.0), lens=32, dof=(27.0, 2.2)),
    '05_spire_vista': dict(loc=(-8.0, 330.0, 60.0), tgt=(0.0, 700.0, 520.0), lens=26),
    '06_aerial_city': dict(loc=(-230.0, -420.0, 520.0), tgt=(15.0, 560.0, 430.0), lens=20),
    '07_helix_twist': dict(loc=(26.0, 50.0, 1.8), tgt=(78.0, 86.0, 250.0), lens=14),
    '08_spire_plaza': dict(loc=(14.0, 560.0, 0.9), tgt=(0.0, 700.0, 48.0), lens=16, exposure=-0.2),
    '09_canyon_south': dict(loc=(2.0, 262.0, 128.0), tgt=(-2.0, 0.0, 30.0), lens=20),
    '10_street_south': dict(loc=(5.0, -110.0, 1.6), tgt=(-3.0, 300.0, 175.0), lens=15, rain=True),
}


def make_rain(cam_ob, count=9000, near=1.0, far=48.0, seed=5):
    """Rain streaks distributed through the camera frustum (denser near the lens)."""
    import math
    import random
    from mathutils import Vector
    from . import materials as M
    from .util import MeshBuilder
    R = random.Random(seed)
    cam = cam_ob.data
    sc = bpy.context.scene
    aspect = sc.render.resolution_x / sc.render.resolution_y
    hf = math.tan(math.atan(cam.sensor_width / (2 * cam.lens)))
    vf = hf / aspect
    m = cam_ob.matrix_world
    pos = m.translation
    fwd = (m.to_3x3() @ Vector((0, 0, -1))).normalized()
    right = (m.to_3x3() @ Vector((1, 0, 0))).normalized()
    upv = (m.to_3x3() @ Vector((0, 1, 0))).normalized()
    wind = Vector((0.12, 0.05, -1.0)).normalized()
    mb = MeshBuilder()
    for _ in range(count):
        d = near + (far - near) * (R.random() ** (1 / 2.2))
        sx, sy = R.uniform(-1.1, 1.1), R.uniform(-1.1, 1.1)
        c = pos + d * (fwd + right * sx * hf + upv * sy * vf)
        L = R.uniform(0.45, 0.85) * (0.6 + 0.4 * min(1.0, d / 10))
        w = 0.0045 + 0.0012 * d ** 0.5
        a = c - wind * L / 2
        b = c + wind * L / 2
        side = wind.cross((c - pos).normalized()).normalized() * w
        mb.add([tuple(a - side), tuple(a + side), tuple(b + side), tuple(b - side)], [(0, 1, 2, 3)], 0)
    g = M.G('Rain')
    t = g.n('ShaderNodeBsdfTransparent')
    gl = g.n('ShaderNodeBsdfGlossy', Roughness=0.2)
    e = g.n('ShaderNodeEmission', Strength=0.06)
    e.inputs['Color'].default_value = (0.75, 0.82, 1.0, 1)
    mx = g.n('ShaderNodeMixShader')
    mx.inputs[0].default_value = 0.32
    g.link(t.outputs[0], mx.inputs[1])
    g.link(gl.outputs[0], mx.inputs[2])
    add = g.n('ShaderNodeAddShader')
    g.link(mx.outputs[0], add.inputs[0])
    g.link(e.outputs[0], add.inputs[1])
    mat = g.done(add.outputs[0])
    ob = mb.to_object('Rain', [mat])
    ob.visible_shadow = False
    return ob


def render_shot(name, path):
    s = SHOTS[name]
    sc = bpy.context.scene
    old = bpy.data.objects.get('ShotCam')
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    cam = scene.camera('ShotCam', s['loc'], s['tgt'], lens=s['lens'], dof=s.get('dof'), shift=s.get('shift', (0, 0)))
    sc.camera = cam
    if 'exposure' in s:
        sc.view_settings.exposure = s['exposure']
    old_rain = bpy.data.objects.get('Rain')
    if old_rain:
        bpy.data.objects.remove(old_rain, do_unlink=True)
    if s.get('rain'):
        bpy.context.view_layer.update()
        make_rain(cam, count=s.get('rain_count', 9000))
    sc.view_settings.exposure = s.get('exposure', 0.0)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path
