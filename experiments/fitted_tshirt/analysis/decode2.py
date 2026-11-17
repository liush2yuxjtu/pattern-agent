from pathlib import Path
b=next(Path('../source').glob('*.prj')).read_bytes()
for n in range(2,130,2):
 for off in range(n):
  for mode in [0,1]:
   out=bytearray(b)
   for i in range(off,len(b)-n+1,n):
    q=b[i:i+n]
    if mode==0:
     out[i:i+n:2]=q[:n//2];out[i+1:i+n:2]=q[n//2:]
    else:out[i:i+n]=q[::2]+q[1::2]
   score=sum(out.count(s) for s in ['面料'.encode(),'前中'.encode(),'后中'.encode(),b'no name'])
   if score>5:
    print(n,off,mode,score,repr(out[:550]));Path(f'work/prj_decode_{n}_{off}_{mode}.bin').write_bytes(out)
