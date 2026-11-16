"""Fault controls for the independent GLB reader, using the shipped mesh bytes."""
import json
from pathlib import Path
import struct
import unittest

from verify_garmentcode_preview import read_glb

ROOT = Path(__file__).resolve().parents[1]


class GarmentPreviewGeometryControls(unittest.TestCase):
    def setUp(self):
        self.data = bytearray((ROOT/'web/garmentcode-preview/garment.glb').read_bytes())
        length = struct.unpack_from('<I', self.data, 12)[0]
        self.doc = json.loads(self.data[20:20+length])
        self.binary_offset = 20 + length + 8
        self.primitive = self.doc['meshes'][0]['primitives'][0]

    def offset(self, index):
        accessor = self.doc['accessors'][index]
        view = self.doc['bufferViews'][accessor['bufferView']]
        return self.binary_offset + view.get('byteOffset', 0) + accessor.get('byteOffset', 0)

    def test_real_mesh_is_readable(self):
        vertices, indices = read_glb(self.data)
        self.assertEqual(len(vertices), 3569)
        self.assertEqual(len(indices)//3, 6958)

    def test_nan_position_is_rejected(self):
        offset = self.offset(self.primitive['attributes']['POSITION'])
        struct.pack_into('<f', self.data, offset, float('nan'))
        with self.assertRaisesRegex(AssertionError, 'Non-finite'):
            read_glb(self.data)

    def test_out_of_range_index_is_rejected(self):
        accessor = self.doc['accessors'][self.primitive['indices']]
        code = {5121:'B', 5123:'H', 5125:'I'}[accessor['componentType']]
        struct.pack_into('<'+code, self.data, self.offset(self.primitive['indices']), 65535)
        with self.assertRaisesRegex(AssertionError, 'out of bounds'):
            read_glb(self.data)

    def test_truncated_file_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'header'):
            read_glb(self.data[:-8])


if __name__ == '__main__':
    unittest.main()
