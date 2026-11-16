#!/usr/bin/env python3
"""Package the MCP-drafted pattern and a Chinese printing/sewing guide."""
import html
import json
from pathlib import Path
import shutil
import zipfile

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (Image, PageBreak, Paragraph, SimpleDocTemplate,
                               Spacer, Table, TableStyle)

ROOT = Path(__file__).resolve().parent
DELIVERY = ROOT / 'work/delivery/straight-skirt-eu40'
BODY = '''基础直身裙 · EU40 标准参考版

本纸样使用 OpenSloper 0.2.0 的 MCP 工具从点、线和公式生成。
尺码采用 Burda 官方女装常规 40 号作参考，不代表人口统计平均值，也不是个人量体定制。
来源：https://www.burdastyle.com/how-to-take-measurements
参考身高 168 cm；人体腰围 74 cm、臀围 98 cm。

尺寸与款式
成衣腰围 75 cm（加 1 cm 活动量），臀围 102 cm（加 4 cm 活动量）。
裙身从腰头接缝到下摆 60 cm；腰头成品高 4 cm，合计约 64 cm。
腰臀高 20 cm、裙身长 60 cm 是本次打版设定；不来自 Burda 尺码表。
前片每侧一个省：省量 2.7 cm、长 9 cm；后片每侧一个省：省量 4.05 cm、长 14 cm。
前片对折裁 1 片，后片镜像裁 2 片；后中装 20 cm 拉链，下摆留 18 cm 行走开衩。

文件
print-a4.pdf：家用 A4 真比例拼接纸样，14 页（1 页封面 + 13 页裁片）。
print-fullsize.pdf：914 × 925 mm 单张真比例纸样，交给大幅面打印店。
straight-skirt-eu40.sloper：可编辑纸样，使用 OpenSloper Design 打开。
measurements-eu40.slm：尺寸文件，必须和 .sloper 保存在同一文件夹。
print-a4.slayout / print-fullsize.slayout：OpenSloper Publish 排版文件。
cutting-layout.svg / cutting-layout.dxf：矢量文件，导入其他软件时复核毫米单位与比例。
draft-preview.png：预览图，不用于按比例裁剪。
使用说明.pdf：中文打印与缝制说明。
build_pattern.py / mcp-calls.jsonl：可复现打版脚本和实际 MCP 调用记录。

打印
1. 先打印 print-a4.pdf 的第一页，选择“实际大小”或 100%；关闭“适合页面”。
2. 封面方框的横、竖都必须量到 10 cm。确认后再打印余下 13 页。
3. 按封面的行列图与 A1、A2、B1 等编号拼接，匹配菱形对位标记。
4. 相邻纸张有 10 mm 重叠区域。修去相应边缘，再对齐标记粘贴。
5. 最外侧连续轮廓是裁剪线，内部虚线是缝线或省道；布纹箭头与布边平行。
6. 省道保留完整布料，不沿省道三角形挖掉布料；只转印省腿、省尖和剪口。

缝份已包含，不要再次添加
侧缝、腰部、腰头各 1 cm；后中 1.5 cm；裙摆 3 cm；前中对折边 0 cm。
腰头缝线长 78 cm（75 cm 腰围 + 3 cm 搭门），展开宽 8 cm；含缝份裁剪约 80 × 10 cm。
省口上方的小凸起是省盖，折合省道后修顺腰线；不要误剪成凹口。

材料与裁剪
建议用无弹力梭织棉布或麻棉布。150 cm 门幅、无方向图案时，软件估算净需 0.8 m；
建议准备至少 1.0 m，并在预缩、对格或单向图案时另留余量。
另备 20 cm 隐形拉链、裙钩或纽扣、腰头粘合衬和缝线。
Front：前中放在布料折边上，裁 1 片，展开为完整前片。
Back：裁左右镜像各 1 片，后中不是折边。
Waistband：面料裁 1 片；衬按同纸样裁 1 片，可修去 1 cm 缝份以减薄。

建议缝制顺序
1. 先用胚布试做，核对腰、臀、腰臀高和裙长；把剪口、省道、拉链止口和开衩顶点转印到布上。
2. 车缝前后省道，从腰口向省尖缝，省尖线尾打结；省份烫向前中或后中，修顺腰线。
3. 后中从腰口下 20 cm 到距下摆 18 cm 的区间缝合；上段留装拉链，下段留作开衩。
4. 按 1 cm 缝份缝合两侧缝，匹配臀线剪口，缝份锁边并烫开。
5. 在后中预留开口安装 20 cm 拉链。开衩边先锁边，按 1.5 cm 缝份折烫并固定。
6. 腰头粘衬，匹配剪口缝到裙腰。30 mm 搭门留在后中一端；腰头沿折线对折，完成端头与内侧包缝，装裙钩。
7. 再次试穿并校正下摆，再折入 3 cm 裙摆缝份固定；熨烫整理。

修改与复核
在 OpenSloper Design 打开 .sloper，在 Measurements 修改 waist、hip、waist_to_hip、skirt_length。
在 Variables 修改 waist_ease、hip_ease、waistband_height 等。修改后重新检查并在 Publish 重新排版导出。
大幅改变腰臀差时，应重新分配省量；每次修改都需检查省盖、腰线和腰头配长。
本版已检查：无缺失尺寸、无无效对象、无 OpenSloper 几何问题；两条侧缝差 0.00 mm；
前后省腿等长；去除省量后的腰线合计 750 mm，匹配腰头。实际穿着合体仍需胚布试穿。

打版方法参考：https://github.com/opensloper/opensloper/blob/v0.2.0/docs/tutorials/skirt-block.md
本次另加常规保留布料的省道、省盖、腰头、后中拉链和开衩位置。
'''


def guide_pdf():
    pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
    base = ParagraphStyle('CN', fontName='STSong-Light', fontSize=10,
                          leading=15, wordWrap='CJK', spaceAfter=6)
    title = ParagraphStyle('TitleCN', parent=base, fontSize=23, leading=29,
                           textColor=colors.HexColor('#244D45'), spaceAfter=10)
    subtitle = ParagraphStyle('SubCN', parent=base, fontSize=13, leading=20,
                              textColor=colors.HexColor('#244D45'), spaceBefore=8)
    small = ParagraphStyle('SmallCN', parent=base, fontSize=8.5, leading=12)
    doc = SimpleDocTemplate(str(ROOT/'使用说明.pdf'), pagesize=A4,
                            leftMargin=18*mm, rightMargin=18*mm,
                            topMargin=15*mm, bottomMargin=15*mm,
                            title='基础直身裙 EU40：中文打印与缝制说明', author='OpenSloper MCP')
    story=[]
    def p(text, style=base):
        return Paragraph(html.escape(text).replace('\n','<br/>'),style)
    story += [p('基础直身裙 · EU40', title),
              p('OpenSloper MCP 制作 ｜ 前片、后片、腰头 ｜ 含缝份', subtitle),
              p('按 Burda 女装常规 40 号制作的标准参考版；不是个人量体定制。先用胚布试穿，再裁正式面料。')]
    rows = [['项目','人体 / 参考值','成衣 / 打版值'],
            ['腰围','74 cm','75 cm（含 1 cm 活动量）'],
            ['臀围','98 cm','102 cm（含 4 cm 活动量）'],
            ['身高','168 cm','Burda 常规号参考身高'],
            ['裙身长度','本次设定','60 cm；另加 4 cm 腰头'],
            ['腰臀高','本次设定','20 cm']]
    table=Table([[p(c,small) for c in row] for row in rows],colWidths=[30*mm,49*mm,94*mm])
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E7F0EB')),
                               ('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#B9C9C1')),
                               ('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),5),
                               ('BOTTOMPADDING',(0,0),(-1,-1),5)]))
    story += [table, Spacer(1,6*mm), Image(str(ROOT/'draft-preview.png'),width=138*mm,height=138*mm),
              p('预览：左为后片，右为对折前片，下方为腰头。预览图不可直接按比例裁剪。',small),
              p('尺寸来源：Burda 官方 How to take measurements。腰臀高与裙长为本次打版设定。',small),
              p('https://www.burdastyle.com/how-to-take-measurements',small), PageBreak()]
    sections = [
        ('先校准，再拼接',
         '打开 print-a4.pdf，共 14 页：1 页校准封面 + 13 页裁片。打印选择“实际大小 / 100%”，关闭“适合页面”。先量封面方框，横竖都应为 10 cm；确认后打印其余页。按 A1、A2、B1 等编号及菱形标记拼接，重叠区域为 10 mm。大幅面打印使用 print-fullsize.pdf（914 × 925 mm）。'),
        ('裁剪与缝份',
         '最外侧连续轮廓为裁剪线，内侧虚线为缝线或省道。前片 Front 对折裁 1 片；后片 Back 左右镜像裁 2 片；腰头 Waistband 裁 1 片面料和 1 片衬。布纹箭头与布边平行。省道布料必须保留，不挖掉三角形。省口的小凸起是省盖，缝省后修顺腰线。'),
        ('已含的缝份与辅料',
         '侧缝、腰部、腰头各 1 cm；后中 1.5 cm；裙摆 3 cm；前中折边 0 cm。不要重复加缝份。腰头含缝份约 80 × 10 cm，成品高 4 cm，含 3 cm 搭门。建议准备 150 cm 门幅梭织布至少 1 m（软件净估算 0.8 m），另备 20 cm 隐形拉链、粘合衬、裙钩和缝线；预缩、对格需另留余量。'),
        ('缝制顺序',
         '1. 胚布试做并转印省道、剪口、拉链止口和开衩顶点。\n2. 从腰口向省尖缝省，省尖打结，省份烫向前中或后中。\n3. 后中只缝合腰口下 20 cm 至距下摆 18 cm 的中段；上段留拉链，下段留开衩。\n4. 匹配臀线剪口，按 1 cm 缝份缝侧缝，锁边、烫开。\n5. 装后中拉链；开衩边锁边，折烫 1.5 cm 并固定。\n6. 腰头粘衬，按剪口接腰，留后中 3 cm 搭门；对折完成端头和内侧，装裙钩。\n7. 试穿后校正下摆，按 3 cm 裙摆缝份完成卷边并熨烫。'),
        ('调整和检查',
         '在 OpenSloper Design 中打开 .sloper，并保留同目录的 measurements-eu40.slm。四项尺寸都可修改，修改后重新检查、排版导出。大幅改变腰臀差时需重新分配省量。当前几何检查通过；前后侧缝各 603.19 mm，差 0.00 mm；前后省腿等长；缝合腰线合计 750 mm。实际合体以胚布试穿为准。'),
    ]
    for heading,text in sections:
        story += [p(heading,subtitle),p(text)]
    story += [p('打版方法参考 OpenSloper v0.2.0 直身裙教程；本版另加普通省道、省盖、腰头及后中开口。',small)]
    def footer(canvas,doc):
        canvas.saveState(); canvas.setFont('STSong-Light',8)
        canvas.setFillColor(colors.HexColor('#66736D'))
        canvas.drawString(18*mm,9*mm,'基础直身裙 EU40 ｜ 中文说明 ｜ 图样已含缝份')
        canvas.drawRightString(192*mm,9*mm,str(doc.page)); canvas.restoreState()
    doc.build(story,onFirstPage=footer,onLaterPages=footer)


def main():
    (ROOT/'使用说明.txt').write_text(BODY,encoding='utf-8')
    guide_pdf()
    files=['print-a4.pdf','print-fullsize.pdf','使用说明.pdf','使用说明.txt',
           'straight-skirt-eu40.sloper','measurements-eu40.slm',
           'print-a4.slayout','print-fullsize.slayout','cutting-layout.svg','cutting-layout.dxf',
           'draft-preview.png','draft-preview.svg','validation-summary.json',
           'validation-opensloper.json','material-estimate.json','build_pattern.py','mcp-calls.jsonl']
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>基础直身裙 EU40</title><style>body{font:16px/1.7 system-ui,sans-serif;max-width:1000px;margin:40px auto;padding:0 24px;color:#193d34;background:#fafbf8}h1{font-size:36px}a{color:#1b6653}img{width:100%;background:white;border:1px solid #d4dfd7}li{margin:.45rem 0}.intro{font-size:18px}nav{display:flex;flex-wrap:wrap;gap:12px}nav a{background:#e1eee5;padding:12px 18px;border-radius:6px}small{color:#50675c}</style><h1>基础直身裙 · EU40</h1><p class="intro">人体腰围 74 cm / 臀围 98 cm；成衣腰围 75 cm / 臀围 102 cm。裙身 60 cm + 腰头 4 cm。</p><p>采用 <a href="https://www.burdastyle.com/how-to-take-measurements">Burda 官方 40 号</a>作标准参考。先做胚布试穿。</p><nav><a href="print-a4.pdf" download>A4 拼接纸样 · 14 页</a><a href="print-fullsize.pdf" download>大幅面纸样 · 真比例</a><a href="使用说明.pdf" download>中文使用说明</a><a href="../straight-skirt-eu40.zip" download>全部文件 ZIP</a></nav><p><strong>打印选 100% / 实际大小，先量 10 × 10 cm 校准方框。</strong>纸样已含缝份；省道布料保留。</p><img src="draft-preview.png" alt="左后片、右前片、下方腰头的纸样预览"><h2>包含文件</h2><ul>'''
    page += ''.join(f'<li><a href="{html.escape(f)}" download>{html.escape(f)}</a></li>' for f in files)
    page += '</ul><small>OpenSloper MCP 已检查：几何问题 0，侧缝长度差 0.00 mm。预览图不用于按比例裁剪。</small></html>'
    (ROOT/'index.html').write_text(page)
    files.append('index.html')
    DELIVERY.mkdir(parents=True,exist_ok=True)
    for name in files: shutil.copy2(ROOT/name,DELIVERY/name)
    archive=DELIVERY.parent/'straight-skirt-eu40.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for name in files: z.write(DELIVERY/name,'straight-skirt-eu40/'+name)
    print('Delivery folder:',DELIVERY)
    print('ZIP:',archive,archive.stat().st_size,'bytes')


if __name__=='__main__': main()
