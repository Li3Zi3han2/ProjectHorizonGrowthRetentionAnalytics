"""Exact-day retention with horizon-specific censoring and Wilson intervals."""
import numpy as np
import pandas as pd
from .config import START, END, OUT

def wilson(k: int, n: int) -> tuple[float, float]:
    z = 1.959963984540054
    p = k / n
    center = (p + z*z/(2*n))/(1+z*z/n)
    width = z*np.sqrt(p*(1-p)/n + z*z/(4*n*n))/(1+z*z/n)
    return center-width, center+width

def calculate(raw: dict, metrics: dict) -> pd.DataFrame:
    users = raw['users'].copy()
    a = raw['sessions'][['user_id', 'session_date']].drop_duplicates()
    a['relative_day'] = (a['session_date'] - a['user_id'].map(users.register_date)).dt.days
    users['patch'] = np.where(users.register_date < pd.Timestamp(START)+pd.Timedelta(days=60), 'pre_patch1',
                              np.where(users.register_date < pd.Timestamp(START)+pd.Timedelta(days=120), 'post_patch1', 'post_patch2'))
    users['channel'] = users['acquisition_channel']
    records, breakdown = [], []
    for d in range(31):
        mature = users.loc[users.register_date.le(pd.Timestamp(END)-pd.Timedelta(days=d))]
        retained = set(a.loc[a.relative_day.eq(d), 'user_id'])
        k, n = int(mature.index.isin(retained).sum()), len(mature)
        lo, hi = wilson(k, n)
        records.append(dict(d=d, eligible=n, retained=k, rate=k/n, ci_low=lo, ci_high=hi))
        metrics[f'retention/d{d}'] = k/n
        metrics[f'retention/eligible/d{d}'] = n
        if d in (1, 7, 30):
            for dimension in ['market', 'channel', 'device', 'patch']:
                for category, group in mature.groupby(dimension):
                    kk, nn = int(group.index.isin(retained).sum()), len(group)
                    lo, hi = wilson(kk, nn)
                    breakdown.append(dict(dimension=dimension, category=category, d=d, eligible=nn, retained=kk, rate=kk/nn, ci_low=lo, ci_high=hi))
                    metrics[f'retention/{dimension}/{category}/d{d}'] = kk/nn
                    metrics[f'population/{dimension}/{category}/d{d}'] = nn
    pd.DataFrame(breakdown).to_csv(OUT / 'tables/python_retention_breakdown.csv', index=False)
    pd.DataFrame(records).to_csv(OUT / 'tables/python_retention_curve.csv', index=False)
    return pd.DataFrame(records)
