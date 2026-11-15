"""Independently reload each cache-free final snapshot and compare full arrays."""
import argparse,json,sys
from pathlib import Path
import bpy,numpy as np


def main():
    p=argparse.ArgumentParser();p.add_argument('--runs',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);rows=[]
    for case in ['baseline','atlas_rigid','left_sleeve_90']:
        root=a.runs/case;bpy.ops.wm.open_mainfile(filepath=str((root/'drape-final.blend').resolve()),load_ui=False)
        assert not bpy.data.libraries;meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert len(meshes)==2
        last=sorted((root/'frames').glob('*.npz'))[-1];delta=0.
        with np.load(last) as f:
            for name,prefix in [('Measured final cloth','cloth'),('Frozen human collider','body')]:
                o=bpy.data.objects[name];ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();m.calc_loop_triangles()
                v=np.array([ev.matrix_world@x.co for x in m.vertices]);t=np.array([x.vertices[:] for x in m.loop_triangles]);ev.to_mesh_clear()
                assert np.array_equal(t,f[prefix+'_triangles']);delta=max(delta,float(np.max(abs(v-f[prefix+'_vertices']))))
        assert delta<1e-7
        rows.append({'case':case,'mesh_count':2,'triangles_match':True,'max_coordinate_error_m':delta,'external_libraries':0,'cloth_simulation_modifiers':sum(m.type=='CLOTH' for o in meshes for m in o.modifiers)})
    a.out.write_text(json.dumps({'rows':rows,'independent_reload_pass':True,'fit_approval':False},indent=2)+'\n');print(json.dumps(rows))


if __name__=='__main__':main()
