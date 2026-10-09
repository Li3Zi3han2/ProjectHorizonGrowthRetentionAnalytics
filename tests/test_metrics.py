"""Lifecycle algebra, censoring boundaries and independent raw labels."""
import json
import os
import pandas as pd
from python_src.config import OUT,ROOT
from python_src.database import query

def test_retention_bounds_and_cohort_maturity():
    f=pd.read_csv(OUT/'tables/retention_curve.csv')
    assert f.rate.between(0,1).all()
    assert f.eligible.is_monotonic_decreasing
    for d in [1,7,30]:
        n=query("SELECT count(*) FROM horizon.users WHERE register_date+%s<=DATE '2026-06-29'",(d,)).iloc[0,0]
        assert n==f.loc[f.d.eq(d),'eligible'].iloc[0]

def test_lifecycle_identity():
    f=pd.read_csv(OUT/'tables/daily_kpis.csv')
    assert (f.dau==f.new_active+f.retained+f.returned).all()
    assert (f.dau<=f.wau).all() and (f.wau<=f.mau).all()
    assert f.new_users.sum()==query('SELECT count(*) FROM horizon.users').iloc[0,0]

def test_sequential_funnel_and_segments():
    f=pd.read_csv(OUT/'tables/funnel.csv')
    for _,g in f.loc[f.stage_type.eq('core')].groupby(['dimension','category']):assert g.n.is_monotonic_decreasing
    segments=pd.read_csv(OUT/'tables/segments.csv')
    assert segments.n.sum()==query('SELECT count(*) FROM horizon.users').iloc[0,0]
    assert segments.segment.nunique()==7

def test_labels_from_separate_sql():
    labels=query((ROOT/'sql/06_churn_labels.sql').read_text()).set_index('user_id').sort_index()
    f=pd.read_csv(OUT/'tables/python_features.csv').set_index('user_id').sort_index()
    assert labels.churn_30.equals(f.churn_30)

def test_summary_matches_primary():
    runtime='python' if os.environ.get('HORIZON_ANALYSIS_MODE')=='python' else 'wolfram'
    s=json.loads((OUT/'executive_summary.json').read_text(encoding='utf-8'));m=json.loads((OUT/f'metrics/{runtime}.json').read_text(encoding='utf-8'))
    for d in [1,7,30]:assert s[f'overall_d{d}']==m[f'retention/d{d}']

def test_experiment_primary_and_independent_power():
    w=json.loads((OUT/'metrics/experiments_wolfram.json').read_text(encoding='utf-8'))
    p=json.loads((OUT/'metrics/power_analysis.json').read_text(encoding='utf-8'))
    b=next(e for e in p['experiments'] if e['experiment']=='B')
    assert w['B']['primary']==b['primary']=='Exact-day D30 retention'
    assert abs(w['B']['baseline']-b['baseline'])<=1e-10
    assert abs(w['B']['per_arm']-b['per_arm'])/b['per_arm']<.01
    c=next(e for e in p['experiments'] if e['experiment']=='C')
    assert w['C']['per_arm']==c['per_arm']
    assert abs(w['C']['baseline']-c['baseline'])<=1e-10
