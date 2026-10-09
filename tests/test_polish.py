"""Regression tests for semantic defects and actual mechanism diagnostics."""
import json
import os
import numpy as np
import pandas as pd
from python_src.config import OUT, ROOT
from python_src.database import query

def read(path):return json.loads((OUT/path).read_text(encoding='utf8'))

def test_classification_counts_and_metrics():
    for runtime in (['python'] if os.environ.get('HORIZON_ANALYSIS_MODE')=='python' else ['wolfram','python']):
        e=read(f'models/{runtime}_evaluation.json')
        for name in ['logistic','nonlinear']:
            cm=np.array(e[name]['confusion_matrix']);tn,fp,fn,tp=cm.ravel()
            assert cm.shape==(2,2) and (cm>=0).all() and cm.sum()==e['test_n']
            p=tp/max(1,tp+fp);r=tp/max(1,tp+fn);f=2*p*r/max(1e-12,p+r)
            for metric,v in [('precision',p),('recall',r),('f1',f)]:assert np.isfinite(e[name][metric]) and abs(e[name][metric]-v)<1e-10

def test_multi_session_observation_semantics():
    f=pd.read_csv(OUT/'tables/python_features.csv')
    assert f.sessions_d0_7.ge(f.active_days_d0_7).all()
    assert f.sessions_d0_7.gt(f.active_days_d0_7).mean()>=.15
    assert f.sessions_d0_7.corr(f.active_days_d0_7)<.995
    assert query('SELECT count(*) FROM (SELECT user_id,event_date FROM horizon.progression GROUP BY 1,2 HAVING count(*)>1) x').iloc[0,0]==0
    assert query('SELECT count(*) FROM (SELECT user_id,session_date,count(*) n FROM horizon.sessions GROUP BY 1,2 HAVING count(*)>3) x').iloc[0,0]==0

def test_loose_synthetic_guardrails():
    v=read('validation/synthetic_calibration.json')['values']
    for k,lo,hi in [('d1_retention',.2,.6),('d7_retention',.07,.4),('d30_retention',.025,.25),('payer_conversion',.005,.15),('chapter2_to_chapter3_conversion',.4,.85),('level12_boss_failure_rate',.35,.9),('device_max_gap',.008,.12)]:assert lo<=v[k]<=hi,(k,v[k])
    assert v['android_d7_retention']<v['pc_d7_retention']
    assert 0<v['reactivation_rate']<.5

def test_gate_diagnosis_matches_summary():
    g=pd.read_csv(OUT/'tables/progression_diagnosis.csv');s=read('executive_summary.json')
    assert 'level' in g and 'chapter' not in g
    r=g.set_index('level').loc[12]
    assert r.attempts>0 and 0<=r.failure_rate<=1
    assert abs(r.failure_rate-r.failures/r.attempts)<1e-10
    assert abs(s['chapter3_gate_failure_rate']-r.failure_rate)<1e-10

def test_optional_adoption_does_not_enter_core_headline():
    f=pd.read_csv(OUT/'tables/funnel.csv');s=read('executive_summary.json')
    g=f.loc[f.dimension.eq('overall')];core=g.loc[g.stage_type.eq('core')]
    assert s['largest_core_funnel_drop']==core.loc[core.step.gt(1)].sort_values('dropoff',ascending=False).iloc[0]['name']
    assert s['largest_core_funnel_drop'] not in ['activity_enter','social_interaction']
    assert g.loc[g.stage_type.eq('optional'),'denominator'].eq(core.loc[core.name.eq('chapter_3'),'n'].iloc[0]).all()

def test_gate_experiment_eligibility_and_independent_power():
    w=pd.read_csv(OUT/'tables/gate_eligibility.csv').set_index('user_id').sort_index()
    p=pd.read_csv(OUT/'tables/python_gate_eligibility.csv').set_index('user_id').sort_index()
    pd.testing.assert_frame_equal(w,p)
    raw=query((ROOT/'sql/09_gate_experiment.sql').read_text()).set_index('user_id').sort_index()
    pd.testing.assert_frame_equal(raw,w,check_dtype=False)
    wa=read('metrics/experiments_wolfram.json')['A'];pa=read('metrics/power_analysis.json')['experiments'][0]
    assert wa['eligible_n']==pa['eligible_n']==len(w)
    assert wa['completed_n']==pa['completed_n']==w.completed_within3.sum()
    assert abs(wa['baseline']-w.completed_within3.mean())<1e-10
    assert abs(wa['baseline']-pa['baseline'])<1e-10
    assert wa['primary']==pa['primary']
    assert abs(wa['per_arm']-pa['per_arm'])/pa['per_arm']<.01

def test_markdown_report_consistency():
    from tools.release_checks import check_numeric_content, check_links
    check_numeric_content(ROOT)
    result=check_links(ROOT)
    assert result['portfolio_images']==12
    assert result['portfolio_data_figures']==11 and result['portfolio_qr_images']==1
    text=(ROOT/'portfolio/Project_Horizon_Portfolio.md').read_text(encoding='utf8')
    assert '控制其他特征后的条件预测关联' in text
    assert '四个日历日期' in text and '实验尚未执行' in text
    assert 'chapter_2' not in text and 'sessions_d0_7' not in text

def test_readme_links_and_current_model_narrative():
    import re
    text=(ROOT/'README.md').read_text(encoding='utf8');s=read('executive_summary.json')
    for target in re.findall(r'\]\(([^)]+)\)',text):assert (ROOT/target).exists(),target
    assert '第二章前后两个相邻步骤的损失接近' in text
    assert '观察性差异、模型系数和版本前后变化均不等于因果效应' in text
    assert '实际区分能力几乎没有变化' in text if s['nonlinear_auc_gain']<.01 else '非线性' in text
    assert ('没有产生实质' in s['model_comparison_narrative'])==(s['nonlinear_auc_gain']<.01)

def test_readme_generator_keeps_chinese_dynamic_results_and_setup(tmp_path, monkeypatch):
    from python_src import portfolio
    current=(ROOT/'README.md').read_text(encoding='utf8')
    (tmp_path/'README.md').write_text(current,encoding='utf8')
    monkeypatch.setattr(portfolio,'ROOT',tmp_path)
    runtime='python' if os.environ.get('HORIZON_ANALYSIS_MODE')=='python' else 'wolfram'
    s=read('executive_summary.json');e=read(f'models/{runtime}_evaluation.json')
    g=read('metrics/generation.json');fd=read('validation/feature_diagnostics.json')
    ex=pd.read_csv(OUT/'tables/experiment_design.csv').set_index('experiment')
    core=pd.read_csv(OUT/'tables/funnel.csv')
    core=core.loc[core.dimension.eq('overall') & core.stage_type.eq('core')].set_index('name')
    setup=current.split('## 项目结构',1)[1]
    for d1 in [.1234, .2345]:
        portfolio.write_readme(s,e,g,ex,d1,core.loc['chapter_3','dropoff'],fd,s['nonlinear_auc_gain'])
        text=(tmp_path/'README.md').read_text(encoding='utf8')
        assert '第二章前后两个相邻步骤的损失接近' in text
        assert '观察性差异、模型系数和版本前后变化均不等于因果效应' in text
        assert f'{d1:.2%}' in text and f"{s['overall_d7']:.2%}" in text
        assert text.split('## 项目结构',1)[1]==setup
        assert 'Growth & Retention Analytics' not in text
        assert '-PythonOnly' in text and '-WolframOnly' in text
