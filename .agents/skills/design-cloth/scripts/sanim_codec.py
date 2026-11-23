"""Style3D V4 pose-track codec reused from the ten-motion workflow."""
from copy import deepcopy
import json
import struct
from zipfile import ZIP_DEFLATED, ZipFile

TRANSFORM = struct.Struct('<9f')
BONES = 101
STRIDE = 16 + BONES * TRANSFORM.size
def read_native(path):
    with ZipFile(path) as archive:
        document = json.loads(archive.read('skeletonAnimation.json'))
        binary = archive.read('sbin')
    native = (document['objects'] if 'objects' in document else document['_objectsArrays'][0])[0]
    size = native['poseTrack']['size']
    total = struct.unpack_from('<Q', binary)[0]
    indexes_at = 8 + total * STRIDE
    assert size == indexes_at + 8 + 4*total
    assert struct.unpack_from('<Q',binary,indexes_at)[0] == total
    assert struct.unpack_from(f'<{total}I',binary,indexes_at+8) == tuple(range(total))
    return document, native, binary, total

def read_frame(binary, index):
    offset = 8 + index*STRIDE
    assert struct.unpack_from('<Q',binary,offset)[0] == BONES
    assert struct.unpack_from('<Q',binary,offset+8+BONES*TRANSFORM.size)[0] == 0
    return [
        {'translate':row[:3], 'rotate':row[3:6], 'scale':row[6:]}
        for row in TRANSFORM.iter_unpack(binary[offset+8:offset+STRIDE-8])
    ]

def write_animation(path, source, frames):
    old_document, _, old_binary, _ = source
    document = deepcopy(old_document)
    native = (document['objects'] if 'objects' in document else document['_objectsArrays'][0])[0]
    document['_fileName'] = native['_name'] = path.stem
    native['previewPath'] = ''
    count = len(frames)
    clip = bytearray(struct.pack('<Q',count))
    for frame in frames:
        assert len(frame) == BONES
        clip += struct.pack('<Q',BONES)
        for joint in frame:
            clip += TRANSFORM.pack(*joint['translate'],*joint['rotate'],*joint['scale'])
        clip += bytes(8)
    clip += struct.pack('<Q',count)
    clip += struct.pack(f'<{count}I',*range(count))
    tracks = sorted((spec['offset'],key,spec) for key,spec in native.items()
                    if isinstance(spec,dict) and 'offset' in spec and key != 'poseTrack')
    native['poseTrack']['size'] = len(clip)
    for original_offset,key,spec in tracks:
        spec['offset'] = len(clip)
        clip += old_binary[original_offset:original_offset+spec['size']]
    with ZipFile(path,'w',ZIP_DEFLATED) as archive:
        archive.writestr('skeletonAnimation.json',json.dumps(document,ensure_ascii=False))
        archive.writestr('sbin',clip)
    with ZipFile(path) as archive:
        assert archive.testzip() is None
    _, _, verified, total = read_native(path)
    assert total == count
    for index in (0,count//2,count-1):
        restored = read_frame(verified,index)
        assert abs(restored[0]['translate'][1]-frames[index][0]['translate'][1]) < 1e-4
