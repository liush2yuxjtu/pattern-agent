"""Render the verified Sandy state, and the existing accepted DXF shell, in Blender."""
from argparse import ArgumentParser
from hashlib import sha256
from mathutils import Vector
from pathlib import Path
import bpy
import json
import sys

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "AGENTS.md").is_file())
VIEWS = {"angle": (1.9, -3.5, .26), "front": (0, -4, .14), "back": (0, 4, .14)}
SANDY_COLORS = {"sandy-standard": (.048, .218, .234), "sandy-flared": (.438, .145, .074)}
RESOLUTION = (940, 840)


def material(name, color, fabric=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    surface = m.node_tree.nodes.get("Principled BSDF")
    surface.inputs["Base Color"].default_value = (*color, 1)
    surface.inputs["Roughness"].default_value = .74 if fabric else .94
    if fabric:
        surface.inputs["Sheen Weight"].default_value = .22
        noise = m.node_tree.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 185
        noise.inputs["Detail"].default_value = 2
        bump = m.node_tree.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = .12
        bump.inputs["Distance"].default_value = .0014
        m.node_tree.links.new(noise.outputs["Fac"], bump.inputs["Height"])
        m.node_tree.links.new(bump.outputs["Normal"], surface.inputs["Normal"])
    return m


def key_light(name, location, target, energy, radius):
    light = bpy.data.lights.new(name, "AREA")
    light.energy = energy
    light.shape = "DISK"
    light.size = radius
    obj = bpy.data.objects.new(name, light)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def cloth_mesh(source):
    state = json.loads(source.read_text())
    flat = state["positions"]
    faces = state["triangles"]
    verts = [(x, -z, y) for x, y, z in zip(flat[::3], flat[1::3], flat[2::3], strict=True)]
    tris = list(zip(faces[::3], faces[1::3], faces[2::3], strict=True))
    mesh = bpy.data.meshes.new("Sandy solved mesh")
    mesh.from_pydata(verts, [], tris)
    mesh.update()
    obj = bpy.data.objects.new("Sandy skirt body", mesh)
    bpy.context.collection.objects.link(obj)
    return [obj]


def frame_camera(camera, place, aim, coords, center, minimum):
    camera.location = place
    rotation = (aim - camera.location).to_track_quat("-Z", "Y")
    camera.rotation_euler = rotation.to_euler()
    projection = rotation.inverted()
    projected = [projection @ (point - center - aim) for point in coords]
    width = 2.2 * max(abs(point.x) for point in projected)
    height = 2.2 * max(abs(point.y) for point in projected) * RESOLUTION[0] / RESOLUTION[1]
    camera.data.ortho_scale = max(minimum, width, height)


def render(case, source, output, views):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if source.suffix == ".json":
        objects = cloth_mesh(source)
    else:
        bpy.ops.import_scene.gltf(filepath=str(source))
        objects = [x for x in bpy.context.scene.objects if x.type == "MESH"]
    assert objects
    coords = [ob.matrix_world @ v.co for ob in objects for v in ob.data.vertices]
    lo = Vector(tuple(min(p[i] for p in coords) for i in range(3)))
    hi = Vector(tuple(max(p[i] for p in coords) for i in range(3)))
    center = (lo + hi) * .5
    for ob in objects:
        ob.location -= center
    height = hi.z - lo.z
    swatch = material(case, SANDY_COLORS.get(case, (.105, .212, .385)), fabric=True)
    for ob in objects:
        ob.data.materials.clear()
        ob.data.materials.append(swatch)
        for poly in ob.data.polygons:
            poly.use_smooth = True

    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new("Diffuse studio")
    scene.world.use_nodes = True
    world_background = scene.world.node_tree.nodes.get("Background")
    world_background.inputs["Color"].default_value = (.72,.77,.78,1)
    world_background.inputs["Strength"].default_value = .34
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.5*height-.052))
    bpy.context.object.data.materials.append(material("Warm gray studio", (.75,.77,.746)))
    origin = Vector((0,0,0))
    key_light("Soft key", (-2.2,-3,3.0), origin, 545, 3.1)
    key_light("Front fill", (2.5,-1.2,1.3), origin, 185, 2.8)
    key_light("Edge fill", (1.6,2.3,2.6), origin, 375, 2.25)
    camera = bpy.data.objects.new("Orthographic camera", bpy.data.cameras.new("Orthographic camera"))
    bpy.context.collection.objects.link(camera)
    camera.data.type = "ORTHO"
    camera.data.clip_end = 250
    minimum = max((hi.x-lo.x)*1.18, height*1.44, .98 if case.startswith("sandy") else 0)
    scene.camera = camera
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 28
    scene.cycles.use_denoising = False
    scene.cycles.adaptive_threshold = .035
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4
    scene.render.resolution_x, scene.render.resolution_y = RESOLUTION
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    output.mkdir(exist_ok=True, parents=True)
    for view in views:
        frame_camera(camera, VIEWS[view], Vector((0, 0, -.025*height)), coords, center, minimum)
        scene.render.filepath = str(output / f"{view}.png")
        bpy.ops.render.render(write_still=True)
    report = {
        "geometry_sha256": sha256(source.read_bytes()).hexdigest(),
        "vertices": sum(len(ob.data.vertices) for ob in objects),
        "faces": sum(len(ob.data.polygons) for ob in objects),
        "dimensions_m": list(hi-lo),
        "renderer": f"Blender {bpy.app.version_string} Cycles CPU",
        "views": [view for view in VIEWS if (output / f"{view}.png").is_file()],
        "scope": "Rendered source geometry, studio lighting and display material. No physical fit claim.",
    }
    (output / "render.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    cli = ArgumentParser()
    cli.add_argument("--capture", type=Path, required=True)
    cli.add_argument("--output", type=Path, required=True)
    cli.add_argument("--case", choices=(*SANDY_COLORS, "shirt-cuff"))
    cli.add_argument("--view", choices=VIEWS)
    args = cli.parse_args(sys.argv[sys.argv.index("--") + 1:])
    cases = (args.case,) if args.case else (*SANDY_COLORS, "shirt-cuff")
    views = (args.view,) if args.view else VIEWS
    for name in cases:
        if name in SANDY_COLORS:
            source = args.capture.resolve() / name / "state.json"
        else:
            source = ROOT / "web/intent-edit-review/sewn/03_cuff_width/files/model.glb"
            assert sha256(source.read_bytes()).hexdigest() == "ffb75cedd87eac81ef39250715e5ae1cf3d1c9230304c6ed01b60afa2bc42835"
        render(name, source, args.output.resolve() / name, views)
