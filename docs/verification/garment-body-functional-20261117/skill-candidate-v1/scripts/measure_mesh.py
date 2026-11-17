#!/usr/bin/env python3
"""Measure connected mesh-plane sections. Values belong to the mesh, not a verified person."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import vtk


def finite_vector(value, name):
    try:
        vector = np.asarray(value, float)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f'{name} must be a finite length-3 vector.') from error
    if vector.shape != (3,) or not np.isfinite(vector).all():
        raise ValueError(f'{name} must be a finite length-3 vector.')
    return vector


def section(mesh, origin, normal, seed):
    origin = finite_vector(origin, 'Plane origin')
    normal = finite_vector(normal, 'Plane normal')
    seed = finite_vector(seed, 'Component seed')
    scale = np.max(np.abs(normal))
    if scale == 0:
        raise ValueError('Plane normal must be finite and nonzero.')
    unit_normal = normal/scale
    unit_normal /= np.linalg.norm(unit_normal)
    plane = vtk.vtkPlane()
    plane.SetOrigin(*origin)
    plane.SetNormal(*unit_normal)
    cutter = vtk.vtkCutter()
    cutter.SetInputData(mesh)
    cutter.SetCutFunction(plane)
    cutter.Update()
    if cutter.GetOutput().GetNumberOfCells() == 0:
        raise ValueError('Plane does not intersect mesh.')
    connected = vtk.vtkPolyDataConnectivityFilter()
    connected.SetInputConnection(cutter.GetOutputPort())
    connected.SetExtractionModeToClosestPointRegion()
    connected.SetClosestPoint(*seed)
    connected.Update()
    part = connected.GetOutput()
    points = []
    length = 0.
    degree = {}
    for i in range(part.GetNumberOfCells()):
        cell = part.GetCell(i)
        for j in range(cell.GetNumberOfPoints()-1):
            ia, ib = cell.GetPointId(j), cell.GetPointId(j+1)
            a, b = np.asarray(part.GetPoint(ia)), np.asarray(part.GetPoint(ib))
            length += np.linalg.norm(a-b)
            points.extend([a, b])
            degree[ia] = degree.get(ia, 0) + 1
            degree[ib] = degree.get(ib, 0) + 1
    if not points:
        raise ValueError('Selected section is empty.')
    # A sum of cut edges is a circumference only for a closed, unbranched loop.
    if any(value != 2 for value in degree.values()):
        raise ValueError('Selected section is not a closed unbranched loop; inspect mesh topology.')
    values = np.asarray(points)
    return {'mesh_girth': float(length), 'world_axis_spans': np.ptp(values, axis=0).tolist(),
            'basis': 'mesh_parameter', 'mesh_checked': True,
            'plane_origin': list(origin), 'plane_normal': normal.tolist(), 'component_seed': list(seed),
            'anatomical_accuracy_verified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mesh', type=Path, required=True, help='OBJ or STL')
    parser.add_argument('--sections', type=Path, required=True, help='JSON list: name, origin, normal, seed')
    parser.add_argument('--unit', choices=['cm', 'mm', 'm', 'normalized'], required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    readers = {'.obj': vtk.vtkOBJReader, '.stl': vtk.vtkSTLReader}
    if args.mesh.suffix.lower() not in readers:
        raise ValueError('Use an OBJ/STL mesh or explicitly convert other formats first.')
    reader = readers[args.mesh.suffix.lower()]()
    reader.SetFileName(str(args.mesh))
    reader.Update()
    mesh = reader.GetOutput()
    if not mesh.GetNumberOfPoints():
        raise ValueError('Mesh is empty or unreadable.')
    results = []
    for item in json.loads(args.sections.read_text(encoding='utf-8')):
        value = section(mesh, item['origin'], item['normal'], item['seed'])
        value.update({'name': item['name'], 'unit': args.unit})
        results.append(value)
    output = {'mesh_sha256': hashlib.sha256(args.mesh.read_bytes()).hexdigest(),
              'measurements': results, 'software': 'VTK '+vtk.vtkVersion.GetVTKVersion()}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
