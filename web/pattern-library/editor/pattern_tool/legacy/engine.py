"""Declared-case design edits, guarded semantic patches and lossless-tag DXF patches.

The case's code is supplied by a sub-agent. This module is not an open-ended
natural-language compiler. Coordinates use the explicitly declared U unit.
"""
from collections import Counter,defaultdict,deque
from copy import deepcopy
from pathlib import Path
import difflib
import hashlib
import json
import math
import yaml
from . import model_reader as reader

def digest(data):return hashlib.sha256(data).hexdigest()
def scalar(value):return round(float(value),6)
def xy(point):return [float(point['横']),float(point['高'])]
def distance(a,b):return math.dist(xy(a),xy(b))
def line(model,piece,name):return reader.line(model,piece,name)
def port(model,reference):return model['裁片接口'][reference['裁片']][reference['接口']]

def recompute(model):
    """Update measured facts only; leave unapproved production parameters alone."""
    for piece,ports in model['裁片接口'].items():
        for item in ports.values():
            segments=[]
            for ref in item['组成']:
                pts=line(model,piece,ref['线条'])['点位']
                segments.append(pts if ref['方向']=='正向' else pts[::-1])
            item['长度']=scalar(sum(sum(distance(a,b) for a,b in zip(pts,pts[1:])) for pts in segments))
            item['起点']=deepcopy(segments[0][0]);item['终点']=deepcopy(segments[-1][-1])
            item['段间间隙']=[scalar(distance(a[-1],b[0])) for a,b in zip(segments,segments[1:])]
    for item in model['关键尺寸']['项目'].values():item['数值']=scalar(reader.computed_dimension(model,item))
    for item in model['连接关系'].values():
        if '走缝长度差' in item:item['走缝长度差']=scalar(port(model,item['连接一'])['长度']-port(model,item['连接二'])['长度'])
        if '袖山总长' in item:
            item['袖山总长']=scalar(sum(port(model,r)['长度'] for r in item['袖片接口']))
            item['衣身袖窿总长']=scalar(sum(port(model,r)['长度'] for r in item['衣身接口']))
            item['总长差']=scalar(item['袖山总长']-item['衣身袖窿总长'])
        if '衣身领圈总长' in item:
            item['衣身领圈总长']=scalar(sum(port(model,r)['长度'] for r in item['衣身接口']))
            item['领条长边']=port(model,item['领条接口'])['长度']
            item['当前几何长度比']=scalar(item['领条长边']/item['衣身领圈总长'])
    calibration=model['原型与部件分层']['配套标定']
    for piece in ['前片','后片']:
        for side in ['左','右']:calibration['当前衣身袖窿'][piece+side]=model['裁片接口'][piece][side+'袖窿']['长度']
    calibration['当前袖山总长']['数值']=model['关键尺寸']['项目']['袖山总长']['数值']
    calibration['当前领圈总长']['数值']=model['关键尺寸']['项目']['领圈总长']['数值']
    for item in model['缝级关系图']['缝级记录']:
        obs=item['当前几何']
        if isinstance(item['边二'],dict):obs['衣身段长度']=scalar(sum(port(model,r)['长度'] for r in item['边一']))
        elif '长度比' in obs:
            obs['衣身长度']=scalar(sum(port(model,r)['长度'] for r in item['边一']))
            obs['领条长度']=scalar(sum(port(model,r)['长度'] for r in item['边二']))
            obs['长度比']=scalar(obs['领条长度']/obs['衣身长度'])
        else:obs['走缝长度差']=scalar(sum(port(model,r)['长度'] for r in item['边一'])-sum(port(model,r)['长度'] for r in item['边二']))

def record_execution(model,case,details,code_hash,base_spec_hash):
    cid=case['id'];intent=case['intent']
    model['文件约定']['纸样版本']='基准版改为基准测试 '+cid
    model['文件约定']['规格修订']='本次执行明确的U单位几何编辑；生产确认状态另行保留。'
    model['文件约定']['流程与现状的区别']='本次二维几何编辑有具体实现与补丁；其余未计算或未批准的生产流程仍按字段状态处理。'
    model['款式特征']['新增改款要求']=[intent]
    order=model['结构化款式单'];order['本轮任务']=intent
    order['设计意图']['自然语言修改要求']=[intent]
    order['设计意图']['必须保持']=['完整保持'+p+'的全部几何与文字' for p in case['preserve_pieces']]+case.get('preserve_features',[])
    plan=model['结构决策与操作方案'];plan['本轮结构差距']=[{'请求':intent,'单位':'U','参数':deepcopy(case['parameters'])}]
    plan['本轮有序操作序列']=[{'操作代号':case['operation'],'状态':'已执行','实现':'intent-edit-benchmark/cases/'+cid+'.py',
      '实现校验值':code_hash,'参数':deepcopy(case['parameters']),'输入规格校验值':base_spec_hash}]
    plan['本轮状态']='本案例代码已执行二维变形，测量事实已复算；不是全部语义操作均已实现。'
    for phase in model['制版流程']['阶段']:
        if phase['阶段名']=='识别':phase['本款状态']='本次自然语言请求已记录；几何单位明确为U。'
        if phase['阶段名']=='决策':phase['本款状态']='本案例限定的几何实现和保留范围已记录；生产装袖映射仍待确认。'
        if phase['阶段名']=='执行':phase['本款状态']='本案例二维编辑已执行；主体净毛样与生产工艺角色仍待确认。'
        if phase['阶段名']=='校验':phase['本款状态']='独立审计结果见本案例外部报告；生产版型未验收。'
    model['确定性执行与输出']['当前模式']='本案例限定几何编辑已执行；完整自然语言制版仍未实现。'
    model['确定性执行与输出']['全局约束']['本轮求解状态']='未运行通用求解器；按案例明确的变形函数执行并接受独立审计。'
    model['本次二维编辑']={'案例':cid,'意图':intent,'影响裁片':case['affected_pieces'],'保留裁片':case['preserve_pieces'],
        '参数':deepcopy(case['parameters']),'实际锚点与说明':details,'生产状态':'待确认，不放行'}

class Dumper(yaml.SafeDumper):
    def ignore_aliases(self,data):return True
def float_repr(dumper,value):
    if not math.isfinite(value):raise ValueError('非有限值')
    text=f'{value:.6f}'.rstrip('0').rstrip('.')
    if text in ('','-0'):text='0'
    if '.' not in text:text+='.0'
    return dumper.represent_scalar('tag:yaml.org,2002:float',text)
def string_repr(dumper,value):return dumper.represent_scalar('tag:yaml.org,2002:str',value,style='|' if '\n' in value else None)
Dumper.add_representer(float,float_repr);Dumper.add_representer(str,string_repr)
def dump_spec(model):
    groups=[['文件约定','单位与坐标','款式特征','按角色阅读'],['缝制交接卡','工艺参数','交付状态','术语说明'],
      ['关键尺寸','裁片接口','连接关系','裁剪清单','成衣部件角色','修改联动'],['材料选择','参考尺码表']]
    used={k for group in groups for k in group}|{'完整二维几何'}
    groups+=[[k for k in model if k not in used],['完整二维几何']]
    labels=['一 文件约定与款式','二 缝制交接与确认','三 制版尺寸与连接','四 材料与参考尺码','五 制版流程与规则','六 完整二维几何']
    return ('\n'.join('# '+label+'\n'+yaml.dump({k:model[k] for k in keys},Dumper=Dumper,allow_unicode=True,sort_keys=False,width=74)
       for label,keys in zip(labels,groups,strict=True))).encode('utf-8')

def escape(key):return str(key).replace('~','~0').replace('/','~1')
def semantic_diff(old,new,path=''):
    if old==new:return []
    if isinstance(old,dict) and isinstance(new,dict):
        ops=[]
        for key in old:
            p=path+'/'+escape(key)
            if key not in new:ops.append({'op':'remove','path':p,'old':old[key]})
            else:ops+=semantic_diff(old[key],new[key],p)
        for key in new:
            if key not in old:ops.append({'op':'add','path':path+'/'+escape(key),'value':new[key]})
        return ops
    if isinstance(old,list) and isinstance(new,list) and len(old)==len(new):
        return [op for i,(a,b) in enumerate(zip(old,new,strict=True)) for op in semantic_diff(a,b,path+'/'+str(i))]
    return [{'op':'replace','path':path,'old':old,'value':new}]

def apply_spec_patch(source,patch):
    if digest(source)!=patch['base_sha256']:raise ValueError('规格基准摘要不匹配')
    model=yaml.load(source.decode('utf-8'),Loader=reader.UniqueLoader)
    for op in patch['operations']:
        keys=[x.replace('~1','/').replace('~0','~') for x in op['path'].split('/')[1:]]
        if not keys:raise ValueError('本格式不允许整文替换')
        parent=model
        for k in keys[:-1]:parent=parent[int(k)] if isinstance(parent,list) else parent[k]
        key=int(keys[-1]) if isinstance(parent,list) else keys[-1]
        if op['op']=='add':
            if isinstance(parent,list) or key in parent:raise ValueError('新增字段冲突')
            parent[key]=deepcopy(op['value'])
        else:
            if parent[key]!=op['old']:raise ValueError('规格旧值不匹配')
            if op['op']=='replace':parent[key]=deepcopy(op['value'])
            elif op['op']=='remove':del parent[key]
            else:raise ValueError('未知规格操作')
    output=dump_spec(model)
    if digest(output)!=patch['target_sha256']:raise ValueError('规格补丁目标摘要不匹配')
    return output

def pairs(source):
    rows=source.splitlines(keepends=True)
    if len(rows)%2:raise ValueError('DXF组码不成对')
    result=[]
    for i in range(0,len(rows),2):
        raw=rows[i+1];value=raw.rstrip(b'\r\n');ending=raw[len(value):]
        result.append({'code':int(rows[i].strip()),'value':value.decode('gb18030'),'code_raw':rows[i],'ending':ending})
    return result
def source_entities(source):
    data=pairs(source);rows=[];i=0
    while i<len(data):
        item=data[i]
        if item['code']!=0 or item['value'] not in ('POLYLINE','LINE','TEXT'):i+=1;continue
        kind=item['value'];start=i;i+=1;indices=[];text=None
        if kind=='POLYLINE':
            while i<len(data) and not(data[i]['code']==0 and data[i]['value']=='SEQEND'):
                if data[i]['code']==0 and data[i]['value']=='VERTEX':
                    coords={};i+=1
                    while i<len(data) and data[i]['code']!=0:
                        if data[i]['code'] in (10,20):coords[data[i]['code']]=i
                        i+=1
                    indices.append([coords[10],coords[20]])
                else:i+=1
        else:
            fields={}
            while i<len(data) and data[i]['code']!=0:
                fields[data[i]['code']]=i;i+=1
            indices=[[fields[10],fields[20]]]
            if kind=='LINE':indices.append([fields[11],fields[21]])
            else:text=data[fields[1]]['value']
        points=[[scalar(data[a]['value']),scalar(data[b]['value'])] for a,b in indices]
        rows.append({'kind':kind,'indices':indices,'points':points,'text':text,'start_pair':start})
    return data,rows
def key_for(kind,points,text=None):return (kind,tuple(tuple(scalar(v) for v in p) for p in points),text)
def geometry_patch(source,old,new):
    data,entities=source_entities(source);lookup=defaultdict(deque)
    for entity in entities:lookup[key_for(entity['kind'],entity['points'],entity['text'])].append(entity)
    oldrows=reader.drawables(old);newrows=reader.drawables(new);operations=[];changed=Counter()
    for a,b in zip(oldrows,newrows,strict=True):
        kind={'折线':'POLYLINE','直线':'LINE','文字':'TEXT'}[a['线型']]
        pa=a['点位'] if kind!='TEXT' else [a['位置']]
        pb=b['点位'] if kind!='TEXT' else [b['位置']]
        text=a.get('内容');identity=key_for(kind,pa,text)
        if not lookup[identity]:raise ValueError('无法按几何识别输入DXF对象')
        entity=lookup[identity].popleft()
        if len(pb)!=len(entity['indices']) or b.get('内容')!=text:raise ValueError('本基准不支持改变实体类型、点数或文字内容')
        for positions,values in zip(entity['indices'],pb,strict=True):
            for index,value in zip(positions,values,strict=True):
                if scalar(data[index]['value'])!=scalar(value):
                    operations.append({'pair_index':index,'code':data[index]['code'],'old':data[index]['value'],'value':f'{float(value):.6f}',
                       '裁片':a['裁片'],'线名':a.get('名称','文字'),'实体顺序':entities.index(entity)})
                    changed[a['裁片']]+=1
    if any(lookup.values()):raise ValueError('DXF有未覆盖对象')
    patch={'format':'guarded-dxf-coordinate-patch/1','base_sha256':digest(source),'operations':sorted(operations,key=lambda x:x['pair_index'])}
    output=apply_dxf_patch(source,patch,check_target=False);patch['target_sha256']=digest(output)
    return patch,output,dict(changed)
def apply_dxf_patch(source,patch,check_target=True):
    if digest(source)!=patch['base_sha256']:raise ValueError('DXF基准摘要不匹配')
    data=pairs(source);seen=set()
    for op in patch['operations']:
        i=op['pair_index']
        if i in seen or i<0 or i>=len(data):raise ValueError('重复或非法DXF位置')
        seen.add(i);item=data[i]
        if item['code']!=op['code'] or item['value']!=op['old']:raise ValueError('DXF旧值或组码不匹配')
        value=float(op['value'])
        if not math.isfinite(value) or item['code'] not in (10,20,11,21):raise ValueError('非法坐标补丁')
    for op in patch['operations']:data[op['pair_index']]['value']=op['value']
    result=b''.join(item['code_raw']+item['value'].encode('gb18030')+item['ending'] for item in data)
    if check_target and digest(result)!=patch['target_sha256']:raise ValueError('DXF目标摘要不匹配')
    return result

def emit(case_module,input_spec,input_dxf,output):
    source_spec=Path(input_spec).read_bytes();source_dxf=Path(input_dxf).read_bytes()
    old=yaml.load(source_spec.decode('utf-8'),Loader=reader.UniqueLoader);new=deepcopy(old)
    reader.validate(old);details=case_module.edit(new)
    for piece in case_module.CASE['preserve_pieces']:
        if new['完整二维几何'][piece]!=old['完整二维几何'][piece]:raise ValueError('变更越过保留裁片')
    recompute(new);record_execution(new,case_module.CASE,details,digest(Path(case_module.__file__).read_bytes()),digest(source_spec))
    data=dump_spec(new);new=yaml.load(data.decode('utf-8'),Loader=reader.UniqueLoader);inventory=reader.validate(new)
    spec_patch={'format':'guarded-semantic-spec-patch/1','base_sha256':digest(source_spec),'target_sha256':digest(data),'operations':semantic_diff(old,new)}
    if apply_spec_patch(source_spec,spec_patch)!=data:raise ValueError('规格补丁重放失败')
    patch,dxf,changed=geometry_patch(source_dxf,old,new)
    if apply_dxf_patch(source_dxf,patch)!=dxf:raise ValueError('几何补丁重放失败')
    dest=Path(output);dest.mkdir(parents=True,exist_ok=True)
    (dest/'intent.txt').write_text(case_module.CASE['intent']+'\n')
    (dest/'new-spec.yaml').write_bytes(data);(dest/'output.dxf').write_bytes(dxf)
    for name,value in [('spec-diff.json',spec_patch),('geometry-patch.json',patch),('case.json',case_module.CASE),('anchors.json',details)]:
        (dest/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    (dest/'spec-diff.patch').write_text(''.join(difflib.unified_diff(source_spec.decode().splitlines(True),data.decode().splitlines(True),fromfile='input-spec.yaml',tofile='new-spec.yaml')))
    measured=[]
    for name,a in old['关键尺寸']['项目'].items():
        b=new['关键尺寸']['项目'][name]
        if a['数值']!=b['数值']:measured.append(f"| {name} | {a['数值']} | {b['数值']} | {b['数值']-a['数值']:.6f} |")
    (dest/'spec-diff.md').write_text('# '+case_module.CASE['title']+'\n\n'+case_module.CASE['intent']+'\n\n| 二维量测项目 | 修改前U | 修改后U | 差值U |\n| --- | --- | --- | --- |\n'+'\n'.join(measured)+'\n\n生产待确认状态继续保留。\n')
    return {'case':case_module.CASE['id'],'generation':'PASS','inventory':inventory,'spec_operations':len(spec_patch['operations']),
       'dxf_coordinate_operations':len(patch['operations']),'changed_coordinates_by_piece':changed,'input_spec_sha256':digest(source_spec),
       'input_dxf_sha256':digest(source_dxf),'new_spec_sha256':digest(data),'output_dxf_sha256':digest(dxf),'production_readiness':'BLOCKED'}
