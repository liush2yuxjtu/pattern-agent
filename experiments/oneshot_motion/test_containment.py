"""Known-volume checks for the conservative exterior-pruning boundary."""
import unittest
import numpy as np
from verify_motion import contained_samples,oracle


class ContainmentPruning(unittest.TestCase):
    def check_mesh(self,v,t,points):
        actual,_=contained_samples(v,t,points)
        expected=oracle.point_inside_mesh(v,t,points)
        np.testing.assert_array_equal(actual,expected)

    def test_closed_cube_random_interior_exterior_and_slab_edges(self):
        v,t=oracle._cube();points=np.random.default_rng(42).uniform(-1.8,1.8,(250,3))
        points=np.concatenate([points,[[.5,.5,z] for z in [-1.0001,-.980001,-.98,0,.98,.9999,1.0001]]])
        self.check_mesh(v,t,points)

    def test_rotated_translated_closed_cube(self):
        v,t=oracle._cube();a=.47;b=.63
        rx=np.array([[1,0,0],[0,np.cos(a),-np.sin(a)],[0,np.sin(a),np.cos(a)]])
        rz=np.array([[np.cos(b),-np.sin(b),0],[np.sin(b),np.cos(b),0],[0,0,1]])
        transform=rz@rx;offset=np.array([3.1,-2.3,.17]);points=np.random.default_rng(17).uniform(-1.8,1.8,(250,3))
        self.check_mesh(v@transform.T+offset,t,points@transform.T+offset)

    def test_two_disjoint_closed_volumes_do_not_fill_the_gap(self):
        v,t=oracle._cube();vertices=np.concatenate([v+[-2,0,0],v+[2,0,0]]);triangles=np.concatenate([t,t+len(v)])
        points=np.random.default_rng(81).uniform([-4,-1.5,-1.5],[4,1.5,1.5],(300,3))
        self.check_mesh(vertices,triangles,np.concatenate([points,[[0,0,0],[2,0,0],[-2,0,0]]]))


if __name__=='__main__':unittest.main()
