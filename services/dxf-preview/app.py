"""Stateless, bounded FastAPI entrypoint for Vercel's Python runtime."""
from pathlib import Path
import asyncio, base64, hashlib, io, json, logging, threading, time, zipfile
from fastapi import FastAPI, Request
from fastapi.responses import Response, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from converter.core import convert_dxf, ConversionError, ENGINE_VERSION, MAX_INPUT_BYTES, parse_dxf, register, get_profile

ROOT=Path(__file__).resolve().parent
app=FastAPI(title='Pattern Agent 纸样三维预览',version=ENGINE_VERSION)
app.add_middleware(CORSMiddleware,allow_origins=['https://liush2yuxjtu.github.io'],allow_methods=['GET','POST'],allow_headers=['Content-Type'],expose_headers=['X-Conversion-Id','X-Output-Sha256'])
app.mount('/assets',StaticFiles(directory=ROOT/'public'),name='assets')
_slots=threading.BoundedSemaphore(1)
logger=logging.getLogger('pattern-agent')

def source_files():
    # Vercel rewrites vercel.json while packaging; its uploaded hash is archived separately.
    files=[ROOT/'app.py',ROOT/'pyproject.toml',ROOT/'converter/core.py',ROOT/'converter/profile.json',*sorted((ROOT/'public').glob('*'))]
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
SOURCE_FILES=source_files()
SOURCE_SHA256=hashlib.sha256(json.dumps(SOURCE_FILES,sort_keys=True,separators=(',',':')).encode()).hexdigest()

@app.exception_handler(ConversionError)
async def conversion_error(request,exc):
    logger.warning(json.dumps({'event':'conversion_rejected','code':exc.code}))
    return JSONResponse({'status':'rejected','error':{'code':exc.code,'message':str(exc)},'supported_profiles_url':'/api/profiles'},status_code=exc.status,headers={'Cache-Control':'no-store'})

@app.get('/')
def home():return FileResponse(ROOT/'public/index.html')

@app.get('/api/health')
def health():
    return {'status':'ok','engine_version':ENGINE_VERSION,'source_sha256':SOURCE_SHA256,'source_files':SOURCE_FILES,'mode':'visual_preview','execution':'synchronous_stateless','storage':'no_uploaded_file_persistence','supported_profiles':[get_profile()['id']],'max_input_bytes':MAX_INPUT_BYTES,'physical_fit':'NOT_RUN'}

@app.get('/api/profiles')
def profiles():
    p=get_profile()
    return {'profiles':[{'id':p['id'],'version':p['version'],'description':p['description'],'expected_polylines':p['expected_polylines'],'units':['mm','cm','inch'],'min_physical_scale':p['min_scale'],'max_physical_scale':p['max_scale'],'max_match_deviation_mm':p['max_match_deviation_mm'],'arbitrary_garment_dxf':False,'calibrated_cloth_simulation':False}],'input':'POST raw DXF body; explicitly set units query parameter','outputs':['glb','json','bundle'],'job_status':'Requests complete synchronously; conversion IDs are deterministic identifiers, not persisted jobs.'}

async def input_bytes(request):
    data=bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data)>MAX_INPUT_BYTES:raise ConversionError('INPUT_SIZE','文件超过512千字节限制。',413)
    return bytes(data)

def options(request):
    params=request.query_params
    unknown=set(params)-{'units','profile','format'}
    if unknown:raise ConversionError('UNKNOWN_OPTION','包含未知转换参数。',400)
    units=params.get('units','');profile=params.get('profile','fitted-tshirt-v1');fmt=params.get('format','glb')
    if fmt not in ['glb','json','bundle']:raise ConversionError('UNKNOWN_FORMAT','输出格式必须为glb、json或bundle。',400)
    return units,profile,fmt

API_DOC = {'parameters':[
    {'name':'units','in':'query','required':True,'schema':{'type':'string','enum':['mm','cm','inch']},'description':'原文件单位，必须显式指定'},
    {'name':'profile','in':'query','required':False,'schema':{'type':'string','default':'fitted-tshirt-v1'}},
    {'name':'format','in':'query','required':False,'schema':{'type':'string','enum':['glb','json','bundle'],'default':'glb'}}
], 'requestBody':{'required':True,'content':{'application/dxf':{'schema':{'type':'string','format':'binary'}}}}}

@app.post('/api/analyze',openapi_extra=API_DOC)
async def analyze(request:Request):
    units,profile,_=options(request);data=await input_bytes(request)
    def work():
        p,source=parse_dxf(data);_,_,match=register(p,units,profile)
        return {'status':'supported','source':source,'matching':match,'engine_version':ENGINE_VERSION,'physical_fit':'NOT_RUN'}
    return await asyncio.to_thread(work)

def bundle(result):
    """Offline viewer reuses the same actual generated GLB; no remote CDN."""
    html=(ROOT/'public/offline.html').read_text()
    html=html.replace('__GENERATED_GLB__',base64.b64encode(result.glb).decode()).replace('__RENDERER_JS__',(ROOT/'public/renderer.js').read_text())
    files={'model.glb':result.glb,'report.json':json.dumps(result.report,ensure_ascii=False,indent=2).encode(),'preview.html':html.encode(),'viewer.js':(ROOT/'public/renderer.js').read_bytes()}
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
        for name,data in files.items():
            i=zipfile.ZipInfo(name,(1980,1,1,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;z.writestr(i,data)
    return buf.getvalue()

@app.post('/api/preview',openapi_extra=API_DOC)
async def preview(request:Request):
    units,profile,fmt=options(request);data=await input_bytes(request)
    def work():
        if not _slots.acquire(blocking=False):raise ConversionError('BUSY','当前实例正在转换，请稍后重试。',503)
        started=time.monotonic()
        try:result=convert_dxf(data,units=units,profile=profile)
        finally:_slots.release()
        logger.info(json.dumps({'event':'conversion_complete','conversion_id':result.report['conversion_id'],'seconds':round(time.monotonic()-started,3),'output_bytes':len(result.glb)}))
        return result
    result=await asyncio.to_thread(work)
    headers={'Cache-Control':'no-store','X-Conversion-Id':result.report['conversion_id'],'X-Output-Sha256':result.report['output_sha256'],'X-Content-Type-Options':'nosniff'}
    if fmt=='json':return JSONResponse({'report':result.report,'glb_base64':base64.b64encode(result.glb).decode()},headers=headers)
    if fmt=='bundle':
        headers['Content-Disposition']='attachment; filename="pattern-agent-preview.zip"'
        return Response(bundle(result),media_type='application/zip',headers=headers)
    headers['Content-Disposition']='attachment; filename="pattern-agent-preview.glb"'
    return Response(result.glb,media_type='model/gltf-binary',headers=headers)
