"""Positive perturbations, unsupported inputs and independent GLB integrity checks."""
import hashlib,io,json,struct,unittest,zipfile
from pathlib import Path
import numpy as np
from fastapi.testclient import TestClient
from app import app
from converter.core import convert_dxf,parse_dxf,ConversionError,MAX_INPUT_BYTES
ROOT=Path(__file__).resolve().parents[1]
SAMPLE=(ROOT/'public/sample.dxf').read_bytes()

def dxf(polys):
    rows=['0','SECTION','2','ENTITIES']
    for p in polys:
        rows+=['0','POLYLINE','8','11','66','1','70','0']
        for x,y in p:rows+=['0','VERTEX','8','11','10',format(float(x),'.9f'),'20',format(float(y),'.9f')]
        rows+=['0','SEQEND']
    rows+=['0','ENDSEC','0','EOF']
    return ('\r\n'.join(rows)+'\r\n').encode()

def inspect_glb(blob):
    magic,version,total=struct.unpack_from('<III',blob);assert magic==0x46546c67 and version==2 and total==len(blob)
    length,kind=struct.unpack_from('<II',blob,12);assert kind==0x4e4f534a
    doc=json.loads(blob[20:20+length]);start=20+length;blength,bkind=struct.unpack_from('<II',blob,start);assert bkind==0x004e4942 and start+8+blength==len(blob);binary=blob[start+8:]
    arrays=[];triangles=0
    for mesh in doc['meshes']:
        p=mesh['primitives'][0];a=doc['accessors'][p['attributes']['POSITION']];view=doc['bufferViews'][a['bufferView']];offset=view['byteOffset'];assert offset+view['byteLength']<=len(binary)
        vertices=np.frombuffer(binary,dtype='<f4',count=a['count']*3,offset=offset).reshape(-1,3);assert np.isfinite(vertices).all()
        a=doc['accessors'][p['indices']];view=doc['bufferViews'][a['bufferView']];faces=np.frombuffer(binary,dtype='<u4',count=a['count'],offset=view['byteOffset']).reshape(-1,3);assert faces.max()<len(vertices)
        areas=np.linalg.norm(np.cross(vertices[faces[:,1]]-vertices[faces[:,0]],vertices[faces[:,2]]-vertices[faces[:,0]]),axis=1);assert np.all(areas>0)
        arrays.append(vertices);triangles+=len(faces)
    return doc,np.vstack(arrays),triangles

class ConversionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.base=convert_dxf(SAMPLE,units='mm');cls.doc,cls.vertices,cls.triangles=inspect_glb(cls.base.glb)
    def test_actual_mesh_and_repeatability(self):
        other=convert_dxf(SAMPLE,units='mm');self.assertEqual(self.base.glb,other.glb);self.assertEqual(self.base.report,other.report);self.assertGreater(self.triangles,30000);self.assertEqual(len(self.doc['meshes']),1);self.assertEqual(self.base.report['source_patches'],5);self.assertEqual(self.base.report['strict_seam_and_intersection_release'],'PASS');self.assertEqual(self.base.report['physical_fit'],'NOT_RUN');self.assertTrue(.45<np.ptp(self.vertices[:,1])<.8);self.assertLess(self.base.report['connection_verification']['checks']['max_3d_seam_length_error_mm'],2);self.assertAlmostEqual(next(s['sewn_3d_length_mm'] for s in self.base.report['connection_verification']['checks']['seams'] if s['name']=='underarm.left'),455.842,delta=.1)
    def test_reordered_reversed_translated_geometry(self):
        p,_=parse_dxf(SAMPLE);rng=np.random.default_rng(713);order=rng.permutation(len(p));raw=dxf([(p[i][::-1] if i%2 else p[i])+[1234,-5678] for i in order]);r=convert_dxf(raw,units='mm');_,v,_=inspect_glb(r.glb);self.assertLess(r.report['matching']['max_sampled_deviation_mm'],.00001);np.testing.assert_allclose(v.min(0),self.vertices.min(0),atol=2e-6);np.testing.assert_allclose(v.max(0),self.vertices.max(0),atol=2e-6)
    def test_centimetre_input_uses_explicit_units(self):
        p,_=parse_dxf(SAMPLE);r=convert_dxf(dxf([q/10 for q in p]),units='cm');_,v,_=inspect_glb(r.glb);np.testing.assert_allclose(v.min(0),self.vertices.min(0),atol=2e-6);np.testing.assert_allclose(v.max(0),self.vertices.max(0),atol=2e-6)
    def test_scale_changes_actual_geometry(self):
        p,_=parse_dxf(SAMPLE);r=convert_dxf(dxf([q*1.1 for q in p]),units='mm');_,v,_=inspect_glb(r.glb);self.assertNotEqual(r.report['output_sha256'],self.base.report['output_sha256']);self.assertAlmostEqual(float(np.ptp(v[:,1])/np.ptp(self.vertices[:,1])),1.1,places=5)
    def test_local_contour_change_changes_output(self):
        p,_=parse_dxf(SAMPLE);p[96][1:-1]=p[96][1:-1]+[2,0];r=convert_dxf(dxf(p),units='mm');inspect_glb(r.glb);self.assertNotEqual(r.glb,self.base.glb)
    def test_open_source_contour_is_rejected(self):
        p,_=parse_dxf(SAMPLE);p[96]=p[96]+[2,0]
        with self.assertRaises(ConversionError) as cm:convert_dxf(dxf(p),units='mm')
        self.assertEqual(cm.exception.code,'SEWING_ASSEMBLY_REJECTED')
    def test_unrelated_pattern_is_rejected(self):
        with self.assertRaises(ConversionError) as cm:convert_dxf(dxf([np.array([[0,0],[200,0],[200,400],[0,400],[0,0]])]),units='mm')
        self.assertEqual(cm.exception.code,'PROFILE_REQUIRED')
    def test_same_count_wrong_geometry_rejected(self):
        p,_=parse_dxf(SAMPLE);p[96]=p[96]+[60,0]
        with self.assertRaises(ConversionError) as cm:convert_dxf(dxf(p),units='mm')
        self.assertEqual(cm.exception.code,'PROFILE_REQUIRED')
    def test_invalid_units_size_and_coordinate(self):
        for data,units,code in [(SAMPLE,'','UNITS_REQUIRED'),(SAMPLE,'cm','UNITS_OR_SCALE'),(b'bad','mm','INVALID_DXF'),(b'x'*(MAX_INPUT_BYTES+1),'mm','INPUT_SIZE')]:
            with self.subTest(code=code),self.assertRaises(ConversionError) as cm:convert_dxf(data,units=units)
            self.assertEqual(cm.exception.code,code)
        p,_=parse_dxf(SAMPLE);p[0][0,0]=float('nan')
        with self.assertRaises(ConversionError) as cm:convert_dxf(dxf(p),units='mm')
        self.assertEqual(cm.exception.code,'INVALID_GEOMETRY')
    def test_no_persistence_or_job_claims(self):
        with TestClient(app) as c:
            h=c.get('/api/health').json();self.assertEqual(h['execution'],'synchronous_stateless');self.assertEqual(h['storage'],'no_uploaded_file_persistence');self.assertFalse(c.get('/api/profiles').json()['profiles'][0]['arbitrary_garment_dxf'])
    def test_http_contract_bundle_and_errors(self):
        with TestClient(app) as c:
            result=c.post('/api/preview?units=mm&format=glb',content=SAMPLE,headers={'Content-Type':'application/dxf'});self.assertEqual(result.status_code,200);self.assertEqual(result.content,self.base.glb);self.assertEqual(hashlib.sha256(result.content).hexdigest(),result.headers['x-output-sha256'])
            response=c.post('/api/preview?units=mm&format=bundle',content=SAMPLE);self.assertEqual(response.status_code,200)
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                self.assertIsNone(z.testzip());self.assertEqual(z.read('model.glb'),self.base.glb);self.assertEqual(json.loads(z.read('report.json'))['output_sha256'],self.base.report['output_sha256']);self.assertEqual(z.read('original-input.dxf'),SAMPLE);self.assertEqual(json.loads(z.read('connection-verification.json'))['verdict'],'PASS');self.assertIn(b'<svg',z.read('corrected-seam-lines.svg'));self.assertNotIn(b'__GENERATED_GLB__',z.read('preview.html'));self.assertNotIn(b'__RENDERER_JS__',z.read('preview.html'))
            for query,data,status in [('units=mm',b'bad',400),('units=mm&format=unknown',SAMPLE,400),('units=mm&profile=any',SAMPLE,422),('units=mm',b'x'*(MAX_INPUT_BYTES+1),413)]:
                r=c.post('/api/preview?'+query,content=data);self.assertEqual(r.status_code,status);self.assertEqual(r.json()['status'],'rejected')
            self.assertEqual(c.get('/api/no-such-job').status_code,404)

if __name__=='__main__':unittest.main(verbosity=2)
