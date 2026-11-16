"""Negative controls prove that the delivery checker rejects real faults."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

import fitz

from verify_artifacts import ROOT,verify


class DeliveryNegativeControls(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.directory=Path(self.temp.name)/'site'
        shutil.copytree(ROOT/'dist',self.directory)
        self.bundle=self.directory/'patterns/straight-skirt-eu40'

    def tearDown(self): self.temp.cleanup()

    def refresh_manifest(self,path,remove=False):
        manifest_path=self.directory/'build.json'
        manifest=json.loads(manifest_path.read_text())
        key=str(path.relative_to(self.directory))
        if remove: manifest['files'].pop(key)
        else: manifest['files'][key]=hashlib.sha256(path.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest))

    def test_healthy_delivery_passes(self):
        self.assertEqual(verify(self.directory)['verdict'],'PASS')

    def test_half_size_calibration_is_rejected(self):
        path=self.bundle/'print-a4.pdf'
        original=fitz.open(path)
        changed=fitz.open()
        cover=changed.new_page(width=original[0].rect.width,height=original[0].rect.height)
        cover.draw_rect(fitz.Rect(30,30,30+50/25.4*72,30+50/25.4*72))
        cover.insert_text((30,20),'13 pages to print')
        changed.insert_pdf(original,from_page=1)
        payload=changed.tobytes()
        original.close(); changed.close(); path.write_bytes(payload)
        self.refresh_manifest(path)
        with self.assertRaisesRegex(AssertionError,'100 x 100 mm'): verify(self.directory)

    def test_missing_measurements_is_rejected(self):
        path=self.bundle/'measurements-eu40.slm'
        path.unlink(); self.refresh_manifest(path,remove=True)
        with self.assertRaisesRegex(AssertionError,'Missing measurement'): verify(self.directory)

    def test_wrong_fold_edge_is_rejected(self):
        path=self.bundle/'straight-skirt-eu40.sloper'
        data=json.loads(path.read_text())
        next(o for o in data['objects'] if o.get('name')=='Front')['foldEdge']=999999
        path.write_text(json.dumps(data)); self.refresh_manifest(path)
        with self.assertRaisesRegex(AssertionError,'front fold'): verify(self.directory)

    def test_broken_outline_is_rejected(self):
        path=self.bundle/'straight-skirt-eu40.sloper'
        data=json.loads(path.read_text())
        next(o for o in data['objects'] if o.get('name')=='B_Waist_centre')['start']=999999
        path.write_text(json.dumps(data)); self.refresh_manifest(path)
        with self.assertRaisesRegex(AssertionError,'Disconnected native outline'): verify(self.directory)

    def test_extra_archive_file_is_rejected(self):
        path=self.bundle.with_suffix('.zip')
        with zipfile.ZipFile(path,'a') as z: z.writestr('unexpected.txt','unexpected content')
        self.refresh_manifest(path)
        with self.assertRaisesRegex(AssertionError,'Archive file set'): verify(self.directory)


if __name__=='__main__': unittest.main()
