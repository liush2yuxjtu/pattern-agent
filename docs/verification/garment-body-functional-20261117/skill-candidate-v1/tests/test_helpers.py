import importlib.util
import sys
import unittest
from unittest import mock
import tempfile
from pathlib import Path
import cv2
import numpy as np
import vtk

ROOT = Path(__file__).resolve().parents[1]

def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT/'scripts'/f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

verify = load('verify_masks')
measure = load('measure_mesh')

class TestMasks(unittest.TestCase):
    def test_known_overlap(self):
        a=np.zeros((10,10),bool);b=a.copy();a[2:6,2:6]=1;b[3:7,3:7]=1
        result=verify.compare(a,b)
        self.assertAlmostEqual(result['iou'],9/23)
        self.assertAlmostEqual(result['dice'],18/32)
        self.assertGreater(result['mean_symmetric_contour_distance_px'],0)
    def test_identical(self):
        a=np.zeros((10,10),bool);a[2:6,2:6]=1
        result=verify.compare(a,a)
        self.assertEqual(result['iou'],1)
        self.assertEqual(result['mean_symmetric_contour_distance_px'],0)
    def test_empty_is_failure(self):
        with self.assertRaises(ValueError):verify.compare(np.zeros((10,10)),np.zeros((10,10)))
    def test_shape_mismatch_is_failure(self):
        with self.assertRaises(ValueError):verify.compare(np.ones((10,10)),np.ones((8,8)))
    def test_overlay_dimensions(self):
        a=np.zeros((10,10),bool);a[2:6,2:6]=1
        image=verify.overlay(np.zeros((10,10,3),np.uint8),a,a)
        self.assertEqual(image.shape,(10,10,3))
        self.assertEqual(image.dtype,np.uint8)
        np.testing.assert_array_equal(image[3,3], [68,121,30])
    def test_numeric_binary_masks_preserve_metrics(self):
        a=np.zeros((10,10));a[2:6,2:6]=1
        self.assertEqual(verify.compare(a,a.astype(np.uint8)),verify.compare(a.astype(bool),a.astype(bool)))
    def test_invalid_mask_values_fail_on_either_input(self):
        good=np.ones((3,3))
        for value in (np.nan,np.inf,-np.inf,0.5,-1,255,1+1j,'1'):
            bad=np.full((3,3),value)
            for a,b in ((bad,good),(good,bad)):
                with self.subTest(value=value,first=a is bad):
                    with self.assertRaisesRegex(ValueError,'binary'):
                        verify.compare(a,b)
                    with self.assertRaisesRegex(ValueError,'binary'):
                        verify.overlay(np.zeros((3,3,3)),a,b)
    def test_mask_dimensions_fail(self):
        for bad in (np.ones(3),np.ones((3,3,1)),np.ones((0,0))):
            with self.subTest(shape=bad.shape),self.assertRaises(ValueError):
                verify.compare(bad,bad)
    def test_load_mask_keeps_explicit_threshold(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'mask.png'
            self.assertTrue(cv2.imwrite(str(path),np.array([[0,127,128,255]],np.uint8)))
            np.testing.assert_array_equal(verify.load_mask(path),[[False,False,True,True]])
    def test_invalid_photo_shape_and_channels_fail(self):
        mask=np.ones((3,3),bool)
        photos=[np.zeros((3,3)),np.zeros((3,3,1)),np.zeros((3,3,4)),
                np.zeros((3,3,3,1)),np.zeros((2,3,3))]
        photos.extend(np.full((3,3,3),value) for value in (np.nan,np.inf,-np.inf,-1,256,'0',1+1j))
        for photo in photos:
            with self.subTest(shape=photo.shape,dtype=photo.dtype),self.assertRaises(ValueError):
                verify.overlay(photo,mask,mask)

class TestMesh(unittest.TestCase):
    def setUp(self):
        cylinder=vtk.vtkCylinderSource();cylinder.SetRadius(10);cylinder.SetHeight(20);cylinder.SetResolution(360);cylinder.Update()
        self.mesh=cylinder.GetOutput()
    def test_known_circle(self):
        result=measure.section(self.mesh,[0,0,0],[0,1,0],[0,0,0])
        self.assertAlmostEqual(result['mesh_girth'],20*np.pi,places=2)
        self.assertTrue(result['mesh_checked'])
        self.assertFalse(result['anatomical_accuracy_verified'])
    def test_missed_plane_fails(self):
        with self.assertRaises(ValueError):measure.section(self.mesh,[0,100,0],[0,1,0],[0,100,0])
    def test_zero_normal_fails(self):
        with self.assertRaises(ValueError):measure.section(self.mesh,[0,0,0],[0,0,0],[0,0,0])
    def test_invalid_vectors_fail_before_vtk(self):
        invalid=[[],[0,0],[0,0,0,0],[[0,0,0]],None,'bad',
                 [np.nan,0,0],[0,np.inf,0],[0,0,-np.inf]]
        for index,name in enumerate(('origin','normal','seed')):
            for value in invalid:
                vectors=[[0,0,0],[0,1,0],[0,0,0]]
                vectors[index]=value
                with self.subTest(vector=name,value=value),mock.patch.object(measure.vtk,'vtkPlane') as plane:
                    with self.assertRaisesRegex(ValueError,'finite length-3'):
                        measure.section(self.mesh,*vectors)
                    plane.assert_not_called()
    def test_normal_scaling_preserves_closed_section(self):
        expected=measure.section(self.mesh,[0,0,0],[0,1,0],[0,0,0])
        for magnitude in (1e308,1e-300):
            with self.subTest(magnitude=magnitude):
                actual=measure.section(self.mesh,[0,0,0],[0,magnitude,0],[0,0,0])
                self.assertAlmostEqual(actual['mesh_girth'],expected['mesh_girth'])
                np.testing.assert_allclose(actual['world_axis_spans'],expected['world_axis_spans'])
    def test_open_section_remains_failure(self):
        surface=vtk.vtkPlaneSource();surface.Update()
        with self.assertRaisesRegex(ValueError,'closed unbranched loop'):
            measure.section(surface.GetOutput(),[0,0,0],[1,0,0],[0,0,0])

if __name__=='__main__':unittest.main()
