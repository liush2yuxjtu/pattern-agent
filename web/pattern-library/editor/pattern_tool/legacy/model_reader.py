"""Read one declarative YAML and build new SVG/DXF drawings from its geometry.

No source DXF, previous design file, photograph or embedded program is read.
This is a drawing exporter, not a cutting-machine driver or a sewing controller.
"""
from pathlib import Path
from collections import Counter
from decimal import Decimal
import argparse
import html
import json
import math
import yaml
import ezdxf


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader,node,deep=False):
    result={}
    for a,b in node.value:
        key=loader.construct_object(a,deep=deep)
        if key in result:raise ValueError('字段重名：'+str(key))
        result[key]=loader.construct_object(b,deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,unique_mapping)


def finite_number(value):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError('坐标与尺寸必须是有限数值')
    return float(value)


def xy(point):return [finite_number(point['横']),finite_number(point['高'])]
def length(points):return sum(math.dist(xy(a),xy(b)) for a,b in zip(points,points[1:]))


def line(model,piece,name):
    matches=[x for x in model['完整二维几何'][piece]['线条'] if x['名称']==name]
    if len(matches)!=1:raise ValueError('线条缺失或重名：'+piece+'／'+name)
    return matches[0]


def interface(model,piece,name):return model['裁片接口'][piece][name]


def resolve_endpoint(model,reference):
    return interface(model,reference['裁片'],reference['接口'])


def computed_dimension(model,dimension):
    method=dimension['计算方式'];piece=dimension.get('裁片')
    if method=='线长相加':return sum(length(line(model,piece,name)['点位']) for name in dimension['线条'])
    if method=='尺寸相加':return sum(computed_dimension(model,model['关键尺寸']['项目'][name]) for name in dimension['尺寸项目'])
    if method=='接口长相加':return sum(resolve_endpoint(model,ref)['长度'] for ref in dimension['接口'])
    if method in ('横向两点距离','竖向两点距离'):
        a,b=[model['完整二维几何'][piece]['定位点'][name] for name in dimension['定位点']]
        axis='横' if method=='横向两点距离' else '高'
        return abs(finite_number(a[axis])-finite_number(b[axis]))
    raise ValueError('未知尺寸算法：'+method)


def validate_process_metadata(model):
    if model['文件约定']['格式版本']!='1.1':return
    stages=model['制版流程']['阶段']
    if [s['阶段名'] for s in stages]!=['识别','计算','决策','执行','校验'] or [s['顺序'] for s in stages]!=list(range(1,6)):
        raise ValueError('制版阶段缺失或顺序错误')
    if any(not s['输入'] or not s['输出'] or not s['本款状态'] for s in stages):raise ValueError('阶段交接信息不完整')
    assets=model['五类基础资产快照']
    for key in ['原型库','松量规则表','语义操作库','部件规则库','测试样例库']:
        if key not in assets:raise ValueError('基础资产记录缺失：'+key)
    for key in ['H1结构平衡','H2弧线形态','H3基准线与点位','H4工艺约定']:
        if key not in model['原型与部件分层']['四层约束']:raise ValueError('原型分层缺失')
    rows=model['尺寸推导']['部位计算账']
    for name,row in rows.items():
        for key in ['净体尺寸','基准松量','面料弹性调整','厚度工艺补偿','成衣目标尺寸','洗后尺寸变化','批准的缩水补偿系数','针织下垂补偿','纸样净尺寸']:
            cell=row[key]
            if not cell['状态'] or not cell['单位']:raise ValueError('尺寸计算项缺少状态或单位')
            if cell['数值'] is not None:finite_number(cell['数值'])
    names=[]
    def references(value):
        if isinstance(value,dict):
            if '裁片' in value and '接口' in value:resolve_endpoint(model,value)
            for item in value.values():references(item)
        elif isinstance(value,list):
            for item in value:references(item)
    for seam in model['缝级关系图']['缝级记录']:
        names.append(seam['关系名称'])
        if seam['汇总关系名称'] not in model['连接关系']:raise ValueError('缝级记录缺少有效汇总关系')
        references(seam)
        params=seam['批准匹配参数']
        if params['数值'] is not None:finite_number(params['数值'])
    if len(names)!=len(set(names)):raise ValueError('缝级关系名称重复')
    if any(op.get('状态')!='已执行' or not op.get('实现') for op in model['结构决策与操作方案']['本轮有序操作序列']):
        raise ValueError('读取器只接受已执行并有实现记录的几何方案；未实现的操作不可伪装为完成')


def validate(model):
    if model['文件约定']['外部设计文件依赖']:
        raise ValueError('本格式要求独立设计文件，不接受外部设计数据依赖')
    if model['单位与坐标']['坐标单位']!='U':raise ValueError('未定义图形单位')
    calibration=model['单位与坐标']['实际比例']
    if calibration['状态']=='已标定':
        if finite_number(calibration['每U毫米数'])<=0:raise ValueError('比例必须为正')
    elif calibration['状态']!='未标定':raise ValueError('未知比例状态')
    counts=Counter();vertices=0
    for piece,part in model['完整二维几何'].items():
        xy(part['排版放置点']);names=[]
        for curve in part['线条']:
            names.append(curve['名称']);points=curve['点位']
            if len(points)<2:raise ValueError('一条线至少两个点')
            for point in points:xy(point)
            if curve['线型'] not in ('直线','折线'):raise ValueError('未知线型')
            if curve['闭合方式'] not in ('开放','闭合'):raise ValueError('未知闭合方式')
            if curve['线型']=='直线' and len(points)!=2:raise ValueError('直线必须恰好两个点')
            counts[curve['线型']]+=1
            if curve['线型']=='折线':vertices+=len(points)
        if len(names)!=len(set(names)):raise ValueError('裁片内线名重名')
        for contour in part['轮廓'].values():
            for segment in contour['组成']:
                line(model,piece,segment['线条'])
                if segment['方向'] not in ('正向','反向'):raise ValueError('未知方向')
        vertex_set={tuple(xy(p)) for curve in part['线条'] for p in curve['点位']}
        for point in part['定位点'].values():
            if tuple(xy(point)) not in vertex_set:raise ValueError('定位点不在线条点位中')
        for text in part['文字']:
            if not isinstance(text['文字内容'],str):raise ValueError('文字内容必须是字符串')
            xy(text['位置']);counts['文字']+=1
    for piece,ports in model['裁片接口'].items():
        for name,port in ports.items():
            walked=[]
            for segment in port['组成']:
                points=line(model,piece,segment['线条'])['点位']
                if segment['方向'] not in ('正向','反向'):raise ValueError('接口方向未定义')
                walked.append(points if segment['方向']=='正向' else points[::-1])
            actual=sum(length(points) for points in walked)
            if not math.isclose(actual,finite_number(port['长度']),rel_tol=0,abs_tol=1e-6):raise ValueError('接口长度不一致：'+piece+'／'+name)
            if xy(port['起点'])!=xy(walked[0][0]) or xy(port['终点'])!=xy(walked[-1][-1]):raise ValueError('接口起止点不一致')
            gaps=[math.dist(xy(a[-1]),xy(b[0])) for a,b in zip(walked,walked[1:])]
            if len(gaps)!=len(port['段间间隙']):raise ValueError('接口间隙记录数量错误')
            if any(not math.isclose(a,b,rel_tol=0,abs_tol=1e-6) for a,b in zip(gaps,port['段间间隙'])):raise ValueError('接口间隙不一致')
    for name,dimension in model['关键尺寸']['项目'].items():
        if dimension['单位']!='U' or not math.isclose(computed_dimension(model,dimension),finite_number(dimension['数值']),rel_tol=0,abs_tol=1e-6):
            raise ValueError('尺寸记录与几何不一致：'+name)
    def check_links(value):
        if isinstance(value,dict):
            if '裁片' in value and '接口' in value:resolve_endpoint(model,value)
            for item in value.values():check_links(item)
        elif isinstance(value,list):
            for item in value:check_links(item)
    check_links(model['连接关系'])
    for relation in model['连接关系'].values():
        if '走缝长度差' in relation:
            difference=resolve_endpoint(model,relation['连接一'])['长度']-resolve_endpoint(model,relation['连接二'])['长度']
            if not math.isclose(difference,relation['走缝长度差'],rel_tol=0,abs_tol=2e-6):raise ValueError('走缝长度差不一致')
    expected=model['文件约定']['几何清单预期']
    if len(model['完整二维几何'])!=expected['裁片'] or counts['折线']!=expected['折线'] or counts['直线']!=expected['直线'] or counts['文字']!=expected['文字'] or vertices!=expected['折线顶点']:
        raise ValueError('几何清单不完整或与预期不一致')
    validate_process_metadata(model)
    return {'裁片数':len(model['完整二维几何']),'线型数量':dict(counts),'折线顶点数':vertices,
            '接口数':sum(len(v) for v in model['裁片接口'].values()),'关键尺寸数':len(model['关键尺寸']['项目']),
            '连接关系数':len(model['连接关系']),'外部设计数据输入数':0}


def placed(point,origin):
    return [float(Decimal(str(point[k]))+Decimal(str(origin[k]))) for k in ('横','高')]


def drawables(model):
    rows=[]
    for piece,part in model['完整二维几何'].items():
        origin=part['排版放置点']
        for curve in part['线条']:
            rows.append({'裁片':piece,'名称':curve['名称'],'线型':curve['线型'],'闭合':curve['闭合方式']=='闭合',
                         '点位':[placed(point,origin) for point in curve['点位']]})
        for text in part['文字']:
            rows.append({'裁片':piece,'线型':'文字','内容':text['文字内容'],'位置':placed(text['位置'],origin)})
    return rows


def export_svg(model,rows):
    points=[p for row in rows for p in (row['点位'] if row['线型']!='文字' else [row['位置']])]
    x0,x1=min(p[0] for p in points),max(p[0] for p in points)
    y0,y1=min(p[1] for p in points),max(p[1] for p in points)
    box=[x0-35,-y1-35,x1-x0+70,y1-y0+70]
    result=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="%s" width="1600">'%' '.join(map(str,box)),
            '<title>独立YAML生成的二维纸样；单位U，实际比例未标定</title>',
            '<rect x="%s" y="%s" width="%s" height="%s" fill="white"/>'%tuple(box),
            '<g stroke="#294d40" stroke-width="0.7" fill="none">']
    for row in rows:
        if row['线型']=='文字':continue
        pts=row['点位']+([row['点位'][0]] if row['闭合'] else [])
        result.append('<polyline points="%s"/>'%' '.join('%s,%s'%(x,-y) for x,y in pts))
    result.append('</g><g fill="#587267" font-size="%s" font-family="Noto Sans CJK SC,sans-serif">'%model['单位与坐标']['文字显示']['字高'])
    for row in rows:
        if row['线型']=='文字':result.append('<text x="%s" y="%s">%s</text>'%(row['位置'][0],-row['位置'][1],html.escape(row['内容'])))
    return '\n'.join(result+['</g></svg>'])+'\n'


def production_status(model):
    # Derive holds from actual fields; a hand-written status list cannot clear them.
    holds=[]
    def hold(name,reason):holds.append({'项目':name,'影响':reason})
    if model['单位与坐标']['实际比例']['状态']!='已标定':hold('实际比例','不能转换成实际毫米。')
    for name,cut in model['裁剪清单'].items():
        if cut['批准裁数']['状态']!='已确认':hold(name+'裁数','裁剪张数未批准。')
        if cut['可用裁剪轮廓']['状态']!='已确认':hold(name+'裁剪轮廓','净样与裁剪角色未确认。')
    if any(model['材料选择'][key]['状态']!='已确认' for key in ('衣身','领条')):hold('材料选择','衣身与领条物料未批准。')
    if any(value.get('状态')!='已确认' for key,value in model['工艺参数'].items() if key!='文字提示'):hold('缝份与工艺','缝份、折边、领边或针迹参数未批准。')
    if any(ref.get('前后对应',{}).get('状态')!='已确认' for name,ref in model['连接关系'].items() if name.endswith('袖装配')):hold('袖山前后与对位','装袖前后关系尚未确认。')
    if model['文件约定']['格式版本']=='1.1' and any(row['成衣目标尺寸']['状态']!='已确认' or row['纸样净尺寸']['状态']!='已确认' for row in model['尺寸推导']['部位计算账'].values()):
        hold('成衣目标与纸样净尺寸','三层尺寸推导尚未完成和批准。')
    return {'状态':'待确认，不放行' if holds else '资料项已确认，仍需实际工艺验证','阻止生产的项目':holds,
             '说明':'绘图程序只输出参考二维图，不控制切割或缝制设备。'}


def reconstruct(specification,output):
    model=yaml.load(Path(specification).read_text(encoding='utf-8'),Loader=UniqueLoader)
    inventory=validate(model)
    rows=drawables(model)
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    doc=ezdxf.new('R2010');doc.units=0
    msp=doc.modelspace()
    for piece in model['完整二维几何']:doc.layers.new(piece)
    for row in rows:
        attrs={'layer':row['裁片']}
        if row['线型']=='折线':msp.add_polyline2d(row['点位'],close=row['闭合'],dxfattribs=attrs)
        elif row['线型']=='直线':msp.add_line(row['点位'][0],row['点位'][1],dxfattribs=attrs)
        else:msp.add_text(row['内容'],dxfattribs={**attrs,'insert':row['位置'],'height':model['单位与坐标']['文字显示']['字高'],'rotation':model['单位与坐标']['文字显示']['旋转角度']})
    doc.saveas(output/'pattern-U.dxf')
    (output/'pattern-U.svg').write_text(export_svg(model,rows),encoding='utf-8')
    (output/'读取后的绘图对象.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    report={'二维重建':'PASS','输入设计文件数':1,'读取规则':'只读取传入的单个YAML；数据不依赖其他设计文件。',
             '几何检查':inventory,'图形单位':'U','DXF单位声明':'未指定物理单位，INSUNITS=0','生产状态':production_status(model)}
    (output/'独立重建报告.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('yaml_file');parser.add_argument('output_directory')
    args=parser.parse_args()
    print(json.dumps(reconstruct(args.yaml_file,args.output_directory),ensure_ascii=False,indent=2))
