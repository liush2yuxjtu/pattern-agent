"""Export the actual metric SVG without rescaling; this is not a print approval."""
import argparse,json,re
from pathlib import Path
import xml.etree.ElementTree as ET
import fitz


def main():
    p=argparse.ArgumentParser();p.add_argument('--svg',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    root=ET.parse(a.svg).getroot()
    def mm(s):
        if not re.fullmatch(r'[0-9.]+mm',s):raise ValueError('SVG must specify physical millimetres')
        return float(s[:-2])
    expected=[mm(root.attrib[k]) for k in ('width','height')]
    with fitz.open(a.svg) as svg:
        with fitz.open('pdf',svg.convert_to_pdf()) as pdf:
            measured=[pdf[0].rect.width*25.4/72,pdf[0].rect.height*25.4/72]
            error=max(abs(x-y) for x,y in zip(expected,measured));assert error<.001
            pdf.save(a.out)
    report={'svg_size_mm':expected,'pdf_size_mm':measured,'max_dimension_error_mm':error,'dimension_match':True,'seam_allowance':'NONE','printing':'Print at100%; verify100mm calibration before use; manufacturing not approved.'}
    a.out.with_name('pdf-scale-check.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':main()
