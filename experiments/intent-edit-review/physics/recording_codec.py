"""Lossless temporal XOR and byte-plane layout. Never quantizes any float."""
import base64
from copy import deepcopy
import numpy as np

FIELDS = ('positions','previous','fields','contacts','folds')

def encode(recording):
    result=deepcopy(recording);blocks={};frames=recording['frames']
    for key in FIELDS:
        raw=[base64.b64decode(f[key],validate=True) for f in frames]
        if any(len(r)!=len(raw[0]) or len(r)%4 for r in raw):raise ValueError('Invalid physical array width')
        values=np.frombuffer(b''.join(raw),dtype='<u4').reshape(len(frames),-1)
        delta=values.copy();delta[1:]^=values[:-1]
        planes=delta.view('u1').reshape(len(frames),-1,4).transpose(2,0,1).copy()
        blocks[key]={'format':'float32-xor-byteplanes/1','frames':len(frames),'width':values.shape[1],
                     'base64':base64.b64encode(planes.tobytes()).decode()}
        for index,frame in enumerate(result['frames']):frame[key]={'block':key,'frame':index}
    return result,blocks

def decode(recording,blocks):
    result=deepcopy(recording)
    for key in FIELDS:
        block=blocks[key];count,width=block['frames'],block['width']
        if block['format']!='float32-xor-byteplanes/1' or count!=len(result['frames']) or width<=0:raise ValueError('Invalid block metadata')
        planes=np.frombuffer(base64.b64decode(block['base64'],validate=True),dtype='u1').reshape(4,count,width)
        delta=planes.transpose(1,2,0).copy().reshape(count,width*4).view('<u4')
        values=np.bitwise_xor.accumulate(delta,axis=0)
        for index,frame in enumerate(result['frames']):frame[key]=base64.b64encode(values[index].tobytes()).decode()
    return result
