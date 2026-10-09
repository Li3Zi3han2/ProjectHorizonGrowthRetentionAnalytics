"""Independent raw-fact session diagnostics and gate experiment eligibility."""
import pandas as pd
from .config import OUT, END
from .database import query, save_json

def gate_population() -> pd.DataFrame:
    p=query('SELECT user_id,event_date,level,boss_attempts,chapter FROM horizon.progression')
    p['event_date']=pd.to_datetime(p.event_date)
    first=p.loc[p.level.eq(12)&p.boss_attempts.gt(0)].groupby('user_id').event_date.min().rename('first_gate_date')
    first=first.loc[first.le(pd.Timestamp(END)-pd.Timedelta(days=3))]
    follow=p.join(first,on='user_id')
    cleared=follow.loc[(follow.event_date-follow.first_gate_date).dt.days.between(0,3)&follow.chapter.ge(3),'user_id']
    result=first.to_frame();result['completed_within3']=result.index.isin(cleared).astype(int)
    result.to_csv(OUT/'tables/python_gate_eligibility.csv')
    return result

def calculate(raw: dict, metrics: dict) -> None:
    s=raw['sessions'];daily=s.groupby(['user_id','session_date']).size()
    values=dict(sessions=len(s),active_user_days=len(daily),sessions_per_active_day=float(daily.mean()),multi_session_day_fraction=float(daily.gt(1).mean()))
    metrics.update({f'session_diagnostics/{k}':v for k,v in values.items()})
    f=pd.read_csv(OUT/'tables/python_features.csv')
    cols=['sessions_d0_7','active_days_d0_7','total_minutes_d0_7','avg_session_minutes']
    f[cols].corr().to_csv(OUT/'tables/feature_correlations.csv')
    save_json(OUT/'validation/feature_diagnostics.json',dict(session_active_day_correlation=float(f.sessions_d0_7.corr(f.active_days_d0_7)),fraction_users_multiple_sessions=float(f.sessions_d0_7.gt(f.active_days_d0_7).mean()),note='Correlated engagement predictors describe one behavior family, not independent causal effects.'))
    # Device performance at user-day grain (any crash; daily mean FPS).
    perf=s.groupby(['user_id','session_date']).agg(crash=('crash_flag','max'),fps=('fps_quality_bucket','mean')).reset_index()
    perf=perf.join(raw['users'][['register_date','device']],on='user_id')
    perf=perf.loc[(perf.session_date-perf.register_date).dt.days.between(0,7)]
    perf['period']=perf.session_date.lt(pd.Timestamp('2026-03-02')).map({True:'pre_patch1',False:'post_patch1'})
    perf.groupby(['device','period']).agg(active_user_days=('user_id','size'),crash_rate=('crash','mean'),mean_fps=('fps','mean')).to_csv(OUT/'tables/device_performance.csv')
    gate_population()
