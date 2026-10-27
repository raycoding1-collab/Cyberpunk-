"""Build the city part and optionally render shots.

    python blender/build.py --shots street_canyon --res 960x540 --samples 32 --out renders/preview
    python blender/build.py --save scene.blend
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402

from cityparts import scene, street, hive  # noqa: E402
from cityparts import shots as SH  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def build(parts):
    t0 = time.time()
    scene.reset()
    scene.setup_world()
    if 'street' in parts:
        street.build()
    if 'hive' in parts:
        hive.build()
    for name in ('capsule_spire', 'backdrop', 'monolith', 'helix', 'bridges', 'spire', 'skyline', 'fabric', 'signs', 'holo', 'clouds'):
        if name in parts:
            mod = __import__(f'cityparts.{name}', fromlist=['build'])
            mod.build()
    print(f'[build] scene built in {time.time() - t0:.1f}s')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--parts', default='capsule_spire,backdrop,clouds')
    ap.add_argument('--shots', default='')
    ap.add_argument('--res', default='960x540')
    ap.add_argument('--samples', type=int, default=32)
    ap.add_argument('--out', default='renders/preview')
    ap.add_argument('--save', default='')
    ap.add_argument('--preview', action='store_true')
    ap.add_argument('--final', action='store_true')
    ap.add_argument('--time-limit', type=float, default=0)
    a = ap.parse_args()
    parts = set(a.parts.split(','))
    build(parts)
    w, h = (int(v) for v in a.res.split('x'))
    scene.setup_render((w, h), a.samples, preview=a.preview or (a.samples < 64 and not a.final), final=a.final, time_limit=a.time_limit)
    scene.setup_compositor()
    if a.save:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.save))
    if a.shots:
        out = os.path.join(ROOT, a.out)
        os.makedirs(out, exist_ok=True)
        names = list(SH.SHOTS) if a.shots == 'all' else a.shots.split(',')
        for n in names:
            t = time.time()
            if a.final and os.path.exists(os.path.join(out, f'{n}.png')):
                print(f'[render] {n}: exists, skipping', flush=True)
                continue
            path = SH.render_shot(n, os.path.join(out, f'{n}.png'))
            print(f'[render] {n}: {time.time() - t:.1f}s -> {path}', flush=True)


if __name__ == '__main__':
    main()
