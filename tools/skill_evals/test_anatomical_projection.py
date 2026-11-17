"""Analytic independent-ray probes, including occlusion and unit response."""
import unittest
import numpy as np
from grade_anatomical_projection import coordinates, ray_hits


class ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.v=np.array([[-1.,0.,0.],[1.,0.,0.],[0.,2.,2.],[-1.,0.,4.],[1.,0.,4.],[0.,2.,6.]])
        self.f=np.array([[0,1,2],[3,4,5]])
        self.c={'width':100,'height':100,'views':{'front':{'axis':'front','px_per_cm':10,'center_cm':[0,1]}}}

    def test_ray_returns_frontmost_not_first_triangle(self):
        hits=ray_hits(self.v,self.f,self.c,'front',[(50,50),(0,0)])
        self.assertAlmostEqual(hits[0],5)
        self.assertIsNone(hits[1])
        reversed_hits=ray_hits(self.v,self.f[::-1],self.c,'front',[(50,50)])
        self.assertEqual(hits[:1],reversed_hits)

    def test_depth_responds_to_real_geometry_shift(self):
        moved=self.v.copy();moved[:,2]+=3
        hit=ray_hits(moved,self.f,self.c,'front',[(50,50)])[0]
        self.assertAlmostEqual(hit,8)

    def test_source_axis_conventions(self):
        self.c['views']['side']={'axis':'side','px_per_cm':10,'center_cm':[0,1]}
        self.c['views']['back']={'axis':'back','px_per_cm':10,'center_cm':[0,1]}
        p=np.array([[2.,1.,3.]])
        xy,z=coordinates(p,self.c,'side');np.testing.assert_allclose(xy,[[80,50]]);np.testing.assert_allclose(z,[2])
        xy,z=coordinates(p,self.c,'back');np.testing.assert_allclose(xy,[[30,50]]);np.testing.assert_allclose(z,[-3])


if __name__=='__main__':unittest.main()
