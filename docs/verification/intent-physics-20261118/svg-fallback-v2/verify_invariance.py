#!/usr/bin/env python3
"""Read-only old-HTML -> draft payload, actual-run and Git archive byte audit.

Only this script's report directory is written. No viewer, HTML, physical data,
archive, Git index, or source file is modified. No browser/physics is executed.
"""
from pathlib import Path
import argparse,base64,copy,datetime,gzip,hashlib,json,re,subprocess,sys,traceback
import numpy as np
ROOT=Path('/workspace/work/pattern-agent-publish')
HTML=Path('web/intent-edit-review/physics/index.html')
DEFAULT_BASE='a351a523359e66ea7ef1d03a96b51d802611924b'
OUTROOT=ROOT/'work/intent-physics/ui-data-invariance'
FIELDS=('positions','previous','fields','contacts','folds')
RUNS={'baseline':('baseline-run37','baseline'),'03_cuff_width':('cuff-run37','cuff-width')}
VIEWERS=('viewer.mjs','viewer.css','viewer.template.html','recording-codec.mjs')
VIEWER_DIR=ROOT/'experiments/intent-edit-review/physics'

def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def load(raw):return json.loads(raw,parse_constant=lambda value:(_ for _ in ()).throw(ValueError('Nonfinite JSON '+value)))
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def resolve(ref):return git('rev-parse',ref+'^{commit}').decode().strip()

class GitBlobs:
    def __init__(self,ref):
        self.ref=ref;self.proc=subprocess.Popen(['git','cat-file','--batch'],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    def get(self,path):
        text=str(path)
        if '\n' in text:raise ValueError('Unsupported newline Git path')
        self.proc.stdin.write((self.ref+':'+text+'\n').encode());self.proc.stdin.flush();header=self.proc.stdout.readline().decode().strip()
        if header.endswith(' missing'):return None,{'missing':True,'header':header}
        oid,kind,size=header.split();size=int(size);parts=[];remaining=size
        while remaining:
            block=self.proc.stdout.read(remaining)
            if not block:raise EOFError('Incomplete Git blob '+text)
            parts.append(block);remaining-=len(block)
        if self.proc.stdout.read(1)!=b'\n':raise ValueError('Bad Git batch framing')
        return b''.join(parts),{'oid':oid,'type':kind,'bytes':size}
    def close(self):
        self.proc.stdin.close();self.proc.stdout.close();error=self.proc.stderr.read();code=self.proc.wait()
        if code:raise RuntimeError(error.decode())


def payload(raw):
    found=re.findall(rb'<script[^>]*id="physics-payload"[^>]*>(.*?)</script>',raw,re.S)
    if len(found)!=1:raise ValueError('Expected exactly one physics-payload')
    compressed=base64.b64decode(found[0].strip(),validate=True);plain=gzip.decompress(compressed)
    return load(plain),{'compressed_sha256':sha(compressed),'json_sha256':sha(plain),'json_bytes':len(plain)}


def differences(a,b,path='$'):
    if type(a)!=type(b):return [path]
    if isinstance(a,dict):
        out=[]
        for key in sorted(set(a)|set(b)):
            if key not in a or key not in b:out.append(path+'.'+key)
            else:out.extend(differences(a[key],b[key],path+'.'+key))
        return out
    if isinstance(a,list):
        if len(a)!=len(b):return [path]
        out=[]
        for i,(x,y) in enumerate(zip(a,b)):out.extend(differences(x,y,f'{path}[{i}]'))
        return out
    return [] if a==b else [path]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-ref',default=DEFAULT_BASE)
    parser.add_argument('--archive-ref',default='HEAD')
    parser.add_argument('--draft',type=Path,default=ROOT/HTML)
    parser.add_argument('--expected-draft-sha256')
    parser.add_argument('--viewer-receipt',type=Path,action='append',default=[])
    parser.add_argument('--output',type=Path,default=OUTROOT/'latest')
    args=parser.parse_args();output=args.output.resolve()
    if not output.is_relative_to(OUTROOT):raise ValueError('Reports may only be written under '+str(OUTROOT))
    output.mkdir(parents=True,exist_ok=True)
    report={'verdict':'RUNNING','scope':'Data/byte invariance only; no browser, rendering, physical calculation or new fit approval.',
            'command':[sys.executable,*sys.argv],'script_sha256':sha(Path(__file__).read_bytes()),
            'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'failures':[],'field_proofs':[]}
    failures=report['failures'];details={'archive_files':[],'manifest_files':[],'original_models':[],'source_files':[],'frame_arrays':[]}
    def require(ok,message,**context):
        if not ok:failures.append({'message':message,**context})
        return bool(ok)
    def equal_field(path,a,b):
        aa=canonical(a);bb=canonical(b);same=aa==bb
        report['field_proofs'].append({'path':path,'byte_identical_canonical_json':same,'old_sha256':sha(aa),'draft_sha256':sha(bb),'old_bytes':len(aa),'draft_bytes':len(bb)})
        require(same,'Non-UI field changed',path=path)
        return same
    blobs=None;baseblobs=None
    try:
        base=resolve(args.base_ref);head=resolve(args.archive_ref);start_head=resolve('HEAD')
        report.update(base_commit=base,archive_commit=head,git_head_at_start=start_head)
        old_raw=git('show',base+':'+str(HTML));new_raw=args.draft.read_bytes()
        old_hash=sha(old_raw);new_hash=sha(new_raw)
        report.update(old_html_sha256=old_hash,draft_html_sha256=new_hash,old_html_bytes=len(old_raw),draft_html_bytes=len(new_raw))
        require(old_hash.startswith('571fd146'),'Baseline is not the original published HTML')
        if args.expected_draft_sha256:require(new_hash==args.expected_draft_sha256,'Draft hash differs from the requested immutable candidate')
        old,old_meta=payload(old_raw);new,new_meta=payload(new_raw);report['embedded_payload']={'old':old_meta,'draft':new_meta}
        del old_raw,new_raw
        changes=differences(old,new)
        allowed={f'$.viewer_sources.{name}' for name in VIEWERS[:3]}
        allowed|={'$.engines[5].verdict','$.engine_receipts.viewer_receipt_sha256'}
        allowed|={f'$.cases[{i}].engine_verdicts[5]' for i in range(2)}
        # Receipt arrays may have the same length but changed hashes.
        def permitted(path):return path in allowed or bool(re.fullmatch(r'\$\.engine_receipts\.viewer_receipt_sha256\[\d+\]',path))
        unexpected=[path for path in changes if not permitted(path)]
        report['payload_changed_paths']=changes;report['unexpected_changed_paths']=unexpected
        require(not unexpected,'Unexpected payload mutations',paths=unexpected)
        require(set(old)==set(new)=={'format','cases','viewer_sources','engines','engine_receipts'},'Unexpected payload schema')
        equal_field('$.format',old['format'],new['format'])
        require(len(old['cases'])==len(new['cases'])==2,'Expected the same two complete cases')
        require(set(old['viewer_sources'])==set(new['viewer_sources'])==set(VIEWERS),'Viewer source key set changed')
        viewer_changes=[name for name in VIEWERS if old['viewer_sources'][name]!=new['viewer_sources'][name]]
        require(set(viewer_changes)==set(VIEWERS[:3]),'Expected only the three renderer/viewer source changes',changed=viewer_changes)
        blobs=GitBlobs(head);baseblobs=GitBlobs(base)
        for name in VIEWERS:
            relative=Path('experiments/intent-edit-review/physics')/name;old_source,_=baseblobs.get(relative);current=(ROOT/relative).read_bytes()
            require(old_source is not None and sha(old_source)==old['viewer_sources'][name],'Old viewer source binding mismatch',file=name)
            require(sha(current)==new['viewer_sources'][name],'Draft viewer source binding mismatch',file=name)
        receipts={}
        targets=new['engine_receipts']['viewer_receipt_sha256']
        require(set(new['engine_receipts'])=={'viewer_receipt_sha256','scope'},'Unexpected engine receipt metadata schema')
        equal_field('$.engine_receipts.scope',old['engine_receipts']['scope'],new['engine_receipts']['scope'])
        if targets:
            candidates=set(args.viewer_receipt)
            for directory in [ROOT/'work/intent-physics',VIEWER_DIR/'evidence']:
                if directory.exists():candidates.update(directory.rglob('*receipt*.json'))
            for path in sorted(candidates):
                if not path.is_file():continue
                raw=path.read_bytes();digest=sha(raw)
                if digest in targets:receipts[digest]={'path':str(path),'sha256':digest,'data':load(raw)}
            require(set(receipts)==set(targets),'Declared UI receipts not all resolvable',unresolved=sorted(set(targets)-set(receipts)))
        report['ui_receipt_bindings']=[{k:v for k,v in row.items() if k!='data'} for row in receipts.values()]
        case_reports=[]
        for i,(a,b) in enumerate(zip(old['cases'],new['cases'])):
            case=b['input']['case'];prefix=f'$.cases[{i}]'
            require(case==a['input']['case'] and case in RUNS,'Case identity/order changed',case=case)
            require(set(a)==set(b),'Case schema changed',case=case)
            for key in sorted(set(a)&set(b)):
                if key=='engine_verdicts':continue
                equal_field(prefix+'.'+key,a[key],b[key])
            for key in sorted(b['input']):equal_field(prefix+'.input.'+key,a['input'][key],b['input'][key])
            for key in sorted(b['audit']):equal_field(prefix+'.audit.'+key,a['audit'][key],b['audit'][key])
            for key in sorted(b['controls']):equal_field(prefix+'.controls.'+key,a['controls'][key],b['controls'][key])
            for key in sorted(b['source_package']):equal_field(prefix+'.source_package.'+key,a['source_package'][key],b['source_package'][key])
            for j in range(7):
                if j!=5:equal_field(prefix+f'.engine_verdicts[{j}]',a['engine_verdicts'][j],b['engine_verdicts'][j])
            matching=[row for row in receipts.values() if row['data'].get('verdict')=='PASS' and row['data'].get('viewer_sources')==new['viewer_sources'] and row['data'].get('case')==case and row['data'].get('input_sha256')==b['audit']['input_sha256'] and row['data'].get('recording_sha256')==b['audit']['recording_sha256']]
            expected_ui='PASS' if matching else 'NOT_RUN'
            require(b['engine_verdicts'][5]==expected_ui,'UI status not supported by current source/data-bound receipts',case=case,expected=expected_ui,actual=b['engine_verdicts'][5])
            run=ROOT/'work/intent-physics'/RUNS[case][0]
            input_raw=(run/'input.json').read_bytes();record_raw=(run/'trajectory.json').read_bytes();actual_input=load(input_raw);actual_record=load(record_raw)
            require(canonical(b['input'])==canonical(actual_input),'Embedded input differs from actual run',case=case)
            require(b['audit']['input_sha256']==sha(input_raw)==actual_record['input_sha256'],'Run input hash binding mismatch',case=case)
            require(b['audit']['recording_sha256']==sha(record_raw),'Actual recording hash binding mismatch',case=case)
            for key,file in [('audit','audit.json'),('controls','controls/manifest.json')]:
                raw=(run/file).read_bytes();require(canonical(b[key])==canonical(load(raw)),'Embedded report differs from actual run',case=case,field=key)
            require(canonical(b['conditions'])==canonical((ROOT/'experiments/intent-edit-review/physics/results'/RUNS[case][1]/'experiment-conditions.yaml').read_text()),'Executed conditions text differs from archive',case=case)
            packed=b['recording'];frames=packed['frames'];original_frames=actual_record['frames'];count=len(original_frames)
            require(count==len(frames)==61,'Expected all 61 recorded states',case=case)
            require(set(b['recording_blocks'])==set(FIELDS),'Missing/extra lossless recorded field block',case=case)
            rebuilt=dict(packed);rebuilt['frames']=[dict(frame) for frame in frames]
            for key,block in b['recording_blocks'].items():
                n,width=block['frames'],block['width'];require(block['format']=='float32-xor-byteplanes/1' and n==count and width>0,'Invalid block metadata',case=case,field=key)
                raw=base64.b64decode(block['base64'],validate=True);require(len(raw)==4*n*width,'Byte-plane block width mismatch',case=case,field=key)
                planes=np.frombuffer(raw,dtype='u1').reshape(4,n,width)
                delta=planes.transpose(1,2,0).copy().reshape(n,width*4).view('<u4')
                values=np.bitwise_xor.accumulate(delta,axis=0)
                for index in range(count):
                    decoded=values[index].astype('<u4',copy=False).tobytes();expected=base64.b64decode(original_frames[index][key],validate=True)
                    equal=decoded==expected
                    require(equal,'Actual recorded float32 bytes differ',case=case,frame=index,field=key)
                    require(frames[index][key]=={'block':key,'frame':index},'Packed frame points to wrong lossless block',case=case,frame=index,field=key)
                    rebuilt['frames'][index][key]=base64.b64encode(decoded).decode()
                    details['frame_arrays'].append({'case':case,'frame':index,'field':key,'bytes':len(decoded),'sha256':sha(decoded),'byte_identical_to_actual_run':equal})
            require(canonical(rebuilt)==canonical(actual_record),'Complete lossless reconstruction or metadata differs from actual run',case=case)
            for key,descriptor in b['source_package']['files'].items():
                raw=base64.b64decode(descriptor['base64'],validate=True);path=Path(descriptor['path']);work=(ROOT/path).read_bytes();committed,info=blobs.get(path)
                ok=(len(raw)==descriptor['byte_length'] and sha(raw)==descriptor['sha256'] and raw==work==committed)
                require(ok,'Complete source package file byte/Git binding mismatch',case=case,file=key,path=str(path))
                details['source_files'].append({'case':case,'key':key,'path':str(path),'sha256':sha(raw),'bytes':len(raw),'git':info,'byte_identical':ok})
            case_reports.append({'case':case,'run':str(run.relative_to(ROOT)),'input_sha256':sha(input_raw),'recording_sha256':sha(record_raw),'recorded_frames':count,'all_recorded_field_arrays':count*len(FIELDS),'complete_recording_reconstructed':canonical(rebuilt)==canonical(actual_record),'original_engine_ui_status':a['engine_verdicts'][5],'draft_engine_ui_status':b['engine_verdicts'][5],'expected_engine_ui_status':expected_ui,'matched_ui_receipt_sha256':[row['sha256'] for row in matching]})
            del actual_input,actual_record,rebuilt,input_raw,record_raw
        report['cases']=case_reports
        require({row['case'] for row in case_reports}==set(RUNS),'Missing complete case')
        for j in range(7):
            if j!=5:equal_field(f'$.engines[{j}]',old['engines'][j],new['engines'][j])
            else:
                for key in set(old['engines'][j])|set(new['engines'][j]):
                    if key!='verdict':equal_field(f'$.engines[{j}].'+key,old['engines'][j][key],new['engines'][j][key])
                expected='PASS' if all(c['engine_verdicts'][5]=='PASS' for c in new['cases']) else 'NOT_RUN'
                require(new['engines'][5]['verdict']==expected,'Combined UI engine status mismatch',expected=expected)
        archive_counts={}
        for case,(run_name,folder) in RUNS.items():
            archive=ROOT/'experiments/intent-edit-review/physics/results'/folder;manifest_path=archive/'artifact-manifest.json';raw=manifest_path.read_bytes();manifest=load(raw);relative=manifest_path.relative_to(ROOT);committed,info=blobs.get(relative)
            require(committed==raw,'Archive manifest differs from current Git HEAD',path=str(relative));details['manifest_files'].append({'path':str(relative),'sha256':sha(raw),'bytes':len(raw),'git':info,'byte_identical':committed==raw})
            require(manifest['case']==case,'Archive case identity mismatch',case=case)
            run=ROOT/'work/intent-physics'/run_name;archive_counts[case]=len(manifest['files'])
            for filename,descriptor in manifest['files'].items():
                path=archive/filename;relative=path.relative_to(ROOT)
                try:
                    stored=path.read_bytes();committed,info=blobs.get(relative);plain=gzip.decompress(stored) if filename.endswith('.gz') else stored
                    local_ok=len(stored)==descriptor['bytes'] and sha(stored)==descriptor['sha256']
                    plain_ok=len(plain)==descriptor['uncompressed_bytes'] and sha(plain)==descriptor['uncompressed_sha256']
                    git_ok=committed==stored and info.get('type')=='blob'
                    require(local_ok and plain_ok and git_ok,'Archive payload missing/corrupt/uncommitted',path=str(relative),local_ok=local_ok,uncompressed_ok=plain_ok,git_ok=git_ok)
                    if filename in ['input.json.gz','trajectory.json.gz']:
                        target=run/filename[:-3];require(plain==target.read_bytes(),'Archive differs from actual run bytes',case=case,file=filename)
                    details['archive_files'].append({'case':case,'path':str(relative),'bytes':len(stored),'sha256':sha(stored),'uncompressed_bytes':len(plain),'uncompressed_sha256':sha(plain),'manifest_stored_match':local_ok,'manifest_uncompressed_match':plain_ok,'git_blob_byte_identical':git_ok,'git':info})
                except Exception as error:
                    failures.append({'message':'Archive file unavailable','path':str(relative),'error':str(error)})
            archive_input=manifest['files']['input.json.gz'];archive_record=manifest['files']['trajectory.json.gz']
            require(manifest['input_sha256']==archive_input['uncompressed_sha256'] and manifest['recording_sha256']==archive_record['uncompressed_sha256'],'Archive root data hashes inconsistent',case=case)
        report['archive_counts']=archive_counts
        require(archive_counts=={'baseline':132,'03_cuff_width':133} and len(details['archive_files'])==265,'Expected exactly all 265 archived payload files')
        model_dir=ROOT/'experiments/teagan_sites_studio/app/dist/models';models=sorted(p for p in model_dir.rglob('*') if p.is_file())
        for path in models:
            relative=path.relative_to(ROOT);raw=path.read_bytes();committed,info=blobs.get(relative);ok=committed==raw and info.get('type')=='blob'
            require(ok,'Original model asset not byte-complete in current Git HEAD',path=str(relative))
            details['original_models'].append({'path':str(relative),'bytes':len(raw),'sha256':sha(raw),'git':info,'byte_identical':ok})
        require(len(models)==5,'Expected the five original model assets',count=len(models))
        report['original_model_assets_checked']=len(models)
        report['archive_payloads_checked']=len(details['archive_files']);report['actual_recorded_arrays_checked']=len(details['frame_arrays'])
        require(len(details['frame_arrays'])==610,'Expected both complete 61-frame, five-field recordings')
        report['draft_html_sha256_at_end']=sha(args.draft.read_bytes());report['git_head_at_end']=resolve('HEAD')
        require(report['draft_html_sha256_at_end']==new_hash,'Draft changed during the immutable snapshot audit')
        require(report['git_head_at_end']==start_head,'Git HEAD changed during current-HEAD archive audit')
        report['verdict']='FAIL' if failures else 'PASS'
    except Exception as error:
        failures.append({'message':'Audit could not finish','error':str(error),'traceback':traceback.format_exc()});report['verdict']='FAIL'
    finally:
        for reader in [blobs,baseblobs]:
            if reader:
                try:reader.close()
                except Exception as error:failures.append({'message':'Git batch completion failure','error':str(error)});report['verdict']='FAIL'
        report['ended_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        (output/'byte-proofs.json').write_text(json.dumps(details,ensure_ascii=False,indent=2)+'\n')
        summary={k:report.get(k) for k in ['verdict','base_commit','archive_commit','old_html_sha256','draft_html_sha256','archive_payloads_checked','actual_recorded_arrays_checked','original_model_assets_checked','unexpected_changed_paths']};summary['failures']=len(failures);summary['output']=str(output)
        print(json.dumps(summary,ensure_ascii=False));return 0 if report['verdict']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
