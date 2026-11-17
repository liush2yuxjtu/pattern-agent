#!/usr/bin/env python3
"""Consumer tests of the actual embedded WASM, with independent analytic checks."""
import base64
import json
from pathlib import Path
import re
import subprocess
import unittest

import numpy as np

from oracle import ROOT


class KernelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        html=(ROOT/'web/cloth-lab/index.html').read_text()
        cls.payload=json.loads(re.search(r'<script id="payload" type="application/json">(.*?)</script>',html,re.S)[1])

    def run_kernel(self, body):
        js='''const p=JSON.parse(require('fs').readFileSync(0,'utf8'));
const w=new WebAssembly.Instance(new WebAssembly.Module(Buffer.from(p.wasm,'base64')),{}).exports;
const x=new Float32Array(w.memory.buffer,w.position_ptr(),9);
const uv=new Float32Array(w.memory.buffer,w.uv_ptr(),6);
const faces=new Int32Array(w.memory.buffer,w.face_ptr(),3);
faces.set([0,1,2]);uv.set([0,0,1,0,0,1]);
w.configure_material(200000,120000,30000,.2,.0005,.22);
'''+body
        result=subprocess.run(['node','-e',js],input=json.dumps({'wasm':self.payload['wasm']}),text=True,capture_output=True,check=True)
        return json.loads(result.stdout)

    def test_actual_wasm_exports_and_fixed_memory(self):
        result=self.run_kernel("console.log(JSON.stringify({memory:w.memory.buffer.byteLength,step:typeof w.step,body:typeof w.collision_probe,material:typeof w.material_probe}));")
        self.assertEqual(result,dict(memory=16777216,step='function',body='function',material='function'))

    def test_unconstrained_gravity_matches_analytic_recurrence(self):
        result=self.run_kernel('''x.set([0,0,0,1,0,0,0,1,0]);w.configure_cloth(3,1);w.finalize_seams();w.set_collision(0);w.step(12,0);console.log(JSON.stringify(Array.from(x)));''')
        initial=np.array([[0,0,0],[1,0,0],[0,1,0]],dtype=float)
        velocity=displacement=0
        for _ in range(12):
            velocity=.993*velocity-9.81/(120*120)
            displacement+=velocity
        expected=initial.copy();expected[:,1]+=displacement
        self.assertLess(np.max(abs(np.array(result).reshape(-1,3)-expected)),2e-6)

    def test_elastic_step_reduces_stretched_triangle_energy(self):
        result=self.run_kernel('''x.set([0,0,0,1.1,0,0,0,1,0]);w.configure_cloth(3,1);w.finalize_seams();w.set_collision(0);const before=Array.from(x);w.step(1,0);console.log(JSON.stringify({before,after:Array.from(x)}));''')
        def energy(points):
            p=np.array(points).reshape(-1,3);F=np.column_stack((p[1]-p[0],p[2]-p[0]));E=(F.T@F-np.eye(2))/2
            den=1-.2**2*120000/200000
            return .5*(200000/den*E[0,0]**2+2*.2*120000/den*E[0,0]*E[1,1]+120000/den*E[1,1]**2)+2*30000*E[0,1]**2
        self.assertLess(energy(result['after']),energy(result['before'])*.99)
        self.assertTrue(np.isfinite(result['after']).all())


if __name__=='__main__':unittest.main(verbosity=2)
