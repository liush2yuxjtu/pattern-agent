"""Real accepted fixture plus fault controls for view/report/mesh binding."""
from pathlib import Path
import base64,copy,json,os,unittest
import numpy as np
from seam_inspector_binding import read_view,validate_view,audit_glb,decode_glb,digest,REPO

class BindingControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture=REPO/'experiments/fitted_tshirt/seam_inspector'
        cls.html=(fixture/'inspector.html').read_text();cls.blob=(fixture/'accepted-model.glb').read_bytes()
        cls.source=(REPO/'services/dxf-preview/public/sample.dxf').read_bytes()
        cls.data,cls.report,_=read_view(cls.html);cls.v,cls.f,cls.cert,_=decode_glb(cls.blob)
        cls.measured=audit_glb(cls.blob,cls.source,'mm');assert cls.measured['verdict']=='PASS';cls.results=[]
    @classmethod
    def tearDownClass(cls):
        out=os.environ.get('SEAM_INSPECTOR_CONTROL_EVIDENCE')
        if out:
            p=Path(out);p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text(json.dumps({'cases':cls.results,'count':len(cls.results)},indent=2)+'\n')
    def check(self,name,change=None):
        data=copy.deepcopy(self.data);report=copy.deepcopy(self.report)
        if change:
            change(data,report)
            with self.assertRaises(ValueError) as error:validate_view(data,report,self.v,self.f,self.cert,self.measured,digest(self.blob),digest(self.source))
            self.results.append({'case':name,'expected':'FAIL','observed':'FAIL','reason':str(error.exception)})
        else:
            validate_view(data,report,self.v,self.f,self.cert,self.measured,digest(self.blob),digest(self.source))
            self.results.append({'case':name,'expected':'PASS','observed':'PASS'})
    def test_exact_artifact(self):self.check('exact accepted cloud artifact')
    def test_wrong_model_digest(self):self.check('false model SHA',lambda d,r:d.update(model_sha256='0'*64))
    def test_wrong_original_digest(self):self.check('false DXF SHA',lambda d,r:d.update(source_sha256='0'*64))
    def test_display_geometry_move(self):
        def change(d,r):
            v=np.frombuffer(base64.b64decode(d['vertices']),'<f4').copy();v[0]+=.003;d['vertices']=base64.b64encode(v.tobytes()).decode()
        self.check('view geometry moved 3mm despite PASS',change)
    def test_triangle_flip(self):
        def change(d,r):
            f=np.frombuffer(base64.b64decode(d['indices']),'<u2').copy();f[0],f[1]=f[1],f[0];d['indices']=base64.b64encode(f.tobytes()).decode()
        self.check('view triangle reversed despite PASS',change)
    def test_source_piece_label(self):self.check('front/back display label swapped',lambda d,r:d['patches']['front'].update(label='后身'))
    def test_seam_label(self):self.check('wrong semantic seam label',lambda d,r:d['seams'][0].update(label='右侧缝'))
    def test_declared_pair(self):self.check('swapped sewing pair',lambda d,r:d['seams'][0].update(a='back.shoulder.left'))
    def test_missing_seam(self):self.check('omitted seam',lambda d,r:d['seams'].pop())
    def test_seam_global_vertices(self):
        def change(d,r):d['segments']['front.side.left']['ids'][0]+=1
        self.check('displayed seam not exported global vertices',change)
    def test_flat_coordinates(self):
        def change(d,r):d['segments']['front.side.left']['xy'][0][0]+=.1
        self.check('flat chart detached from GLB certificate',change)
    def test_original_curve(self):
        def change(d,r):d['segments']['front.side.left']['original'][0][0]+=1
        self.check('false original curve overlay',change)
    def test_false_measurement(self):self.check('forged zero length error',lambda d,r:d['seams'][4]['measurement'].update(length_error_mm=0))
    def test_original_not_relabelled_pass(self):self.check('original FAIL relabelled PASS',lambda d,r:d['checks'].update(original_verdict='PASS'))
    def test_missing_opening(self):self.check('intended boundary hidden',lambda d,r:d['openings'].pop())
    def test_forged_embedded_report(self):self.check('report disagrees with independent oracle',lambda d,r:r['checks'].update(max_seam_gap_mm=9))
    def test_false_material_approval(self):self.check('material approval invented',lambda d,r:r.update(material_mechanics='PASS'))
    def test_duplicate_html_certificate(self):
        with self.assertRaisesRegex(ValueError,'DUPLICATE_DATA_BLOCK'):read_view(self.html+'<script id="sp-data" type="application/json">{}</script>')
        self.results.append({'case':'duplicate HTML certificate block','expected':'FAIL','observed':'FAIL'})

if __name__=='__main__':unittest.main()
