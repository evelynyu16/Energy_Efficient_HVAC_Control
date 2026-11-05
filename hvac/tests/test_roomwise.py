from engine import *
from fastapi.testclient import TestClient
import server,pytest,time
def seq(temps,occ=None,times=None):
    return [dict(date=f"2025-01-01 09:{m:02d}:00",temp=t,humidity=40,occupied=o) for t,o,m in zip(temps,occ or [1]*len(temps),times or range(len(temps)))]
def play(rows,c=D):
    s=initial(); modes=[]
    for _ in rows:advance(s,rows,c);modes.append(s['mode'])
    return modes,s
def test_boundaries_and_hold():
    assert play(seq([19,21,21,21,21,20.5]))[0]==['Heating']*5+['Standby']
    assert play(seq([25,23.6,23.5],times=[0,5,6]))[0]==['Cooling','Cooling','Standby']
    assert play(seq([20,24],times=[0,5]))[0]==['Standby','Standby']
def test_vacancy_and_reference():
    modes,s=play(seq([19]*5,[0,0,0,0,1],[0,5,10,11,12]))
    assert modes==['Heating','Heating','Eco','Eco','Heating']
    assert (s['a'],s['b'])==(10,12)
def test_gap_precedes_manual():
    r=seq([25]*4,times=[0,1,10,11]);s=initial();s['manual']='Heating'
    for i in range(3):advance(s,r,D)
    assert s['mode']=='Unavailable' and s['gap']==9
    advance(s,r,D);assert s['mode']=='Heating' and s['excluded']==11 and s['b']==0
def test_import():
    header='date,Temperature,Humidity,Occupancy\n';a='2025-01-01 09:00:00,21,44,1\n'
    assert len(parse([('a',header+a+a)]))==1
    for bad in [a.replace('21','nan'),a.replace(',44',',110'),a.replace(',1\n',',2\n'),a+a.replace('21','22')]:
        with pytest.raises(ValueError):parse([('a',header+bad)])
def test_api_lifecycle(tmp_path,monkeypatch):
    monkeypatch.setattr(server,'DB',str(tmp_path/'test.db'));server.rows_for.cache_clear()
    client=TestClient(server.app);d=client.get('/api/session').json();sid=d['id'];assert d['total']==20560
    def post(action,payload={}):return client.post('/api/session/'+sid+'/'+action,json=payload)
    assert post('tick').json()['state']['i']==-1
    post('play');durations=[]
    for i in range(100):
        t=time.perf_counter();result=post('tick').json();durations.append(time.perf_counter()-t)
    assert result['state']['i']==99 and max(durations)<1
    post('pause');assert post('tick').json()['state']['i']==99
    assert post('settings',{**D,'high':20}).status_code==422
    assert post('import',{'text':'broken'}).status_code==422
    post('manual',{'mode':'Cooling'});assert post('step').json()['state']['mode']=='Cooling'
    post('manual',{'mode':None});x=post('finish').json()
    assert x['state']['i']==20559 and x['state']['gap']>0
    nxt=post('reset').json();assert nxt['id']!=sid and nxt['state']['i']==-1
    assert TestClient(server.app).get('/api/session/'+sid).json()['events']==x['events']
