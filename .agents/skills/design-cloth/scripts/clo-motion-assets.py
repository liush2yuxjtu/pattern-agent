"""Export paired SANIM and skeletal FBX assets in Blender's Python runtime."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import struct
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sanim_codec import read_frame, read_native, write_animation
from sanim_rig import fk, rig

import bpy
import numpy as np
from mathutils import Matrix, Vector


def world(bones, frame):
    positions, rotations = fk(bones, frame)
    to_blender = Matrix.Rotation(math.pi / 2, 4, "X")
    matrices = []
    for position, rotation in zip(positions, rotations):
        transform = Matrix(rotation).to_4x4()
        transform.translation = Vector(position) * 0.001
        matrices.append(to_blender @ transform @ to_blender.inverted())
    return matrices


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bind(bones, rest):
    armature = bpy.data.armatures.new("Source avatar")
    obj = bpy.data.objects.new("Source avatar", armature)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    parents = {child: i for i, bone in enumerate(bones) for child in bone["sons"]}
    bpy.ops.object.mode_set(mode="EDIT")
    names = []
    for index, bone in enumerate(bones):
        name = bone.get("_name") or bone.get("name") or f"joint_{index}"
        edit = armature.edit_bones.new(name)
        transform = rest[index]
        edit.head = transform.translation
        edit.tail = transform @ Vector((0, 0.025, 0))
        edit.align_roll(transform.to_3x3() @ Vector((0, 0, 1)))
        if index in parents:
            edit.parent = armature.edit_bones[names[parents[index]]]
        names.append(edit.name)
    bpy.ops.object.mode_set(mode="OBJECT")
    return obj, names


def skin(path, armature, names, rest):
    with ZipFile(path) as archive:
        data = json.loads(archive.read("avatar.json"))
        binary = archive.read("sbin")
    objects = {item["_id"]: item for group in data["_objectsArrays"] for item in group}
    avatar = next(item for item in objects.values() if "skeleton" in item and "avatarSizes" in item)

    def chunk(block):
        return memoryview(binary)[block["offset"]:block["offset"] + block["size"]]

    def array(block, offset, dtype, width):
        count, = struct.unpack_from("<Q", block, offset)
        values = np.frombuffer(block, dtype=dtype, count=count * width, offset=offset + 8)
        return values.reshape(count, width), offset + 8 + count * width * 4

    to_blender = Matrix.Rotation(math.pi / 2, 4, "X")
    for key in avatar["currentSkinnedMeshes"]:
        part = objects[key]
        if "heel" in part["_name"].lower():
            continue
        body = objects[part["mesh"]]
        mesh_data = chunk(body["geoMesh"]["geoMeshData"])
        points, offset = array(mesh_data, 0, "<f4", 3)
        _, offset = array(mesh_data, offset, "<f4", 3)  # normals
        _, offset = array(mesh_data, offset, "<f4", 3)  # UV
        faces, _ = array(mesh_data, offset, "<u4", 3)
        binding = objects[part["skinnedInfo"]]
        inverse = np.array(binding["clusterMatrics"], dtype=float).reshape(-1, 4, 4).transpose(0, 2, 1)
        binding_data = chunk(binding["vertexes"])
        positions, influences = [], []
        offset = 8
        for point in points:
            weights, offset = array(binding_data, offset, "<f4", 1)
            joints, offset = array(binding_data, offset, "<u4", 1)
            clusters, offset = array(binding_data, offset, "<u4", 1)
            weights = weights.ravel() / weights.sum()
            rest_point = Vector((0.0, 0.0, 0.0))
            combined = {}
            for weight, joint, cluster in zip(weights, joints.ravel(), clusters.ravel()):
                local = Vector((inverse[cluster] @ np.r_[point, 1.0])[:3]) * 0.001
                rest_point += (rest[joint] @ (to_blender.to_3x3() @ local)) * float(weight)
                combined[joint] = combined.get(joint, 0.0) + float(weight)
            positions.append(rest_point)
            influences.append(combined)
        mesh = bpy.data.meshes.new(part["_name"])
        mesh.from_pydata(positions, [], faces.tolist())
        mesh.update()
        obj = bpy.data.objects.new(part["_name"], mesh)
        bpy.context.collection.objects.link(obj)
        obj.parent = armature
        modifier = obj.modifiers.new("Source avatar skin", "ARMATURE")
        modifier.object = armature
        groups = [obj.vertex_groups.new(name=name) for name in names]
        for index, weights in enumerate(influences):
            for joint, weight in weights.items():
                groups[joint].add([index], weight, "REPLACE")
        obj.select_set(True)


def export(bones, path, output, fps, avatar):
    native = read_native(path)
    frames = [read_frame(native[2], index) for index in range(native[3])]
    sanim = output / (path.stem + ".sanim")
    write_animation(sanim, native, frames)
    check = read_native(sanim)
    if check[3] != native[3] or any(
            read_frame(check[2], i) != read_frame(native[2], i) for i in range(native[3])):
        raise ValueError(f"Style3D round trip differs for {path.name}")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    rest = world(bones, frames[0])
    obj, names = bind(bones, rest)
    skin(avatar, obj, names, rest)
    scene = bpy.context.scene
    scene.render.fps = fps
    scene.frame_start, scene.frame_end = 0, len(frames) - 1
    previous = {}
    for index, frame in enumerate(frames):
        scene.frame_set(index)
        matrices = dict(zip(names, world(bones, frame)))
        for name, matrix in matrices.items():
            pose = obj.pose.bones[name]
            pose.rotation_mode = "QUATERNION"
            parent = pose.parent
            parent_space = ({"parent_matrix": matrices[parent.name],
                             "parent_matrix_local": parent.bone.matrix_local} if parent else {})
            pose.matrix_basis = pose.bone.convert_local_to_pose(
                matrix, pose.bone.matrix_local, invert=True, **parent_space)
            quaternion = pose.rotation_quaternion
            if name in previous and quaternion.dot(previous[name]) < 0:
                quaternion.negate()
            previous[name] = quaternion.copy()
            for channel in ("rotation_quaternion", "location", "scale"):
                pose.keyframe_insert(channel, frame=index, group=name)
    source_positions = {}
    for index in sorted({0, len(frames) // 2, len(frames) - 1}):
        scene.frame_set(index)
        source_positions[index] = [tuple(obj.pose.bones[name].matrix.translation) for name in names]
    fbx = output / (path.stem + ".fbx")
    bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, add_leaf_bones=False,
                             bake_anim=True, bake_anim_use_all_actions=False,
                             bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = fps
    bpy.ops.import_scene.fbx(filepath=str(fbx), anim_offset=0.0)
    imported, = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    if not any(obj.type == "MESH" for obj in bpy.context.scene.objects):
        raise ValueError(f"FBX has no skinned avatar for {path.name}")
    if set(names) != set(imported.pose.bones.keys()):
        raise ValueError(f"FBX skeleton readback differs for {path.name}")
    errors = []
    for index, expected in source_positions.items():
        bpy.context.scene.frame_set(index)
        for name, point in zip(names, expected):
            actual = imported.matrix_world @ imported.pose.bones[name].matrix.translation
            errors.append((actual - Vector(point)).length)
    if max(errors) > 0.005:
        raise ValueError(f"FBX sampled joint readback drift {max(errors):.6f} m for {path.name}")
    return {"name": path.stem, "frames": len(frames), "fps": fps,
            "sanim_sha256": sha(sanim), "fbx_sha256": sha(fbx),
            "source_sha256": sha(path), "fbx_max_sampled_joint_error_m": max(errors)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--avatar", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("motions", type=Path, nargs="+")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    args.out.mkdir(parents=True, exist_ok=True)
    bones = rig(args.avatar)
    records = [export(bones, path, args.out, args.fps, args.avatar) for path in args.motions]
    (args.out / "motions.json").write_text(json.dumps(records, indent=2) + "\n")


if __name__ == "__main__":
    main()
