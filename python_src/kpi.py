"""Independent calendar metrics from session facts using pandas."""
import numpy as np
import pandas as pd
from .config import START, END, OUT
from .database import query

def calculate(raw: dict, metrics: dict) -> pd.DataFrame:
    u, s = raw['users'], raw['sessions']
    a = s[['user_id', 'session_date']].drop_duplicates().sort_values(['user_id', 'session_date'])
    a['previous'] = a.groupby('user_id')['session_date'].shift()
    a['register_date'] = a['user_id'].map(u['register_date'])
    a['kind'] = np.where(a['session_date'].eq(a['register_date']), 'new_active',
                         np.where((a['session_date'] - a['previous']).dt.days.ge(7), 'returned', 'retained'))
    composition = a.groupby(['session_date', 'kind']).size().unstack(fill_value=0)
    records = []
    new = u.groupby('register_date').size()
    for day in pd.date_range(START, END):
        row = dict(day=day.strftime('%Y-%m-%d'), new_users=int(new.get(day, 0)))
        for kind in ['new_active', 'retained', 'returned']:
            row[kind] = int(composition[kind].get(day, 0)) if kind in composition else 0
        row['dau'] = sum(row[k] for k in ['new_active', 'retained', 'returned'])
        for span, name in [(7, 'wau'), (30, 'mau')]:
            row[name] = int(a.loc[a['session_date'].between(day-pd.Timedelta(days=span-1), day), 'user_id'].nunique())
        for key, value in row.items():
            if key != 'day':
                metrics[f'daily/{row["day"]}/{key}'] = value
        row['dau_mau'] = row['dau'] / max(row['mau'], 1)
        records.append(row)
    payments = query('SELECT user_id,amount_usd::float8 amount FROM horizon.monetization')
    metrics.update(users=len(u), payers=int(payments.user_id.nunique()), revenue=float(payments.amount.sum()))
    metrics.update(payer_conversion=metrics['payers']/len(u), arpu=metrics['revenue']/len(u), arppu=metrics['revenue']/max(1, metrics['payers']))
    frame = pd.DataFrame(records)
    frame.to_csv(OUT / 'tables/python_daily_kpis.csv', index=False)
    return frame
