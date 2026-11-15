"""Meaningful analytic positives and deliberate failure cases for geometry.py.

Run: blender -b --python verification/test_geometry.py
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from geometry import analyze_frame, _tri_intersects, _point_on_path, EPS


def tube(xs, radius, count=16, capped=False):
    vertices = [[x, radius * np.cos(theta), radius * np.sin(theta)]
                for x in xs for theta in np.arange(count) * 2 * np.pi / count]
    triangles = []
    for ring in range(len(xs) - 1):
        for k in range(count):
            a, b = ring * count + k, ring * count + (k + 1) % count
            c, d = (ring + 1) * count + (k + 1) % count, (ring + 1) * count + k
            triangles.extend([[a, b, c], [a, c, d]])
    if capped:
        for ring, reverse in ((0, True), (len(xs) - 1, False)):
            centre = len(vertices)
            vertices.append([xs[ring], 0., 0.])
            for k in range(count):
                a, b = ring * count + k, ring * count + (k + 1) % count
                triangles.append([centre, b, a] if reverse else [centre, a, b])
    return np.array(vertices), np.array(triangles)


def valid_fixture():
    n = 16
    v, t = tube([-.6, -.2, .2, .6], .12, n)
    bv, bt = tube([-1., -.2, .2, 1.], .04, n, capped=True)
    topology = dict(armholes={'L': list(range(2*n, 3*n)), 'R': list(range(n, 2*n))},
                    cuffs={'L': list(range(3*n, 4*n)), 'R': list(range(n))},
                    sleeve_triangles={'L': list(range(4*n, 6*n)), 'R': list(range(2*n))},
                    seam_pairs=[[i, i] for i in range(n, 3*n)],
                    expected_openings=2, expected_components=1)
    arrays = dict(cloth_vertices=v, cloth_triangles=t, body_vertices=bv, body_triangles=bt,
                  path_L=np.array([[0., 0, 0], [.8, 0, 0]]),
                  path_R=np.array([[0., 0, 0], [-.8, 0, 0]]), rest_vertices=v.copy())
    return arrays, topology


class GeometryAcceptance(unittest.TestCase):
    def setUp(self):
        self.a, self.t = valid_fixture()

    def test_valid_arm_paths_and_seams(self):
        m = analyze_frame(self.a, self.t)
        self.assertTrue(m['arm_entry_pass'], m)
        self.assertTrue(m['cloth_sim_pass'], m)
        self.assertEqual(m['seam_max_gap_mm'], 0.)
        self.assertEqual(m['self_intersection_pairs'], 0)
        self.assertEqual(m['cloth_body_intersection_pairs'], 0)
        self.assertEqual(m['body_inside_sample_count'], 0)
        for side in ('L', 'R'):
            self.assertEqual(m['sleeves'][side]['armhole_crossings'], 1)
            self.assertEqual(m['sleeves'][side]['cuff_crossings'], 1)
            self.assertAlmostEqual(m['sleeves'][side]['interior_winding_min'], 1., places=5)

    def test_wrong_sides(self):
        self.a['path_L'], self.a['path_R'] = self.a['path_R'], self.a['path_L']
        m = analyze_frame(self.a, self.t)
        self.assertFalse(m['arm_entry_pass'])
        self.assertGreater(m['sleeves']['L']['wrong_side_crossings'], 0)

    def test_pierced_sleeve_surface(self):
        self.a['path_L'] = np.array([[0., 0, 0], [.3, 0, 0], [.4, .2, 0], [.5, 0, 0], [.8, 0, 0]])
        m = analyze_frame(self.a, self.t)
        self.assertFalse(m['arm_entry_pass'])
        self.assertEqual(m['sleeves']['L']['armhole_crossings'], 1)
        self.assertEqual(m['sleeves']['L']['cuff_crossings'], 1)
        self.assertGreater(m['sleeves']['L']['sleeve_wall_crossings'], 0)

    def test_cuff_not_crossed(self):
        self.a['path_L'][-1, 0] = .4
        m = analyze_frame(self.a, self.t)
        self.assertFalse(m['arm_entry_pass'])
        self.assertEqual(m['sleeves']['L']['cuff_crossings'], 0)

    def test_path_direction_reversed(self):
        self.a['path_L'] = self.a['path_L'][::-1].copy()
        m = analyze_frame(self.a, self.t)
        self.assertFalse(m['arm_entry_pass'])
        self.assertEqual(m['sleeves']['L']['armhole_hits'][0]['direction'], -1)

    def test_detached_seam(self):
        v = self.a['cloth_vertices']
        self.a['cloth_vertices'] = np.concatenate([v, [v[16] + [0, 0, .003]]])
        self.a['rest_vertices'] = self.a['cloth_vertices'].copy()
        self.t['seam_pairs'].append([16, len(v)])
        m = analyze_frame(self.a, self.t)
        self.assertTrue(m['arm_entry_pass'])
        self.assertFalse(m['seam_pass'])
        self.assertFalse(m['cloth_sim_pass'])
        self.assertAlmostEqual(m['seam_max_gap_mm'], 3.)

    def test_strict_two_mm_seam_threshold(self):
        v = self.a['cloth_vertices']
        self.a['cloth_vertices'] = np.concatenate([v, [v[16] + [0, .002, 0]]])
        self.a['rest_vertices'] = self.a['cloth_vertices'].copy()
        self.t['seam_pairs'].append([16, len(v)])
        m = analyze_frame(self.a, self.t)
        self.assertFalse(m['seam_pass'])

    def test_open_armhole_attachment(self):
        # Delete an adjacent torso triangle while preserving the sleeve shell.
        self.a['cloth_triangles'] = np.delete(self.a['cloth_triangles'], 32, axis=0)
        self.t['sleeve_triangles']['L'] = [x - 1 for x in self.t['sleeve_triangles']['L']]
        m = analyze_frame(self.a, self.t)
        self.assertFalse(m['arm_entry_pass'])
        self.assertFalse(m['sleeves']['R']['armhole_attached'])

    def test_body_pierces_cloth(self):
        self.a['body_vertices'][:, 1] += .13
        m = analyze_frame(self.a, self.t)
        self.assertFalse(m['cloth_sim_pass'])
        self.assertGreater(m['cloth_body_intersection_pairs'], 0)
        self.assertGreater(m['body_inside_sample_count'], 0)

    def test_enclosed_cloth_fails_without_intersection(self):
        # A body enclosing the whole sleeve cloth makes intersection-only
        # detection report zero. The independent inside samples catch it.
        self.a['body_vertices'][:, 1:] *= 5.
        m = analyze_frame(self.a, self.t)
        self.assertEqual(m['cloth_body_intersection_pairs'], 0)
        self.assertGreater(m['body_inside_sample_count'], 0)
        self.assertFalse(m['cloth_sim_pass'])

    def test_nonadjacent_self_intersection(self):
        n = len(self.a['cloth_vertices'])
        extra = np.array([[.9,.2,0],[.9,.4,0],[.9,.3,.2], [.8,.3,.05],[1.,.3,.05],[.9,.3,.3]])
        self.a['cloth_vertices'] = np.concatenate([self.a['cloth_vertices'], extra])
        self.a['rest_vertices'] = self.a['cloth_vertices'].copy()
        self.a['cloth_triangles'] = np.concatenate([self.a['cloth_triangles'], [[n,n+1,n+2],[n+3,n+4,n+5]]])
        self.t.update(expected_components=3, expected_openings=4)
        m = analyze_frame(self.a, self.t)
        self.assertGreater(m['self_intersection_pairs'], 0)
        self.assertFalse(m['cloth_sim_pass'])

    def test_near_contact_within_epsilon_is_allowed(self):
        # Parallel faces separated by 0.5 micrometre do not intersect.
        tri = np.array([[0.,0,0],[1.,0,0],[0.,1.,0]])
        self.assertFalse(_tri_intersects(tri, tri + [0,0,EPS/2]))
        # Pure edge contact does not become an area-overlap failure.
        self.assertFalse(_tri_intersects(tri, np.array([[0.,0,0],[1.,0,0],[0.,-1,0]])))
        # Exact nonadjacent overlapping faces remain a failure.
        self.assertTrue(_tri_intersects(tri, tri.copy()))

    def test_missing_labels_fail_closed(self):
        del self.t['cuffs']['L']
        m = analyze_frame(self.a, self.t)
        self.assertFalse(m['arm_entry_pass'])
        self.assertFalse(m['cloth_sim_pass'])

    def test_nonfinite_coordinates_fail_closed(self):
        self.a['cloth_vertices'][0, 0] = np.nan
        m = analyze_frame(self.a, self.t)
        self.assertFalse(m['arm_entry_pass'])
        self.assertFalse(m['cloth_sim_pass'])
        self.assertTrue(m['errors'])

    def test_self_intersecting_closed_body_rejected(self):
        vertices=self.a['body_vertices'];triangles=self.a['body_triangles']
        offset=vertices.copy();offset[:,1]+=.035
        self.a['body_vertices']=np.concatenate([vertices,offset])
        self.a['body_triangles']=np.concatenate([triangles,triangles+len(vertices)])
        m=analyze_frame(self.a,self.t)
        self.assertTrue(m['body_topology_pass'])
        self.assertGreater(m['body_self_intersection_pairs'],0)
        self.assertFalse(m['body_mesh_valid'])
        self.assertFalse(m['cloth_sim_pass'])

    def test_inside_out_body_rejected(self):
        self.a['body_triangles'] = self.a['body_triangles'][:, ::-1]
        m = analyze_frame(self.a, self.t)
        self.assertFalse(m['body_mesh_valid'])
        self.assertFalse(m['cloth_sim_pass'])


def negative_controls(arrays, topology):
    """Mutate a real evaluated frame and require the same verifier to reject it."""
    baseline = analyze_frame(arrays, topology)
    rows = []
    def run(name, a, t, reason_key, predicate):
        metrics = analyze_frame(a, t)
        detected = bool(predicate(metrics))
        rows.append(dict(name=name, expected='FAIL', detected=detected,
                         arm_entry_pass=metrics['arm_entry_pass'], cloth_sim_pass=metrics['cloth_sim_pass'],
                         reason_key=reason_key, relevant={k:metrics.get(k) for k in
                         ('seam_max_gap_mm','self_intersection_pairs','cloth_body_intersection_pairs','body_inside_sample_count')},
                         sleeves=metrics.get('sleeves'), errors=metrics.get('errors')))
    a = {k:v.copy() for k,v in arrays.items()}
    a['path_L'],a['path_R'] = a['path_R'].copy(),a['path_L'].copy()
    run('left_right_miswear', a, deepcopy(topology), 'wrong_side_crossings',
        lambda m: not m['arm_entry_pass'] and m['sleeves']['L'].get('wrong_side_crossings',0)>0)
    a = {k:v.copy() for k,v in arrays.items()}
    a['path_L'] = a['path_L'][::-1].copy()
    run('reverse_dressing_direction',a,deepcopy(topology),'directed_cap_crossing',lambda m:not m['arm_entry_pass'])
    if baseline.get('sleeves',{}).get('L',{}).get('armhole_hits') and baseline['sleeves']['L'].get('cuff_hits'):
        path = arrays['path_L']
        ah = baseline['sleeves']['L']['armhole_hits'][0]['distance_m']
        cuff = baseline['sleeves']['L']['cuff_hits'][0]['distance_m']
        before = _point_on_path(path,ah+.20*(cuff-ah))
        mid = _point_on_path(path,ah+.50*(cuff-ah))
        after = _point_on_path(path,ah+.80*(cuff-ah))
        axis = after-before;axis/=np.linalg.norm(axis)
        radial=np.cross(axis,[0.,1.,0.])
        if np.linalg.norm(radial)<.1:radial=np.cross(axis,[0.,0.,1.])
        radial/=np.linalg.norm(radial)
        a={k:v.copy() for k,v in arrays.items()}
        a['path_L']=np.array([path[0],before,mid+.4*radial,after,path[-1]])
        run('arm_through_sleeve_fabric',a,deepcopy(topology),'sleeve_wall_crossings',
            lambda m:not m['arm_entry_pass'] and m['sleeves']['L'].get('sleeve_wall_crossings',0)>0)
        a={k:v.copy() for k,v in arrays.items()}
        a['path_L']=np.array([path[0],mid])
        run('arm_does_not_exit_cuff',a,deepcopy(topology),'cuff_crossings',
            lambda m:not m['arm_entry_pass'] and m['sleeves']['L'].get('cuff_crossings',-1)==0)
    # Actually split the armhole seam: new sleeve-side vertices are moved 3mm
    # while torso-side vertices stay in place. The topology and pair mapping
    # are updated, so this detects both the physical gap and lost attachment.
    a={k:v.copy() for k,v in arrays.items()}; t=deepcopy(topology)
    old=list(t['armholes']['L']); n=len(a['cloth_vertices'])
    new=list(range(n,n+len(old))); mapping=dict(zip(old,new))
    axis=a['cloth_vertices'][t['cuffs']['L']].mean(0)-a['cloth_vertices'][old].mean(0)
    axis/=np.linalg.norm(axis)
    a['cloth_vertices']=np.concatenate([a['cloth_vertices'],a['cloth_vertices'][old]+axis*.003])
    rest=np.asarray(a.get('rest_vertices',t.get('rest_vertices')))
    a['rest_vertices']=np.concatenate([rest,rest[old]+axis*.003])
    for face in t['sleeve_triangles']['L']:
        a['cloth_triangles'][face]=[mapping.get(int(i),int(i)) for i in a['cloth_triangles'][face]]
    t['armholes']['L']=new
    t['seam_pairs'].extend([[i,j] for i,j in zip(old,new)])
    run('detached_armhole_seam_3mm',a,t,'seam_gap_and_attachment',
        lambda m:not m['cloth_sim_pass'] and not m.get('seam_pass',True)
                   and not m['sleeves']['L'].get('armhole_attached',True))
    a={k:v.copy() for k,v in arrays.items()}
    a['body_vertices'][:,1] += .12
    run('body_pierces_garment_surface',a,deepcopy(topology),'cloth_body_intersections',
        lambda m:not m['cloth_sim_pass'] and m.get('cloth_body_intersection_pairs',0)>0)
    a={k:v.copy() for k,v in arrays.items()};t=deepcopy(topology)
    n=len(a['cloth_vertices']);x=float(a['cloth_vertices'][:,0].max())+.3
    centre=np.array([x,0.,1.2])
    extra=np.array([[0,-.1,0],[0,.1,0],[0,0,.2],[-.1,0,.05],[.1,0,.05],[0,0,.3]])+centre
    a['cloth_vertices']=np.concatenate([a['cloth_vertices'],extra])
    rest=np.asarray(a.get('rest_vertices',t.get('rest_vertices')))
    a['rest_vertices']=np.concatenate([rest,extra])
    a['cloth_triangles']=np.concatenate([a['cloth_triangles'],[[n,n+1,n+2],[n+3,n+4,n+5]]])
    t['expected_components']=int(t.get('expected_components',1))+2
    t['expected_openings']=int(t.get('expected_openings',4))+2
    run('nonadjacent_fabric_self_intersection',a,t,'self_intersection_pairs',
        lambda m:not m['cloth_sim_pass'] and m.get('self_intersection_pairs',0)>0)
    return dict(source='real evaluated frame', baseline_arm_entry_pass=baseline['arm_entry_pass'],
                baseline_cloth_sim_pass=baseline['cloth_sim_pass'], control_count=len(rows),
                all_detected=bool(rows) and all(r['detected'] for r in rows), controls=rows)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(GeometryAcceptance)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    payload = dict(tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                   passed=result.wasSuccessful(), cases=[t.id() for group in unittest.defaultTestLoader.loadTestsFromTestCase(GeometryAcceptance) for t in [group]])
    target = Path(__file__).resolve().parents[1] / 'evidence' / 'negative-tests.json'
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(payload, indent=2))
    if '--' in sys.argv:
        import argparse
        parser=argparse.ArgumentParser()
        parser.add_argument('--frame',required=True)
        parser.add_argument('--topology',required=True)
        parser.add_argument('--out',required=True)
        args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
        controls=negative_controls(dict(np.load(args.frame)),json.loads(Path(args.topology).read_text()))
        Path(args.out).write_text(json.dumps(controls,indent=2))
        print('REAL_FRAME_NEGATIVE_CONTROLS',json.dumps({k:v for k,v in controls.items() if k!='controls'}))
        sys.exit(0 if result.wasSuccessful() and controls['all_detected'] and controls['baseline_cloth_sim_pass'] else 2)
    sys.exit(0 if result.wasSuccessful() else 2)
