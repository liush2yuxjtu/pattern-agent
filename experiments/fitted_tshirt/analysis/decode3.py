from pathlib import Path
b=next(Path('../source').glob('*.prj')).read_bytes()
# Test common permutations on arbitrary block sizes, score just beginning.
b=b[:1100]
for n in range(3,130):
 for off in range(n):
  for p in [list(range(0,n,2))+list(range(1,n,2)),list(range(1,n,2))+list(range(0,n,2))]:
   for inv in [False,True]:
    if inv:p=[p.index(i) for i in range(n)]
    out=bytearray(b)
    for i in range(off,len(b)-n+1,n):out[i:i+n]=bytes(b[i+j] for j in p)
    score=out.count('面料'.encode())+out.count(b'no name')
    if score>3:print(n,off,inv,score,repr(out[:550]))
