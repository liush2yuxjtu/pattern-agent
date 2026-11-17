#!/usr/bin/env python3
"""Stage exact run archives and small visual inputs for Anthropic's pinned viewer."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
from visual_gallery import collect,inject

HERE=Path(__file__).resolve().parent


def archive_tree(source,target):
    target.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob('*')):
            if not path.is_file() or '__pycache__' in path.parts or path.suffix=='.pyc':continue
            info=zipfile.ZipInfo(str(path.relative_to(source)),(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16
            archive.writestr(info,path.read_bytes())
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
    return hashlib.sha256(target.read_bytes()).hexdigest()


def build(workspace,site,evidence):
    site.mkdir(parents=True,exist_ok=True);evidence.mkdir(parents=True,exist_ok=True)
    review=workspace/'review-inputs';inventory=[]
    for number in [1,2,3]:
        origin=workspace/f'iteration-{number}';stage=review/f'iteration-{number}'
        for run in sorted(origin.glob('eval-*/*/run-*')):
            relative=run.relative_to(origin);thin=stage/relative
            output=thin/'outputs';output.mkdir(parents=True,exist_ok=True)
            for name in ['eval_metadata.json','grading.json','timing.json']:
                shutil.copyfile(run/name,thin/name)
            case,config=relative.parts[:2];key=f'iteration-{number}/{case}/{config}'
            target=site/'artifacts'/key;target.mkdir(parents=True,exist_ok=True)
            archive=site/'artifacts'/(key+'.zip');digest=archive_tree(run,archive)
            inventory.append(dict(run=key,archive=str(archive.relative_to(site)),sha256=digest,grading=json.loads((run/'grading.json').read_text())['summary']))
            for name in ['report.md','TRACE.md','metrics.json','audit.json','measurements.csv']:
                source=run/'outputs'/name
                if source.is_file():shutil.copyfile(source,output/name)
            for folder,prefix in [('renders',''),('overlays','overlay-')]:
                for name in ['front','side','back','close-up','pose','depth']:
                    source=run/'outputs'/folder/(name+'.png')
                    if source.is_file():
                        shutil.copyfile(source,output/(prefix+name+'.png'))
                        shutil.copyfile(source,target/(prefix+name+'.png'))
            (output/'artifacts.md').write_text('Full unmodified executor files, source meshes, raw depth, scripts, trace and independent grades:\n\nhttps://liush2yuxjtu.github.io/pattern-agent/garment-body/anatomical-evals/'+str(archive.relative_to(site))+'\n\nArchive SHA256: '+digest+'\n\nThis viewer uses visual previews; the ZIP retains all run artifacts. No outputs or failures were removed from that archive.\n')
        shutil.copyfile(origin/'benchmark.json',site/f'benchmark-iteration-{number}.json')
        command=[sys.executable,str(HERE/'build_functional_review.py'),'--workspace',str(stage),'--benchmark',str(origin/'benchmark.json'),'--out',str(site/('eval.html' if number==2 else f'iteration-{number}.html'))]
        if number==2:command+=['--previous-workspace',str(review/'iteration-1')]
        subprocess.run(command,check=True)
        page=site/('eval.html' if number==2 else f'iteration-{number}.html')
        document=page.read_text().replace('<head>','<head>\n<link rel="icon" href="../../assets/favicon.svg" type="image/svg+xml">',1)
        document=document.replace('<body>','<body>\n<nav style="padding:12px 20px;background:#e5ede5;font:14px/1.5 system-ui">'
            '<a href="../skill/">Current skill & download</a> · <a href="iteration-1.html">First candidate</a> · '
            '<a href="eval.html">Selected lean revision</a> · <a href="iteration-3.html">Untuned camera holdout</a> · '
            '<a href="opencv-before-after.png">OpenCV before/after</a> · <a href="manifest.json">Raw artifact hashes</a>'
            '<br>14 subagent executions. Round 1: 22/22 each. Round 2: lean 22/22, original 21/22 (missing metrics field, geometry correct). '
            'Holdout: 8/8 each. Core instructions 40.03% shorter; not a fit-accuracy, token-cost, native-trigger or clothed-image quality gain.</nav>',1)
        gallery=collect(workspace,site,origin)
        document=inject(document,gallery)
        page.write_text(document)
        (site/f'gallery-iteration-{number}.json').write_text(json.dumps(gallery,ensure_ascii=False,indent=2)+'\n')
        for name in ['benchmark.json','benchmark.md','analysis.json','grading-summary.json','aggregate-upstream.log','benchmark-upstream-raw.json']:
            source=origin/name
            if source.is_file():
                destination=evidence/f'iteration-{number}'/name;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,destination)
    for name in ['protocol.json','functional-evals.json','frozen-assertions.json','frozen-inputs.json','frozen-v2.json','holdout-spec.json','holdout-freeze.json','hillclimb-proposal.json','proposal-v2.json','selection.json','history.json','independent-review.json','independent-review.md']:
        if (workspace/name).is_file():shutil.copyfile(workspace/name,evidence/name)
    for name in ['fixtures','skill-snapshot-v0','skill-candidate-v1','skill-candidate-v2','grader-controls','native-readiness']:
        digest=archive_tree(workspace/name,site/(name+'.zip'));inventory.append(dict(archive=name+'.zip',sha256=digest))
    # Private answers are disclosed only after the frozen runs and untuned holdout.
    oracle=site/'oracle.zip'
    with zipfile.ZipFile(oracle,'w',zipfile.ZIP_DEFLATED) as archive:
        for name in ['fit-target-state.json','fit-target.obj','fit-target-joints.json','state-audit.json','provenance.json']:
            archive.write(workspace/'private-oracle'/name,name)
    inventory.append(dict(archive='oracle.zip',sha256=hashlib.sha256(oracle.read_bytes()).hexdigest()))
    manifest=dict(scope='Executed anatomical model component evaluations, not clothed photo generation or native Claude triggers',executions=14,previews='Pinned Anthropic viewer, curated visual inputs; complete original run archives retained',archives=inventory)
    manifest['files']={str(p.relative_to(site)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(site.rglob('*')) if p.is_file() and p.name!='manifest.json'}
    (site/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    shutil.copyfile(site/'manifest.json',evidence/'site-manifest.json')
    print(json.dumps({'runs':14,'files':len(manifest['files']),'site':str(site)}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True);parser.add_argument('--site',type=Path,required=True);parser.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args();build(args.workspace.resolve(),args.site.resolve(),args.evidence.resolve())
