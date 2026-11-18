import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {buildHinges,foldFields} from '../../freesewing_cloth_lab/source/fold-fields.js';

const directory=path.resolve(process.argv[2]);
const input=JSON.parse(fs.readFileSync(path.join(directory,'input.json'),'utf8'));
const file=path.join(directory,'trajectory.json'),recording=JSON.parse(fs.readFileSync(file,'utf8'));
const triangles=Uint32Array.from(input.triangles.flat().map(id=>input.global_ids[id]));
const cornerUV=input.triangles.flatMap(face=>face.flatMap(id=>input.uv[id]));
const hinges=buildHinges(triangles,cornerUV),count=Math.max(...input.global_ids)+1;
const first=new Int32Array(count).fill(-1);input.global_ids.forEach((gid,i)=>{if(first[gid]<0)first[gid]=i;});
for(const frame of recording.frames){
 const bytes=Buffer.from(frame.positions,'base64'),positions=new Float32Array(bytes.buffer,bytes.byteOffset,bytes.byteLength/4),welded=new Float32Array(count*3);
 first.forEach((raw,gid)=>welded.set(positions.subarray(raw*3,raw*3+3),gid*3));
 const result=foldFields(welded,triangles,hinges),fields=new Float32Array(input.triangles.length*2);
 for(let i=0;i<input.triangles.length;i++){fields[2*i]=result.triangleAngle_deg[i];fields[2*i+1]=result.triangleCurvature_per_m[i];}
 frame.folds=Buffer.from(fields.buffer).toString('base64');
}
recording.fold_derivation={hinges:hinges.length,flat_degrees:0,foldback_degrees:180,
 source:'experiments/freesewing_cloth_lab/source/fold-fields.js',
 source_sha256:crypto.createHash('sha256').update(fs.readFileSync(new URL('../../freesewing_cloth_lab/source/fold-fields.js',import.meta.url))).digest('hex'),
 scope:'Actual signed adjacent-face dihedrals and geometric curvature; no permanent crease law.'};
fs.writeFileSync(file,JSON.stringify(recording));
console.log(JSON.stringify({frames:recording.frames.length,hinges:hinges.length}));
