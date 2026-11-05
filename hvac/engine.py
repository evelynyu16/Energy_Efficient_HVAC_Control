"""All timers use recorded time, never UI playback speed."""
import csv,io,math
from datetime import datetime
D=dict(low=20.,high=24.,band=.5,hold=5.,vacancy=10.,start="08:00",end="18:00")
ACTIVE={"Heating","Cooling"}
def settings(c):
    if set(c)!=set(D): raise ValueError("Incomplete settings.")
    for k in ("low","high","band","hold","vacancy"):
        if type(c[k]) not in (int,float) or not math.isfinite(c[k]): raise ValueError(f"Invalid {k}")
    if not (c["low"]<c["high"] and 0<=c["band"]<(c["high"]-c["low"])/2 and min(c["hold"],c["vacancy"])>=0): raise ValueError("Check comfort bounds, hysteresis and durations.")
    for k in ("start","end"):
        if datetime.strptime(c[k],"%H:%M").strftime("%H:%M")!=c[k]: raise ValueError("Use HH:MM.")
    if c["start"]>=c["end"]: raise ValueError("Schedule end must follow start (same day).")
    return c
def parse(files):
    rows={}
    for name,txt in files:
        rd=csv.reader(io.StringIO(txt.lstrip('\ufeff'))); header=next(rd,[])
        keys=['date','Temperature','Humidity','Occupancy']
        if not all(k in header for k in keys): raise ValueError(f"{name}: expected {', '.join(keys)}")
        for n,row in enumerate(rd,2):
            if not row: continue
            if len(row)==len(header)+1: row=row[1:] # UCI row number
            try:
                if len(row)!=len(header):raise ValueError()
                d=dict(zip(header,row)); ts=datetime.fromisoformat(d['date'])
                if ts.tzinfo is not None:raise ValueError()
                t,h,o=float(d['Temperature']),float(d['Humidity']),int(d['Occupancy'])
                if not math.isfinite(t) or not 0<=h<=100 or o not in (0,1):raise ValueError()
            except (ValueError,OverflowError):raise ValueError(f"{name}, line {n}: invalid reading.")
            r=dict(date=ts.isoformat(sep=' '),temp=t,humidity=h,occupied=o)
            if r['date'] in rows and rows[r['date']]!=r:raise ValueError(f"{name}, line {n}: conflicting timestamp.")
            rows[r['date']]=r
    if not rows:raise ValueError("No readings found.")
    return [rows[k] for k in sorted(rows)]
def initial():
    return dict(i=-1,mode="Ready",base="Ready",since=None,bsince=None,vac=None,manual=None,run=False,a=0.,b=0.,excluded=0.,gap=0.,reason="Start or step through the readings.")
def mins(a,b):return (datetime.fromisoformat(b)-datetime.fromisoformat(a)).total_seconds()/60
def thermostat(temp,old,since,ts,c):
    if old in ACTIVE|{'Standby'} and since and mins(since,ts)<c['hold']:return old,"Minimum mode duration"
    if old=='Heating' and temp<c['low']+c['band']:return old,"Heating hysteresis"
    if old=='Cooling' and temp>c['high']-c['band']:return old,"Cooling hysteresis"
    if temp<c['low']:return 'Heating','Below lower limit'
    if temp>c['high']:return 'Cooling','Above upper limit'
    return 'Standby','Within comfort range'
def decide(s,r,c,gap=False,release=False):
    ts=r['date']; t=r['temp'];clock=ts[11:16]
    if gap:s['vac']=None
    elif r['occupied']:s['vac']=None
    elif s['vac'] is None:s['vac']=ts
    if gap:m,b,why='Unavailable','Unavailable','Input gap exceeds five minutes'
    else:
        b=(thermostat(t,s['base'],s['bsince'],ts,c)[0] if c['start']<=clock<c['end'] else 'Eco')
        if s['manual']:m,why=s['manual'],'Manual override'
        elif s['vac'] and mins(s['vac'],ts)>=c['vacancy']:m,why='Eco','Vacancy delay reached'
        else:m,why=thermostat(t,s['mode'] if not release else 'Ready',s['since'],ts,c)
    if m!=s['mode']:s['since']=ts
    if b!=s['base']:s['bsince']=ts
    s.update(mode=m,base=b,reason=why)
def advance(s,rows,c):
    if s['i']+1>=len(rows):s['run']=False;return
    old=s['i'];s['i']+=1;r=rows[s['i']];delta=mins(rows[old]['date'],r['date']) if old>=0 else 0
    gap=delta>5
    if gap or s['mode']=='Unavailable' or s['manual']:
        s['excluded']+=delta
        if gap:s['gap']+=delta
    else:
        if s['mode'] in ACTIVE:s['a']+=delta
        if s['base'] in ACTIVE:s['b']+=delta
    decide(s,r,c,gap)
    if s['i']==len(rows)-1:s['run']=False
