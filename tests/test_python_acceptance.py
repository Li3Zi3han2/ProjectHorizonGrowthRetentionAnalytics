"""Independent current Python algorithms, SQL comparators and report lineage."""
import json
import math
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss
from python_src.config import OUT, ROOT, ARTIFACT_ROOT
from python_src.database import query

def test_python_predictions_reproduce_evaluation():
    p=pd.read_csv(OUT/'models/python_predictions.csv');e=json.loads((OUT/'models/python_evaluation.json').read_text(encoding='utf8'))
    assert len(p)==e['test_n'] and p.user_id.is_unique
    for model in ['logistic','nonlinear']:
        y=p.churn_30;score=p[model];assert score.between(0,1).all()
        for name,fn in [('roc_auc',roc_auc_score),('pr_auc',average_precision_score),('brier',brier_score_loss)]:assert abs(fn(y,score)-e[model][name])<=1e-10

def test_python_retention_from_independent_sql():
    actual=query((ROOT/'sql/03_retention.sql').read_text(encoding='utf8')).sort_values('d');p=pd.read_csv(OUT/'tables/python_retention_curve.csv').sort_values('d')
    np.testing.assert_array_equal(actual.eligible,p.eligible);np.testing.assert_array_equal(actual.retained,p.retained)
    np.testing.assert_allclose(actual.rate,p.rate,rtol=1e-8,atol=1e-10)

def test_python_gate_eligibility_from_independent_sql():
    actual=query((ROOT/'sql/09_gate_experiment.sql').read_text(encoding='utf8')).set_index('user_id').sort_index();p=pd.read_csv(OUT/'tables/python_gate_eligibility.csv').set_index('user_id').sort_index()
    p.first_gate_date=pd.to_datetime(p.first_gate_date);actual.first_gate_date=pd.to_datetime(actual.first_gate_date)
    pd.testing.assert_frame_equal(actual,p,check_dtype=False)

def test_python_experiment_candidates_and_power():
    from statsmodels.stats.power import NormalIndPower
    from statsmodels.stats.proportion import proportion_effectsize
    plans=json.loads((OUT/'metrics/power_analysis.json').read_text(encoding='utf8'))['experiments']
    runtime=json.loads((OUT/'executive_summary.json').read_text(encoding='utf8'))['analysis_engine']
    p=pd.read_csv(OUT/f'models/{runtime}_predictions.csv').sort_values('logistic',ascending=False)
    candidates=p.head(math.ceil(len(p)/10));b=plans[1]
    count=query("SELECT count(DISTINCT s.user_id) FROM horizon.sessions s JOIN horizon.users u USING(user_id) WHERE session_date=register_date+30 AND s.user_id=ANY(%s)",(candidates.user_id.astype(int).tolist(),)).iloc[0,0]
    assert b['eligible_n']==len(candidates) and abs(b['baseline']-count/len(candidates))<=1e-10
    n=math.ceil(NormalIndPower().solve_power(abs(proportion_effectsize(b['baseline'],min(.999,b['baseline']+.03))),power=.8,alpha=.05,ratio=1));assert n==b['per_arm']

def test_python_mode_summary_and_portfolio_are_current():
    s=json.loads((OUT/'executive_summary.json').read_text(encoding='utf8'));m=json.loads((OUT/'metrics/python.json').read_text(encoding='utf8'))
    for d in [1,7,30]:assert s[f'overall_d{d}']==m[f'retention/d{d}']
    md=(ARTIFACT_ROOT/'portfolio/Project_Horizon_Portfolio.md').read_text(encoding='utf8')
    assert f"{s['overall_d7']:.2%}" in md and '实验尚未执行' in md
    assert s['dataset_sha256']==json.loads((OUT/'dataset_manifest.json').read_text(encoding='utf8'))['dataset_sha256']
    if s['analysis_engine']=='python':
        assert '本次 Python 独立分析的时间测试结果' in md
        assert '下表为 Wolfram 主实现' not in md
    assert '只高 -' not in md
