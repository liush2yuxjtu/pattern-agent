#!/usr/bin/env python3
"""Fault-inject actual receipts without changing completed outputs or main grader."""
import argparse,pathlib,tempfile,json,cv2
from commerce_receipt_adapter import audit,sha
def main():
    P=pathlib.Path
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--candidate',required=True);p.add_argument('--source',required=True);p.add_argument('--out',required=True);a=p.parse_args();source=P(a.candidate).resolve();results=[]
    with tempfile.TemporaryDirectory(prefix='receipt-adapter-controls-') as temp:
     for name in ['replace_output','wrong_input_hash','non_equivalent_png']:
      d=P(temp)/name;d.mkdir()
      for q in source.iterdir():(d/q.name).symlink_to(q,target_is_directory=q.is_dir())
      (d/'receipts').unlink();(d/'receipts').mkdir()
      for q in (source/'receipts').iterdir():(d/'receipts'/q.name).symlink_to(q)
      receipt=d/'receipts/front.json';r=json.loads(receipt.read_text());receipt.unlink()
      if name=='replace_output':
       (d/'images').unlink();(d/'images').mkdir()
       for q in (source/'images').iterdir():(d/'images'/q.name).symlink_to(q)
       im=cv2.imread(str(d/'images/front.png'));(d/'images/front.png').unlink();im[:100,:100]=[0,255,0];cv2.imwrite(str(d/'images/front.png'),im)
      elif name=='wrong_input_hash':
       key=next(iter(r['input_hashes']));r['input_hashes'][key]='0'*64
      else:
       args=r.get('arguments',r.get('args'));key=next(x for x in r['input_hashes'] if 'original.' in x);im=cv2.imread(key);im[:100,:100]=[0,255,0];fake=d/'non-equivalent.png';cv2.imwrite(str(fake),im);del r['input_hashes'][key];r['input_hashes'][str(fake)]=sha(fake);args['referenced_image_paths']=[str(fake) if x==key else x for x in args['referenced_image_paths']]
      receipt.write_text(json.dumps(r));report=audit(d,a.source);assert report['verdict']=='FAIL',name;results.append(dict(name=name,passed=True,actual_verdict=report['verdict'],failures=report['failures']))
    out=P(a.out);out.parent.mkdir(parents=True,exist_ok=True);report=dict(adapter_sha256=sha(P(__file__).with_name('commerce_receipt_adapter.py')),controls=results,all_passed=all(x['passed'] for x in results));out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))


if __name__ == "__main__":
    main()
