export function decodeBlock(block){
 if(block.format!=='float32-xor-byteplanes/1'||!Number.isSafeInteger(block.frames)||!Number.isSafeInteger(block.width)||block.frames<1||block.width<1)throw Error('Invalid physical block metadata');
 const bytes=Uint8Array.from(atob(block.base64),c=>c.charCodeAt(0)),total=block.frames*block.width;
 if(bytes.length!==total*4)throw Error('Truncated physical block');
 const words=new Uint32Array(total),view=new Uint8Array(words.buffer);
 for(let plane=0;plane<4;plane++)for(let i=0;i<total;i++)view[i*4+plane]=bytes[plane*total+i];
 for(let frame=1;frame<block.frames;frame++)for(let j=0;j<block.width;j++)words[frame*block.width+j]^=words[(frame-1)*block.width+j];
 return new Float32Array(words.buffer);
}
export function encodeBase64(values){
 const bytes=new Uint8Array(values.buffer,values.byteOffset,values.byteLength);let string='';
 for(let i=0;i<bytes.length;i+=32768)string+=String.fromCharCode(...bytes.subarray(i,i+32768));
 return btoa(string);
}
