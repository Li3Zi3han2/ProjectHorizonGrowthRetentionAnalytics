"""Python translation of the existing player state machine; no Wolfram runtime."""
import csv
import io
import math
from datetime import date, timedelta
import numpy as np
from .config import CONFIG, ROOT, OUT
from .database import connect, resolve_sql, save_json

HEADERS = {
    'users':['user_id','register_date','market','acquisition_channel','campaign','device','platform','age_bucket','latent_player_archetype','acquisition_quality'],
    'sessions':['session_id','user_id','session_date','session_number','session_minutes','device','fps_quality_bucket','crash_flag'],
    'progression':['user_id','event_date','chapter','level','tutorial_completed','core_loop_unlocked','boss_attempts','boss_failures'],
    'gameplay_events':['event_id','user_id','event_time','event_type','event_value'],
    'monetization':['transaction_id','user_id','transaction_date','product_type','amount_usd'],
    'acquisition':['user_id','market','channel','campaign','creative','acquisition_date'],
    'content_exposure':['user_id','date','content_type','content_id','exposed','clicked']}
DATES = [(date.fromisoformat(CONFIG['start_date'])+timedelta(days=d)).isoformat() for d in range(180)]
REGISTRATION_WEIGHTS = np.array([1+.004*d+.6*(120<=d<=127) for d in range(180)])
REGISTRATION_WEIGHTS /= REGISTRATION_WEIGHTS.sum()


def player(uid, seed, counters):
    rng = np.random.RandomState(seed+uid)
    reg = int(rng.choice(180, p=REGISTRATION_WEIGHTS))
    market = rng.choice(['CN','JP','KR','US','DE'], p=[.25,.18,.12,.3,.15])
    channel = rng.choice(['organic','store_feature','creator','video_ads','referral','cross_promo'], p=[.20,.10,.17,.32,.09,.12])
    device = rng.choice(['PC','iOS','Android'], p=[.25,.3,.45])
    arch = rng.choice(['story','combat','collector','social','casual'])
    effect = {'organic':.10,'creator':.12 if market in ['JP','KR'] else .04,'video_ads':-.06,'referral':.12,'cross_promo':.02}.get(channel,0)
    quality = float(np.clip(.48+effect+rng.normal(0,.15),.05,.95))
    campaign = channel+'_'+str(rng.randint(1,4))
    if campaign == 'video_ads_3': quality = max(.05,quality-.09)
    eng = float(np.clip(.35+.4*quality+rng.normal(0,.19),.03,.98))
    skill = float(np.clip(rng.random_sample()+.20*(arch=='combat')-.20*(arch=='casual'),.05,.95))
    soc = float(np.clip(rng.random_sample()+.25*(channel=='referral')+.2*(arch=='social'),0,1))
    fit, spend = rng.uniform(.25,.95), rng.random_sample()
    rows = {t:[] for t in HEADERS}
    rows['users'].append([uid,DATES[reg],market,channel,campaign,device,'desktop' if device=='PC' else 'mobile',rng.choice(['18-24','25-34','35+']),arch,quality])
    rows['acquisition'].append([uid,market,channel,campaign,'creative_'+str(uid%4+1),DATES[reg]])
    rr = rng.random_sample((180,13))
    alive,streak,n,ch,tut,core,wall,socialn,paid,sn = 1,0,0,0,0,0,0,0,0,0
    mobile, android = device!='PC', device=='Android'
    for k,d in enumerate(range(reg,180)):
        r=rr[k]
        p=max(.03,.16+.22*eng+.08*fit+.16*math.exp(-k/3)-.025*mobile-.045*android-.035*wall) if alive else .0015+.002*eng
        if 120<=d<=124 and streak>=14:
            p=max(p,.008+.015*eng+.010*min(1,n/15)+.006*min(1,ch/3)+.009*min(1,socialn/5)+.008*paid+.008*quality)
        if k and r[0]>=p:
            streak+=1
            continue
        alive=1;streak=0;n+=1
        oldch,oldtut,oldcore=ch,tut,core
        att=fail=social=activity=0;money=0
        fps=1 if android and r[1]<(.48 if d<60 else .20) else (2 if r[1]<.72 else 3)
        crash=int(r[2]<(.13 if fps==1 else .017))
        if tut==0 and r[3]<.76+.13*eng: tut=1
        if tut and core==0 and r[4]<.73+.13*fit: core=1;ch=1
        if core and ch==1 and n>=2 and r[5]<.75: ch=2
        if ch==2 and n>=2:
            att=1+int(r[6]<.5)
            if r[7]<1-(1-(.22+.45*skill+.10*fit-.065*mobile))**att:
                ch=3;fail=att-1;wall=0
            else: fail=att;wall=1
        if ch>=3 and n>=12 and n%8==0: ch=min(6,ch+1)
        if ch>=3 and r[8]<.46+.28*fit+(.08 if d>=120 else 0): activity=1
        if ch>=3 and activity and r[9]<.10+.40*soc+.15*eng: social=1
        if r[10]<(.001+.003*spend+.001*eng+.0005*fit+.0005*min(1,ch/3) if paid==0 else .02+.03*spend):
            money=4.99 if r[11]<.7 else 19.99
        socialn+=social
        if money: paid=1
        minutes=max(2,(18+36*eng+12*fit+12*r[11])*(1-.45*crash))
        ns=1+int(rng.random_sample()<.15+.25*eng)+int(rng.random_sample()<.025+.035*eng)
        weights=rng.uniform(.7,1.3,ns);weights/=weights.sum()
        for j in range(ns):
            counters['sessions']+=1;sn+=1
            rows['sessions'].append([counters['sessions'],uid,DATES[d],sn,float(minutes*weights[j]),device,fps,crash if j==0 else 0])
        rows['progression'].append([uid,DATES[d],ch,12 if ch==2 else max(1,ch*4),tut,core,att,fail])
        events=[]
        if n==1: events.append(('tutorial_start',1))
        if tut>oldtut: events.append(('tutorial_complete',1))
        if core>oldcore: events.append(('core_loop_unlock',1))
        events.extend(('chapter_complete',cc) for cc in range(oldch+1,ch+1))
        if att:
            events.append(('boss_attempt',att))
            if fail<att: events.append(('boss_clear',1))
        if activity: events.extend([('activity_enter',1),('activity_complete',1)])
        if ch>=3 and oldch<3: events.append(('social_unlock',1))
        if social: events.append(('social_interaction',1))
        for ei,(kind,value) in enumerate(events,1):
            counters['gameplay_events']+=1
            rows['gameplay_events'].append([counters['gameplay_events'],uid,f'{DATES[d]} 12:{ei:02d}:00',kind,value])
        if money:
            counters['monetization']+=1
            rows['monetization'].append([counters['monetization'],uid,DATES[d],'starter_or_cosmetic',money])
        if d%7==0:
            rows['content_exposure'].append([uid,DATES[d],'patch2_event' if d>=120 else 'weekly_content','content_'+str(d//7),1,activity])
        if r[12]<.04+.06*(1-eng)+.14*math.exp(-k/6)+.04*wall+.05*crash: alive=0
    return rows


def generate(users):
    counters={'sessions':0,'gameplay_events':0,'monetization':0}
    # One transaction in a new build schema: a failure cannot publish partial facts.
    with connect() as con, con.cursor() as cur:
        cur.execute(resolve_sql((ROOT/'sql/00_create_schema.sql').read_text()))
        for batch in range(1,users+1,CONFIG['batch_size']):
            rows={t:[] for t in HEADERS}
            for uid in range(batch,min(users+1,batch+CONFIG['batch_size'])):
                for t,values in player(uid,CONFIG['seed'],counters).items(): rows[t].extend(values)
            for t,values in rows.items():
                stream=io.StringIO(newline='');csv.writer(stream,lineterminator='\n').writerows(values)
                with cur.copy(resolve_sql(f'COPY horizon.{t} FROM STDIN WITH (FORMAT CSV)')) as copy:
                    copy.write(stream.getvalue().encode())
            if (batch-1)%10000==0: print(f'Python generated / loaded users {min(users,batch+CONFIG["batch_size"]-1)}',flush=True)
        cur.executemany(resolve_sql('INSERT INTO horizon.run_metadata VALUES(%s,%s)'), [('users',str(users)),('seed',str(CONFIG['seed'])),('generator','Python'),('status','generated')])
    save_json(OUT/'metrics/generation.json',dict(users=users,seed=CONFIG['seed'],sessions=counters['sessions'],events=counters['gameplay_events'],transactions=counters['monetization'],generator='Python'))
