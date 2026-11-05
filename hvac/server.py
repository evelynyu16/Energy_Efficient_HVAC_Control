from pathlib import Path
import os,sqlite3,json
from functools import lru_cache
from threading import RLock
from uuid import uuid4
from contextlib import closing
from fastapi import FastAPI,HTTPException
from fastapi.staticfiles import StaticFiles
from engine import *
ROOT=Path(__file__).resolve().parent
DB=os.getenv("HVAC_DB",str(ROOT/"hvac.sqlite3"))
app=FastAPI(title="Roomwise HVAC Simulator")
lock=RLock()
def dump(x):return json.dumps(x,allow_nan=False)
def connect():
    db=sqlite3.connect(DB);db.row_factory=sqlite3.Row
    db.executescript('CREATE TABLE IF NOT EXISTS datasets(id TEXT PRIMARY KEY,name TEXT,rows TEXT); CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY,ds TEXT,config TEXT,state TEXT); CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,sid TEXT,stamp TEXT,kind TEXT,detail TEXT);');return db
@lru_cache(maxsize=4)
def rows_for(ds):
    with closing(connect()) as db:return json.loads(db.execute('select rows from datasets where id=?',(ds,)).fetchone()[0])
def new(db,ds,c):
    sid=uuid4().hex[:12];db.execute('insert into sessions values(?,?,?,?)',(sid,ds,dump(c),dump(initial())));return sid
def event(db,sid,r,kind,detail):
    db.execute('insert into events(sid,stamp,kind,detail) values(?,?,?,?)',(sid,r['date'] if r else None,kind,dump(dict(detail=detail,reading=r))))
def view(db,sid):
    q=db.execute('select * from sessions where id=?',(sid,)).fetchone()
    if not q:raise HTTPException(404,'Unknown session')
    s=json.loads(q['state']);rs=rows_for(q['ds']);i=s['i']
    ev=[{**dict(e),'detail':json.loads(e['detail'])} for e in db.execute('select * from events where sid=? order by id desc limit 100',(sid,))]
    return dict(id=sid,source=db.execute('select name from datasets where id=?',(q['ds'],)).fetchone()[0],settings=json.loads(q['config']),state=s,total=len(rs),current=rs[i] if i>=0 else None,trend=rs[max(0,i-59):i+1],events=ev)
@app.get('/api/session')
def latest():
    with lock,closing(connect()) as db,db:
        q=db.execute('select id from sessions order by rowid desc limit 1').fetchone()
        if q:return view(db,q[0])
        rs=parse([(p.name,p.read_text()) for p in sorted((ROOT/'data').glob('*.txt'))]);db.execute('insert or ignore into datasets values(?,?,?)',('uci','UCI • Office occupancy',dump(rs)));sid=new(db,'uci',D);db.commit();return view(db,sid)
@app.get('/api/history')
def history():
    with closing(connect()) as db:return [dict(x) for x in db.execute('select s.id,d.name,json_extract(s.state,"$.i")+1 as readings from sessions s join datasets d on d.id=s.ds order by s.rowid desc')]
@app.get('/api/session/{sid}')
def get(sid:str):
    with closing(connect()) as db:return view(db,sid)
@app.post('/api/session/{sid}/{action}')
def command(sid:str,action:str,payload:dict):
    try:
        with lock,closing(connect()) as db,db:
            q=db.execute('select * from sessions where id=?',(sid,)).fetchone()
            if not q:raise HTTPException(404,'Unknown session')
            s=json.loads(q['state']);c=json.loads(q['config']);rs=rows_for(q['ds']);ds=q['ds']
            def reading():return rs[s['i']] if s['i']>=0 else None
            def log(kind,info):event(db,sid,reading(),kind,info)
            if action in ('step','tick','finish'):
                for _ in range(len(rs) if action=='finish' else 1):
                    if (action=='tick' and not s['run']) or s['i']>=len(rs)-1:break
                    old=s['mode'];advance(s,rs,c)
                    if old!=s['mode']:log('Mode',f"{old} → {s['mode']}: {s['reason']}")
            elif action in ('play','pause'):s['run']=action=='play' and s['i']<len(rs)-1
            elif action in ('reset','import'):
                s['run']=False;db.execute('update sessions set state=? where id=?',(dump(s),sid))
                if action=='import':
                    txt=payload.get('text','')
                    if len(txt)>5_000_000:raise ValueError('Maximum file size is 5 MB.')
                    loaded=parse([(payload.get('name','CSV'),txt)]);ds=uuid4().hex
                    db.execute('insert into datasets values(?,?,?)',(ds,payload.get('name','CSV'),dump(loaded)))
                newid=new(db,ds,c);db.commit();return view(db,newid)
            elif action in ('settings','manual'):
                old=s['mode'];release=False
                if action=='settings':
                    updated=settings(payload);log('Settings',{'before':c,'after':updated});c=updated
                else:
                    val=payload.get('mode')
                    if val not in (None,'Heating','Cooling','Standby','Eco'):raise ValueError('Unknown mode')
                    release=val is None;s['manual']=val;log('Control',val or 'Automatic')
                if reading() and old!='Unavailable':decide(s,reading(),c,release=release)
                if old!=s['mode']:log('Mode',f"{old} → {s['mode']}: {s['reason']}")
            else:raise HTTPException(404,'Unknown action')
            db.execute('update sessions set state=?,config=? where id=?',(dump(s),dump(c),sid));db.commit();return view(db,sid)
    except (ValueError,TypeError,KeyError) as e:raise HTTPException(422,str(e))
app.mount('/',StaticFiles(directory=ROOT/'dist',html=True,check_dir=False),name='web')
