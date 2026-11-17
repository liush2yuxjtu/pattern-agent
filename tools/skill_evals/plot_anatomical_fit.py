#!/usr/bin/env python3
"""Plot independently reopened initial/final OBJ silhouettes against fixed masks."""
import argparse
import json
from pathlib import Path
import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from grade_anatomical_projection import coordinates,read_obj


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--workspace',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    fixture=args.workspace/'fixtures/anatomical-fit';final=args.workspace/'iteration-2/eval-2-anatomical-fit/with_skill/run-1/outputs/final.obj'
    camera=json.loads((fixture/'camera.json').read_text());stats={};fig,axes=plt.subplots(2,2,figsize=(8,10))
    for row,view in enumerate(['front','side']):
        reference=cv2.imread(str(fixture/f'reference-{view}-mask.png'),0)>0;stats[view]={}
        for column,(stage,source) in enumerate([('Initial',fixture/'initial.obj'),('Final',final)]):
            v,f=read_obj(source);xy,_=coordinates(v,camera,view);mask=np.zeros(reference.shape,np.uint8)
            for triangle in f:cv2.fillConvexPoly(mask,np.rint(xy[triangle]).astype(np.int32),255)
            mask=mask>0;iou=float((mask&reference).sum()/(mask|reference).sum());stats[view][stage.lower()]=iou
            image=np.full((*mask.shape,3),245,np.uint8);image[mask&reference]=[45,175,65];image[reference&~mask]=[235,45,155];image[mask&~reference]=[20,195,225]
            axes[row,column].imshow(image);axes[row,column].set_title(f'{view.title()} {stage.lower()} | IoU {iou:.4f}');axes[row,column].axis('off')
    fig.suptitle('Actual anatomical mesh fit — fixed reference and cameras',fontsize=14)
    fig.text(.5,.025,'Green: overlap   Pink: reference only   Cyan: model only\nSynthetic control; IoU is not human measurement accuracy',ha='center',fontsize=10)
    fig.tight_layout(rect=[0,.07,1,.96]);args.out.mkdir(parents=True,exist_ok=True);fig.savefig(args.out/'opencv-before-after.png',dpi=160);plt.close(fig)
    (args.out/'independent-fit-metrics.json').write_text(json.dumps({'method':'Separate OBJ parser and OpenCV triangle union at unchanged supplied camera/resolution','views':stats,'real_person_accuracy':'NOT_ESTABLISHED'},indent=2)+'\n')
    print(json.dumps(stats))


if __name__=='__main__':main()
