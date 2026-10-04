import base64, json, os, re, time, uuid
from datetime import datetime
from pathlib import Path
BASE=Path(__file__).parent
DATA=Path(os.environ.get('WELD_DATA_DIR','/tmp/weld-inspections' if os.environ.get('VERCEL') else str(BASE)))
if os.environ.get('VERCEL'):
    DATA.mkdir(parents=True,exist_ok=True)
    os.environ.setdefault('WELD_DB_PATH',str(DATA/'weld_inspections.db'))
import cv2, numpy as np
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from database import init_db, connect
from ml.detector import WeldDetector
from services.reports import create_report

UPLOADS=DATA/'uploads'; REPORTS=DATA/'generated_reports'; SAMPLES=BASE/'sample_images'
for p in (UPLOADS,REPORTS,SAMPLES): p.mkdir(parents=True,exist_ok=True)
app=FastAPI(title='AI Welding Inspection API',version='1.0.0')
app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:5173','http://127.0.0.1:5173'],allow_methods=['*'],allow_headers=['*'])
detector=WeldDetector(); init_db()

def make_samples():
    # Synthetic, clearly illustrative weld textures for immediate offline demos.
    rng=np.random.default_rng(17); h,w=480,800
    for kind,name in [('crack','sample_crack.jpg'),('porosity','sample_porosity.jpg'),('fusion','sample_incomplete_fusion.jpg'),('good','sample_good_weld.jpg')]:
        if (SAMPLES/name).exists(): continue
        im=np.zeros((h,w,3),np.uint8); im[:]=(27,34,43)
        for y in range(h):
            shade=int(95+45*np.cos((y-h/2)/80)+rng.normal(0,3)); im[y,70:730]=(shade,shade+4,shade+8)
        cv2.rectangle(im,(68,80),(732,400),(65,76,88),3)
        for x in range(90,720,24): cv2.line(im,(x,110),(x+8,370),(128,137,147),1)
        cv2.ellipse(im,(400,240),(225,78),0,0,360,(170,177,184),-1)
        cv2.ellipse(im,(400,240),(207,60),0,0,360,(124,135,146),-1)
        if kind=='crack': cv2.polylines(im,[np.array([[330,203],[354,225],[345,244],[382,265],[371,292],[418,316]])],False,(30,28,27),8)
        elif kind=='porosity':
            for x,y,r in [(344,220,10),(390,246,13),(434,220,8),(458,266,11),(367,278,7),(421,292,6)]: cv2.circle(im,(x,y),r,(37,40,44),-1); cv2.circle(im,(x-2,y-2),max(2,r//3),(178,182,186),2)
        elif kind=='fusion': cv2.line(im,(400,170),(405,306),(36,38,41),15)
        cv2.putText(im,'DEMO SAMPLE · '+kind.upper(),(22,455),cv2.FONT_HERSHEY_SIMPLEX,.7,(222,229,235),2)
        cv2.imwrite(str(SAMPLES/name),im)
make_samples()

class Login(BaseModel): username:str; password:str
@app.get('/api/health')
def health(): return {'status':'ok','model':'trained' if detector.model.available else 'prototype_fallback'}
@app.post('/api/auth/login')
def login(data:Login):
    if data.username=='admin' and data.password=='admin123': return {'ok':True,'user':'AI Inspector','token':'local-demo-session'}
    raise HTTPException(401,'Invalid username or password')
@app.get('/api/dashboard/stats')
def stats():
    with connect() as db:
        rows=db.execute('SELECT verdict,COUNT(*) n FROM inspections GROUP BY verdict').fetchall()
        total=db.execute('SELECT COUNT(*) FROM inspections').fetchone()[0]
        failed=db.execute("SELECT COUNT(*) FROM inspections WHERE verdict='FAIL'").fetchone()[0]
        defects=db.execute("SELECT COUNT(*) FROM inspections WHERE defect_type!='No Defect'").fetchone()[0]
        recent=[dict(r) for r in db.execute('SELECT id,inspection_id,timestamp,filename,defect_type,confidence,severity,verdict,processing_time FROM inspections ORDER BY id DESC LIMIT 5')]
    return {'total':total,'passed':total-failed,'failed':failed,'defects':defects,'recent':recent}
@app.get('/api/samples')
def samples(): return [{'name':p.name,'url':'/api/samples/'+p.name} for p in sorted(SAMPLES.glob('*.jpg'))]
@app.get('/api/samples/{name}')
def sample(name:str):
    if Path(name).name!=name or not name.endswith('.jpg'): raise HTTPException(404,'Sample not found')
    path=SAMPLES/name
    if not path.exists(): raise HTTPException(404,'Sample not found')
    return FileResponse(path,media_type='image/jpeg')
def inline_jpeg(image):
    h,w=image.shape[:2]; scale=min(1.0,1280/max(h,w))
    if scale<1: image=cv2.resize(image,(int(w*scale),int(h*scale)),interpolation=cv2.INTER_AREA)
    ok, encoded=cv2.imencode('.jpg',image,[int(cv2.IMWRITE_JPEG_QUALITY),82])
    if not ok: raise HTTPException(500,'Could not prepare inspection preview')
    return 'data:image/jpeg;base64,'+base64.b64encode(encoded).decode('ascii')

def annotate(image, result, path):
    x,y,w,h=result['bbox']; out=image.copy(); color=(55,220,120) if result['verdict']=='PASS' else (40,85,240)
    cv2.rectangle(out,(x,y),(x+w,y+h),color,3)
    label=f"{result['defect_type']}  {result['confidence']:.0%}"
    cv2.rectangle(out,(x,max(0,y-32)),(min(out.shape[1],x+290),y),color,-1)
    cv2.putText(out,label,(x+7,max(20,y-10)),cv2.FONT_HERSHEY_SIMPLEX,.62,(255,255,255),2,cv2.LINE_AA)
    cv2.putText(out,'PROTOTYPE ROI',(12,28),cv2.FONT_HERSHEY_SIMPLEX,.55,(240,240,240),1,cv2.LINE_AA)
    cv2.imwrite(str(path),out)
@app.post('/api/inspection/analyze')
async def analyze(image:UploadFile|None=File(None), sample_name:str|None=Form(None)):
    filename=Path(image.filename or 'weld.jpg').name if image else 'weld.jpg'
    if sample_name:
        allowed={'sample_crack.jpg':'crack','sample_porosity.jpg':'porosity','sample_incomplete_fusion.jpg':'fusion','sample_good_weld.jpg':'good'}
        if sample_name not in allowed: raise HTTPException(400,'Unknown sample image')
        source=SAMPLES/sample_name; payload=source.read_bytes(); hint=allowed[sample_name]; filename=sample_name
    else:
        if Path(filename).suffix.lower() not in ('.jpg','.jpeg','.png'): raise HTTPException(400,'Upload a JPG, JPEG or PNG image')
        if image is None: raise HTTPException(400,'Choose an image to analyze')
        payload=await image.read()
        if not payload: raise HTTPException(400,'Choose an image to analyze')
        if len(payload)>10*1024*1024: raise HTTPException(413,'Image must be smaller than 10 MB')
        hint=None
    arr=cv2.imdecode(np.frombuffer(payload,np.uint8),cv2.IMREAD_COLOR)
    if arr is None: raise HTTPException(400,'The selected file is not a readable image')
    start=time.perf_counter(); result=detector.analyze(arr,hint); elapsed=time.perf_counter()-start
    inspection_id='WELD-'+datetime.now().strftime('%Y')+'-'+uuid.uuid4().hex[:6].upper()
    image_path=UPLOADS/(inspection_id+Path(filename).suffix.lower()); annotated_path=UPLOADS/(inspection_id+'_annotated.jpg')
    image_path.write_bytes(payload); annotate(arr,result,annotated_path)
    defect=result['defect_type']; summary=(f'No major defect pattern was detected in the inspected region. Overall quality is marked PASS.' if defect=='No Defect' else f'Potential {defect.lower()}-like discontinuity detected in the weld region. Further inspection is recommended. This prototype result is not a certified inspection.')
    stamp=datetime.now().astimezone().isoformat(timespec='seconds')
    values=(inspection_id,stamp,filename,str(image_path),str(annotated_path),defect,result['confidence'],result['severity'],result['verdict'],elapsed,None,summary,result['analysis_mode'],json.dumps(result['bbox']))
    with connect() as db: cur=db.execute('INSERT INTO inspections(inspection_id,timestamp,filename,image_path,annotated_path,defect_type,confidence,severity,verdict,processing_time,report_path,summary,analysis_mode,bbox) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',values); rowid=cur.lastrowid
    record=get_record(rowid); annotated=cv2.imread(str(annotated_path));
    return public(record) | {'image_data_url':inline_jpeg(arr),'annotated_data_url':inline_jpeg(annotated)}
def get_record(id):
    with connect() as db: row=db.execute('SELECT * FROM inspections WHERE id=?',(id,)).fetchone()
    if not row: raise HTTPException(404,'Inspection not found')
    return dict(row)
def public(r):
    return {k:r[k] for k in ['id','inspection_id','timestamp','filename','defect_type','confidence','severity','verdict','processing_time','summary','analysis_mode']} | {'image_url':f"/api/inspection/{r['id']}/image",'annotated_url':f"/api/inspection/{r['id']}/annotated",'report_url':f"/api/report/{r['id']}/download",'bbox':json.loads(r['bbox'])}
@app.get('/api/inspection/history')
def history():
    with connect() as db: rows=db.execute('SELECT * FROM inspections ORDER BY id DESC').fetchall()
    return [public(dict(r)) for r in rows]
@app.get('/api/inspection/{id}')
def inspection(id:int): return public(get_record(id))
@app.get('/api/inspection/{id}/image')
def original(id:int): return FileResponse(get_record(id)['image_path'])
@app.get('/api/inspection/{id}/annotated')
def annotated(id:int): return FileResponse(get_record(id)['annotated_path'])
@app.delete('/api/inspection/{id}')
def delete(id:int):
    r=get_record(id)
    for k in ('image_path','annotated_path','report_path'):
        if r[k] and Path(r[k]).exists(): Path(r[k]).unlink()
    with connect() as db: db.execute('DELETE FROM inspections WHERE id=?',(id,))
    return {'ok':True}
@app.post('/api/report/{id}')
def report(id:int):
    r=get_record(id); p=REPORTS/(r['inspection_id']+'.pdf'); create_report(r,p)
    with connect() as db: db.execute('UPDATE inspections SET report_path=? WHERE id=?',(str(p),id))
    return {'ok':True,'download_url':f'/api/report/{id}/download'}
@app.get('/api/report/{id}/download')
def download(id:int):
    r=get_record(id); p=Path(r['report_path']) if r['report_path'] else REPORTS/(r['inspection_id']+'.pdf')
    if not p.exists(): create_report(r,p); 
    with connect() as db: db.execute('UPDATE inspections SET report_path=? WHERE id=?',(str(p),id))
    return FileResponse(p,media_type='application/pdf',filename=r['inspection_id']+'_inspection_report.pdf')
