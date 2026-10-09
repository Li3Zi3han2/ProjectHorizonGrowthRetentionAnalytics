"""Patch2 silent-user return eligibility; history ends before Patch2."""
import pandas as pd
from .config import START, OUT
from .database import query, save_json

def calculate(raw: dict, metrics: dict) -> dict:
    u,s = raw['users'],raw['sessions']
    patch = pd.Timestamp(START)+pd.Timedelta(days=120)
    silent_start = patch-pd.Timedelta(days=14)
    active = s.loc[s.session_date.between(silent_start,patch-pd.Timedelta(days=1)), 'user_id']
    eligible = u.loc[u.register_date.lt(silent_start)&~u.index.isin(active)]
    after = s.loc[s.user_id.isin(eligible.index)&s.session_date.between(patch,patch+pd.Timedelta(days=6))]
    return_dates = after.groupby('user_id').session_date.min().rename('return_date')
    post = s.join(return_dates,on='user_id')
    post = post.loc[(post.session_date-post.return_date).dt.days.between(0,6)]
    days = post.groupby('user_id').session_date.nunique()
    result = dict(eligible=len(eligible),returned=len(return_dates),post_return_days7=float(days.mean()) if len(days) else 0)
    for key,value in result.items(): metrics[f'reactivation/{key}']=value
    metrics['return_rate'] = len(return_dates)/max(len(eligible),1)
    history = s.loc[s.user_id.isin(eligible.index)&s.session_date.lt(patch)].groupby('user_id').agg(historical_active_days=('session_date','nunique'),historical_minutes=('session_minutes','sum'))
    hp=query("SELECT user_id,max(chapter) history_chapter FROM horizon.progression WHERE event_date<DATE '2026-05-01' GROUP BY user_id").set_index('user_id')
    hm=query("SELECT user_id,sum(amount_usd)::float8 history_spend FROM horizon.monetization WHERE transaction_date<DATE '2026-05-01' GROUP BY user_id").set_index('user_id')
    he=query("SELECT user_id,count(*) history_social FROM horizon.gameplay_events WHERE event_time<DATE '2026-05-01' AND event_type='social_interaction' GROUP BY user_id").set_index('user_id')
    history=history.join(hp).join(hm).join(he).fillna({'history_spend':0,'history_social':0})
    history['returned'] = history.index.isin(return_dates.index).astype(int)
    history['post_return_days7'] = days.reindex(history.index)
    history = history.join(u[['device','acquisition_channel']])
    profile=history.groupby('returned').agg(n=('returned','size'),history_days=('historical_active_days','mean'),history_minutes=('historical_minutes','mean'),history_chapter=('history_chapter','mean'),history_spend=('history_spend','mean'),history_social=('history_social','mean'),post_return_days7=('post_return_days7','mean'))
    profile.to_csv(OUT / 'tables/reactivation_profile.csv')
    for group,row in profile.iterrows():
        for key in ['n','history_days','history_minutes','history_chapter','history_spend','history_social']:
            metrics[f'reactivation/profile/{group}/{key}']=float(row[key])
    history.groupby('device').returned.agg(['count','mean']).to_csv(OUT / 'tables/reactivation_device.csv')
    save_json(OUT / 'metrics/python_reactivation.json',result)
    return result
