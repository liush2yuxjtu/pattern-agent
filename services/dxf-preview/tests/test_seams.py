"""Adversarial acceptance of the actual exported sewn-shell artifact."""
import copy,hashlib,json,os,struct,unittest
from pathlib import Path
import numpy as np
from converter.core import convert_dxf
from verification.seams import audit_arrays,audit_glb,decode_glb
from verification.geometry import analytic_tests

ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'public/sample.dxf').read_bytes()

class SewingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.converted=convert_dxf(SOURCE,units='mm');cls.v,cls.f,cls.m,_=decode_glb(cls.converted.glb);cls.results=[]
    @classmethod
    def tearDownClass(cls):
        destination=os.environ.get('SEWING_TEST_EVIDENCE')
        if destination:
            p=Path(destination);p.mkdir(parents=True,exist_ok=True);(p/'adversarial-controls.json').write_text(json.dumps(cls.results,ensure_ascii=False,indent=2)+'\n')
    def check_case(self,name,expected,change=None,intersections=False):
        v=self.v.copy();f=self.f.copy();m=copy.deepcopy(self.m)
        if change:v,f,m=change(v,f,m)
        result=audit_arrays(v,f,m,SOURCE,'mm',check_intersections=intersections)
        self.results.append({'case':name,'expected':expected,'observed':result['verdict'],'failures':result['failures'],'self_intersections':result['checks'].get('proper_self_intersections'),'max_gap_mm':result['checks'].get('max_seam_gap_mm')})
        self.assertEqual(result['verdict'],expected,result['failures']);return result
    def test_strict_oracle_has_23_analytic_controls(self):
        r=analytic_tests();self.assertTrue(r['all_passed']);self.assertEqual(r['test_count'],23)
        self.results.append({'case':'independent_SAT_and_topology_analytic_controls','count':23,'observed':'PASS'})
    def test_hidden_gltf_node_transform_is_rejected(self):
        blob=self.converted.glb;length=struct.unpack_from('<I',blob,12)[0];doc=json.loads(blob[20:20+length]);doc['nodes'][0]['scale']=[-1,1,1];raw=json.dumps(doc,separators=(',',':')).encode();raw+=b' '*((-len(raw))%4);tail=blob[20+length:];changed=struct.pack('<III',0x46546c67,2,20+len(raw)+len(tail))+struct.pack('<II',len(raw),0x4e4f534a)+raw+tail
        r=audit_glb(changed,SOURCE,'mm');self.assertEqual(r['verdict'],'FAIL');self.assertIn('UNVERIFIED_NODE_TRANSFORM',' '.join(r['failures']))
        self.results.append({'case':'hidden_scene_mirror_transform','expected':'FAIL','observed':r['verdict'],'failures':r['failures']})
    def test_exact_float32_export_passes_all_seams(self):
        r=audit_glb(self.converted.glb,SOURCE,'mm');self.assertEqual(r['verdict'],'PASS',r['failures']);c=r['checks']
        self.assertEqual(len(c['seams']),15);self.assertEqual(c['max_seam_gap_mm'],0);self.assertEqual(c['proper_self_intersections'],0);self.assertEqual(c['topology']['connected_components'],1);self.assertEqual(c['topology']['boundary_cycles'],4);self.assertEqual(c['vertex_link_failures'],0);self.assertLess(c['max_3d_seam_length_error_mm'],2)
        self.results.append({'case':'actual_export','observed':'PASS','sha256':hashlib.sha256(self.converted.glb).hexdigest(),'seams':15,'gaps_mm':0,'intersections':0,'boundary_cycles':4})
    def test_rigid_transform_is_still_valid(self):
        def change(v,f,m):
            t=.43;r=np.array([[np.cos(t),0,np.sin(t)],[0,1,0],[-np.sin(t),0,np.cos(t)]]);return v@r.T+[.6,-.3,.9],f,m
        self.check_case('rigid_transform','PASS',change,True)
    def test_original_file_hash_cannot_be_forged(self):
        def change(v,f,m):m['input_sha256']='0'*64;return v,f,m
        self.check_case('wrong_original_hash','FAIL',change)
    def test_source_front_back_labels_cannot_be_swapped(self):
        def change(v,f,m):
            a=m['pattern']['original_edges'];a['sleeve.cap.front'],a['sleeve.cap.back']=a['sleeve.cap.back'],a['sleeve.cap.front'];return v,f,m
        self.check_case('wrong_source_edge_labels','FAIL',change)
    def test_undeclared_ease_is_rejected(self):
        def change(v,f,m):m['segments']['front.side.left']['process_mm']=-26;return v,f,m
        self.check_case('hidden_extra_ease','FAIL',change)
    def test_removed_seam_is_rejected(self):
        def change(v,f,m):m['seams'].pop();return v,f,m
        self.check_case('missing_declared_seam','FAIL',change)
    def test_reversed_cap_pairing_is_rejected(self):
        def change(v,f,m):m['segments']['sleeve.left.cap.front']['vertices'].reverse();return v,f,m
        self.check_case('reversed_sleeve_cap_pairing','FAIL',change)
    def test_coincident_but_unwelded_patch_is_rejected(self):
        def change(v,f,m):
            p=m['patches']['front'];old=np.asarray(p['global_vertices']);duplicate=np.arange(len(v),len(v)+len(old));v=np.vstack([v,v[old]]);start,n=p['face_start'],p['face_count'];f[start:start+n]=duplicate[np.asarray(p['local_faces'])];p['global_vertices']=duplicate
            for s in m['segments'].values():
                if s['patch']=='front':s['vertices']=duplicate[np.asarray(s['local_vertices'])].tolist()
            return v,f,m
        self.check_case('coincident_unwelded_front','FAIL',change)
    def test_three_mm_seam_gap_is_rejected(self):
        def change(v,f,m):
            p=m['patches']['front'];old=np.asarray(p['global_vertices']);duplicate=np.arange(len(v),len(v)+len(old));v=np.vstack([v,v[old]+[0,0,.003]]);start,n=p['face_start'],p['face_count'];f[start:start+n]=duplicate[np.asarray(p['local_faces'])];p['global_vertices']=duplicate
            for s in m['segments'].values():
                if s['patch']=='front':s['vertices']=duplicate[np.asarray(s['local_vertices'])].tolist()
            return v,f,m
        r=self.check_case('three_mm_open_seam','FAIL',change);self.assertGreaterEqual(r['checks']['max_seam_gap_mm'],2.999)
    def test_real_deleted_triangle_creates_rejected_hole(self):
        def change(v,f,m):
            i=100;f=np.delete(f,i,axis=0)
            for p in m['patches'].values():
                if p['face_start']<=i<p['face_start']+p['face_count']:p['local_faces']=np.delete(p['local_faces'],i-p['face_start'],axis=0);p['face_count']-=1
                elif p['face_start']>i:p['face_start']-=1
            return v,f,m
        self.check_case('deleted_face_internal_hole','FAIL',change)
    def test_flipped_triangle_is_rejected(self):
        def change(v,f,m):f[100]=f[100,::-1];m['patches']['front']['local_faces'][100]=m['patches']['front']['local_faces'][100,::-1];return v,f,m
        self.check_case('flipped_face_winding','FAIL',change)
    def test_consistently_inside_out_shell_is_rejected(self):
        def change(v,f,m):
            for p in m['patches'].values():p['local_faces']=p['local_faces'][:,::-1]
            return v,f[:,::-1],m
        r=self.check_case('entire_inside_out_shell','FAIL',change);self.assertIn('ENTIRE_GARMENT_INSIDE_OUT',r['failures'])
    def test_piercing_other_panel_is_rejected(self):
        def change(v,f,m):
            p=m['patches']['front'];boundary=set(i for s in m['segments'].values() if s['patch']=='front' for i in s['vertices']);eligible=np.array([i for i in p['global_vertices'] if i not in boundary]);i=eligible[np.argmin(np.linalg.norm(v[eligible]-[0,1.2,.10],axis=1))];v[i,2]=-.25;m['claimed_verdict']='PASS';return v,f,m
        r=self.check_case('front_point_pierces_back_despite_fake_PASS','FAIL',change,True);self.assertGreater(r['checks']['proper_self_intersections'],0)
    def test_adjacent_coplanar_fold_is_not_excluded(self):
        def change(v,f,m):
            i=100;a,b,c=f[i];candidates=np.flatnonzero(np.sum(np.isin(f,[a,b]),axis=1)==2);j=next(int(x) for x in candidates if x!=i);d=next(int(x) for x in f[j] if x not in [a,b]);v[d]=.25*v[a]+.25*v[b]+.5*v[c];return v,f,m
        r=self.check_case('shared_edge_positive_area_fold','FAIL',change,True);self.assertGreater(r['checks']['proper_self_intersections'],0)

if __name__=='__main__':unittest.main(verbosity=2)
