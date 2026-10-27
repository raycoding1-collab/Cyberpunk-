"""Low cloud ceiling just above the Spire's crown. The underside glows with
the city's light (magenta-violet over the districts, gold around the
arcology) and is diffuse, so the searchlight beams land on it as real spots.
The Spire's needle pierces the deck."""

from . import materials as M
from .util import MeshBuilder, collection

Z = 560.0


def cloud_material(name, scale, density, glow):
    g = M.G(name)
    obj = g.coords('Object')
    warp = g.noise(obj, scale * 0.6, 3, 0.5, out='Color')
    vm = g.n('ShaderNodeVectorMath')
    vm.operation = 'MULTIPLY_ADD'
    g.link(warp, vm.inputs[0])
    vm.inputs[1].default_value = (420.0, 420.0, 0.0)
    g.link(obj, vm.inputs[2])
    p = vm.outputs[0]
    n1 = g.noise(p, scale, 7, 0.62)
    n2 = g.noise(p, scale * 4.0, 5, 0.6)
    d = g.math('MULTIPLY_ADD', n2, 0.35, n1)
    alpha = g.ramp(d, [(0.42, (0, 0, 0)), (0.78, (density, density, density))])
    sep = g.n('ShaderNodeSeparateXYZ')
    g.link(obj, sep.inputs[0])
    # distance from the Spire (0, 700) drives the warm glow
    dx = g.math('SUBTRACT', sep.outputs['X'], 0.0)
    dy = g.math('SUBTRACT', sep.outputs['Y'], 700.0)
    r = g.math('SQRT', g.math('ADD', g.math('MULTIPLY', dx, dx), g.math('MULTIPLY', dy, dy)))
    warm = g.ramp(g.math('DIVIDE', r, 1600.0), [(0.0, (1.0, 0.55, 0.18)), (0.18, (0.8, 0.25, 0.35)), (0.5, (0.32, 0.12, 0.45)), (1.0, (0.06, 0.04, 0.12))])
    em = g.n('ShaderNodeEmission')
    g.link(warm, em.inputs['Color'])
    g.link(g.math('MULTIPLY', d, glow), em.inputs['Strength'])
    diff = g.n('ShaderNodeBsdfDiffuse')
    diff.inputs['Color'].default_value = (0.3, 0.3, 0.34, 1)
    add = g.n('ShaderNodeAddShader')
    g.link(diff.outputs[0], add.inputs[0])
    g.link(em.outputs[0], add.inputs[1])
    tr = g.n('ShaderNodeBsdfTransparent')
    mx = g.n('ShaderNodeMixShader')
    sa = g.n('ShaderNodeSeparateColor')
    g.link(alpha, sa.inputs[0])
    g.link(sa.outputs[0], mx.inputs[0])
    g.link(tr.outputs[0], mx.inputs[1])
    g.link(add.outputs[0], mx.inputs[2])
    return g.done(mx.outputs[0])


def build():
    col = collection('Clouds')
    for i, (z, scale, dens, glow) in enumerate(((Z, 0.0011, 0.92, 0.55), (Z + 70.0, 0.0007, 0.75, 0.3))):
        mb = MeshBuilder()
        mb.add([(-6000, -5000, z), (6000, -5000, z), (6000, 7000, z), (-6000, 7000, z)], [(0, 1, 2, 3)], 0)
        ob = mb.to_object(f'CloudDeck{i}', [cloud_material(f'Cloud{i}', scale, dens, glow)], col)
        ob.visible_shadow = False
    return col
