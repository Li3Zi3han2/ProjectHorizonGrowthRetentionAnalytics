"""Operations snapshot from raw facts, independently using pandas priority rules."""
import numpy as np
import pandas as pd
from .config import END, OUT
from .database import query

ACTIONS = {'New & Unactivated':'检查引导与首次核心循环触达','Returning Users':'个性化回流导航并开展随机实验','High-Value Users':'稳定体验与内容服务','Healthy New Users':'强化核心循环与内容匹配','At-Risk Users':'按可观测风险与成本排序触达','Highly Engaged Non-Payers':'内容推荐，避免强制付费压力','Core Engaged Users':'维持内容节奏与社交可达性'}

def calculate(raw: dict, metrics: dict) -> pd.DataFrame:
    u, s = raw['users'], raw['sessions']
    end = pd.Timestamp(END)
    recent = s.loc[s.session_date.ge(end-pd.Timedelta(days=27))]
    f = u[['register_date']].copy()
    f['last_date'] = s.groupby('user_id').session_date.max()
    f['active28'] = recent.groupby('user_id').session_date.nunique().reindex(f.index,fill_value=0)
    f['minutes28'] = recent.groupby('user_id').session_minutes.sum().reindex(f.index,fill_value=0)
    p = query('SELECT user_id,max(chapter) chapter FROM horizon.progression GROUP BY user_id').set_index('user_id')
    m = query('SELECT user_id,sum(amount_usd)::float8 spend FROM horizon.monetization GROUP BY user_id').set_index('user_id')
    f = f.join(p).join(m).fillna({'spend':0})
    ordered = s[['user_id','session_date']].drop_duplicates().sort_values(['user_id','session_date']).copy()
    ordered['gap'] = ordered.groupby('user_id').session_date.diff().dt.days
    returned = ordered.loc[ordered.gap.ge(7)&ordered.session_date.ge(end-pd.Timedelta(days=6)), 'user_id']
    f['segment'] = np.select([f.register_date.ge(end-pd.Timedelta(days=6))&f.chapter.lt(1),f.index.isin(returned),f.spend.ge(50),f.register_date.ge(end-pd.Timedelta(days=6)),f.last_date.lt(end-pd.Timedelta(days=6)),f.active28.ge(10)&f.spend.eq(0)],['New & Unactivated','Returning Users','High-Value Users','Healthy New Users','At-Risk Users','Highly Engaged Non-Payers'],default='Core Engaged Users')
    f['payer'] = f.spend.gt(0).astype(int)
    summary = f.groupby('segment').agg(n=('segment','size'),active_days28=('active28','mean'),minutes28=('minutes28','mean'),chapter=('chapter','mean'),payer_rate=('payer','mean'))
    # Retention is descriptive by current snapshot group; warn about future-informed grouping.
    mature = u.register_date.le(end-pd.Timedelta(days=30))
    d30 = s.loc[(s.session_date-s.user_id.map(u.register_date)).dt.days.eq(30),'user_id']
    f['d30_observed'] = f.index.isin(d30).astype(float)
    summary['d30_retention_mature'] = f.loc[mature].groupby('segment').d30_observed.mean()
    summary['recommended_action'] = [ACTIONS[name] for name in summary.index]
    for name, row in summary.iterrows():
        metrics[f'segment/{name}'] = int(row['n'])
    summary.to_csv(OUT / 'tables/python_segments.csv')
    return summary.reset_index()
