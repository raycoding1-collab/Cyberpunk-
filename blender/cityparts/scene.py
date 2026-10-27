"""World, atmosphere, render and compositing setup."""

import bpy

from . import materials as M


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def setup_render(res=(1920, 1080), samples=128, preview=False, final=False, time_limit=0):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    cy = sc.cycles
    cy.device = 'CPU'
    cy.samples = samples
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.02 if preview else 0.012
    cy.adaptive_min_samples = 16
    cy.use_denoising = True
    cy.denoiser = 'OPENIMAGEDENOISE'
    cy.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
    cy.denoising_prefilter = 'ACCURATE'
    cy.use_light_tree = True
    cy.max_bounces = 8
    cy.diffuse_bounces = 3
    cy.glossy_bounces = 4
    cy.transmission_bounces = 6
    cy.transparent_max_bounces = 16
    cy.volume_bounces = 1
    cy.sample_clamp_indirect = 12.0
    cy.sample_clamp_direct = 0.0
    cy.blur_glossy = 0.6
    cy.caustics_reflective = False
    cy.caustics_refractive = False
    try:
        cy.use_guiding = True
        cy.use_volume_guiding = True
        cy.use_surface_guiding = True
    except Exception:
        pass
    if final:
        # measured: guiding and extra bounces cost ~15% for no visible gain here
        cy.use_guiding = False
        cy.diffuse_bounces = 2
        cy.glossy_bounces = 3
        cy.volume_bounces = 0
        cy.adaptive_threshold = 0.015
        cy.denoising_quality = 'HIGH'
    if time_limit:
        cy.time_limit = time_limit
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.render.use_persistent_data = False
    sc.render.threads_mode = 'AUTO'
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_depth = '8'
    vs = sc.view_settings
    vs.view_transform = 'AgX'
    try:
        vs.look = 'AgX - Medium High Contrast'
    except Exception:
        pass
    vs.exposure = 0.0
    vs.gamma = 1.0


def setup_world(density=0.0007, anisotropy=0.4, mist=0.0024, mist_top=75.0):
    sc = bpy.context.scene
    w = bpy.data.worlds.new('NightSky')
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld')
    # sky: deep indigo zenith, magenta-violet light-polluted horizon
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Generated'], sep.inputs[0])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    cr = ramp.color_ramp
    cr.elements[0].position = 0.0
    cr.elements[0].color = (0.016, 0.006, 0.022, 1)
    cr.elements[1].position = 0.18
    cr.elements[1].color = (0.004, 0.004, 0.014, 1)
    e = cr.elements.new(0.6)
    e.color = (0.0015, 0.0015, 0.004, 1)
    nt.links.new(sep.outputs['Z'], ramp.inputs[0])
    bg = nt.nodes.new('ShaderNodeBackground')
    bg.inputs['Strength'].default_value = 1.0
    nt.links.new(ramp.outputs[0], bg.inputs['Color'])
    nt.links.new(bg.outputs[0], out.inputs['Surface'])
    # homogeneous haze: gives every light a halo and the canyon its depth
    vol = nt.nodes.new('ShaderNodeVolumePrincipled')
    vol.inputs['Density'].default_value = density
    vol.inputs['Anisotropy'].default_value = anisotropy
    vol.inputs['Color'].default_value = (0.62, 0.66, 1.0, 1)
    nt.links.new(vol.outputs[0], out.inputs['Volume'])
    # low-lying mist layer: denser air in the streets, clearer above the roofs
    if mist > 0:
        import bmesh
        me = bpy.data.meshes.new('MistLayer')
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts:
            v.co.x *= 6000.0
            v.co.y *= 6000.0
            v.co.z = (v.co.z + 0.5) * mist_top - 0.5
        bm.to_mesh(me)
        bm.free()
        mm = bpy.data.materials.new('Mist')
        mm.use_nodes = True
        mnt = mm.node_tree
        mnt.nodes.clear()
        mo = mnt.nodes.new('ShaderNodeOutputMaterial')
        mv = mnt.nodes.new('ShaderNodeVolumePrincipled')
        mv.inputs['Density'].default_value = mist
        mv.inputs['Anisotropy'].default_value = anisotropy
        mv.inputs['Color'].default_value = (0.62, 0.66, 1.0, 1)
        mnt.links.new(mv.outputs[0], mo.inputs['Volume'])
        me.materials.append(mm)
        ob = bpy.data.objects.new('MistLayer', me)
        ob.location = (0, 300, 0)
        sc.collection.objects.link(ob)
    return w


def setup_compositor(bloom=0.6, threshold=1.0, dispersion=0.012, vignette=True):
    sc = bpy.context.scene
    ng = bpy.data.node_groups.new('Grade', 'CompositorNodeTree')
    ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    rl = ng.nodes.new('CompositorNodeRLayers')
    glare = ng.nodes.new('CompositorNodeGlare')
    glare.inputs['Type'].default_value = 'Bloom'
    glare.inputs['Quality'].default_value = 'High'
    glare.inputs['Threshold'].default_value = threshold
    glare.inputs['Strength'].default_value = bloom
    glare.inputs['Size'].default_value = 0.85
    glare.inputs['Saturation'].default_value = 1.0
    ng.links.new(rl.outputs['Image'], glare.inputs['Image'])
    last = glare.outputs[0]
    # thin anamorphic streaks on the hottest lights
    streak = ng.nodes.new('CompositorNodeGlare')
    streak.inputs['Type'].default_value = 'Streaks'
    streak.inputs['Quality'].default_value = 'Medium'
    streak.inputs['Threshold'].default_value = threshold * 6
    streak.inputs['Strength'].default_value = 0.12
    streak.inputs['Streaks'].default_value = 2
    streak.inputs['Streaks Angle'].default_value = 0.0
    streak.inputs['Fade'].default_value = 0.9
    ng.links.new(last, streak.inputs['Image'])
    last = streak.outputs[0]
    lens = ng.nodes.new('CompositorNodeLensdist')
    try:
        lens.inputs['Dispersion'].default_value = dispersion
        lens.inputs['Distortion'].default_value = -0.004
    except Exception:
        pass
    ng.links.new(last, lens.inputs['Image'])
    last = lens.outputs[0]
    outn = ng.nodes.new('NodeGroupOutput')
    ng.links.new(last, outn.inputs[0])
    sc.compositing_node_group = ng
    sc.render.compositor_device = 'CPU'
    sc.render.use_compositing = True
    return ng


def camera(name, location, target, lens=24.0, sensor=36.0, dof=None, shift=(0, 0)):
    from mathutils import Vector
    cam = bpy.data.cameras.new(name)
    cam.lens = lens
    cam.sensor_width = sensor
    cam.clip_start = 0.1
    cam.clip_end = 20000
    cam.shift_x, cam.shift_y = shift
    if dof:
        cam.dof.use_dof = True
        cam.dof.focus_distance = dof[0]
        cam.dof.aperture_fstop = dof[1]
    ob = bpy.data.objects.new(name, cam)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = location
    d = Vector(target) - Vector(location)
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return ob
