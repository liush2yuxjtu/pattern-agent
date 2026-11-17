"""Independent VTK cutter validation; does not import reproduce.py."""
import vtk,json,math
from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parent
reader=vtk.vtkOBJReader();reader.SetFileName(str(root.parent/'inputs/body.obj'));reader.Update()
results=[]
for y in [128,109,88]:
 plane=vtk.vtkPlane();plane.SetOrigin(0,y,0);plane.SetNormal(0,1,0)
 cut=vtk.vtkCutter();cut.SetInputConnection(reader.GetOutputPort());cut.SetCutFunction(plane);cut.Update()
 pd=cut.GetOutput(); total=0.;n=0
 # Directly sum cutter line lengths belonging to geometrically central contour (all points |x| < 20).
 for i in range(pd.GetNumberOfCells()):
  c=pd.GetCell(i);pts=[pd.GetPoint(c.GetPointId(j)) for j in range(c.GetNumberOfPoints())]
  if all(abs(p[0])<20 for p in pts):
   total+=sum(math.dist(a,b) for a,b in zip(pts,pts[1:]));n+=1
 results.append({'y_cm':y,'vtk_central_length_cm':total,'vtk_selected_line_cells':n})
saved=json.loads((root/'corrected-measurements.json').read_text())
for result,record in zip(results,saved['section_results']):
 expected=record['loops'][record['selected_component_index']]['perimeter_cm'];result['difference_cm']=result['vtk_central_length_cm']-expected
 assert abs(result['difference_cm'])<.0001
for name in ['section-evidence.png','corrected-depth.png']:
 with Image.open(root/name) as im: im.load();print('REOPEN',name,im.size,im.mode)
assert next(d for d in saved['dimensions'] if d['name']=='bust_point_distance')['value'] is None
assert next(d for d in saved['dimensions'] if d['name']=='depth')['value'] is None
(root/'independent-verification.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
