"""Parity-gated executive summary, Markdown portfolio and notebooks."""
import json
from pathlib import Path
import pandas as pd
from .config import ROOT, OUT, CONFIG, ARTIFACT_ROOT
from .database import save_json
from .experiments import plan

DISCLOSURE='Project Horizon is a fictional game. All user-level and event-level data in this repository are synthetically generated for portfolio demonstration purposes. No proprietary, confidential, or real player data are used.'

def read_json(path: str) -> dict:
    return json.loads((OUT/path).read_text(encoding='utf-8'))

def generate(engine='wolfram', dual=True) -> None:
    parity=read_json('parity/status.json')
    if dual: assert parity['status']=='PASS'
    else: assert parity['status']=='SKIPPED'
    m=read_json(f'metrics/{engine}.json');em=read_json(f'models/{engine}_evaluation.json');g=read_json('metrics/generation.json')
    f=pd.read_csv(OUT/'tables/funnel.csv');core=f.loc[f.dimension.eq('overall')&f.stage_type.eq('core')].sort_values('step');optional=f.loc[f.dimension.eq('overall')&f.stage_type.eq('optional')]
    largest=core.loc[core.step.gt(1)].sort_values('dropoff',ascending=False).iloc[0]
    wall=pd.read_csv(OUT/'tables/progression_diagnosis.csv').set_index('level').loc[12]
    ret=pd.read_csv(OUT/'tables/retention_breakdown.csv');device=ret.loc[ret.dimension.eq('device')&ret.d.eq(7)].sort_values('rate')
    coef=pd.read_csv(OUT/'tables/logistic_coefficients.csv').assign(magnitude=lambda x:x.coefficient.abs()).sort_values('magnitude',ascending=False)
    top=coef.loc[~coef.feature.eq('registration_week')].head(5).feature.tolist()
    families={'sessions_d0_7':'早期活跃强度','active_days_d0_7':'早期活跃强度','total_minutes_d0_7':'早期活跃强度','avg_session_minutes':'早期活跃强度','chapter_reached_d7':'主线进度','tutorial_completed':'核心循环触达','core_loop_unlocked':'核心循环触达','boss_attempts_d0_7':'关卡尝试与摩擦','boss_failure_rate_d0_7':'关卡尝试与摩擦'}
    delta=em['nonlinear']['roc_auc']-em['logistic']['roc_auc']
    narrative=('非线性模型没有产生实质 discrimination gain；当前瓶颈更可能是可观测信息。Logistic 的解释性与较低部署成本适合作为运营 ranking baseline。' if delta<.01 else '非线性模型具有可见 discrimination gain；是否采用仍需结合校准、成本与前瞻验证。')
    s=dict(users=int(m['users']),simulation_days=CONFIG['simulation_days'],seed=CONFIG['seed'],overall_d1=m['retention/d1'],overall_d7=m['retention/d7'],overall_d30=m['retention/d30'],activation_rate=m['activation_rate'],activation_definition='D7 core-loop unlock: D0-D7 unlock among mature D7 registrations',largest_core_funnel_drop=largest['name'],largest_core_funnel_drop_fraction=float(largest.dropoff),largest_optional_adoption_drop=optional.sort_values('dropoff',ascending=False).iloc[0]['name'],highest_risk_device=device.iloc[0].category,device_d7_gap=float(device.iloc[-1].rate-device.iloc[0].rate),chapter3_completion_given_chapter2=float(core.loc[core.name.eq('chapter_3'),'conversion'].iloc[0]),chapter3_gate_level=12,chapter3_gate_failure_rate=float(wall.failure_rate),top_churn_signals=top,churn_signal_families=list(dict.fromkeys(families.get(k,k) for k in top)),model_auc=em['logistic']['roc_auc'],model_pr_auc=em['logistic']['pr_auc'],model_brier=em['logistic']['brier'],lift_at_10pct=em['logistic']['lift_at_10pct'],capture_at_10pct=em['logistic']['capture_at_10pct'],nonlinear_auc=em['nonlinear']['roc_auc'],nonlinear_auc_gain=delta,model_comparison_narrative=narrative,reactivation_eligible=int(m['reactivation/eligible']),reactivation_count=int(m['reactivation/returned']),reactivation_rate=m['return_rate'],post_return_active_days=m['reactivation/post_return_days7'],payer_conversion=m['payer_conversion'],arpu=m['arpu'],key_recommendations=['首次 Level 12 尝试时随机验证关卡优化','按设备市场版本分层随机验证性能改善','D7 top10% 保留对照验证扶持；回流用户随机比较导航'],parity=parity,run_mode='full' if m['users']==200000 else 'fast/debug',portfolio_pages=11,disclosure=DISCLOSURE)
    save_json(OUT/'executive_summary.json',s)
    s['analysis_engine']=engine;s['dataset_sha256']=read_json('dataset_manifest.json')['dataset_sha256'] if (OUT/'dataset_manifest.json').exists() else None
    save_json(OUT/'executive_summary.json',s)
    if engine=='wolfram' and not dual:
        assert (OUT/'tables/experiment_design.csv').exists(), 'Wolfram-only requires native experiment plans'
    else: plan(s,engine)
    from .portfolio import generate_presentation
    generate_presentation(engine,dual)
    write_notebook(engine,dual)

def write_notebook(engine='wolfram',dual=True) -> None:
    import nbformat as nbf
    nb=nbf.v4.new_notebook();cells=[nbf.v4.new_markdown_cell('# Project Horizon\n\n'+DISCLOSURE),nbf.v4.new_code_cell("from pathlib import Path\nimport json, pandas as pd, sys\nfrom IPython.display import display, Image\nroot=Path.cwd()\nif not (root/'outputs').exists(): root=root.parent\nsys.path.insert(0,str(root))\nfrom python_src.database import query\ns=json.loads((root/'outputs/executive_summary.json').read_text(encoding='utf8'))\nassert query('SELECT count(*) FROM horizon.users').iloc[0,0]==s['users']\nassert s['parity']['status']=='PASS'\ndisplay(s)")]
    for title,file in [('Mature retention','retention_curve.csv'),('Core funnel','core_funnel.csv'),('Optional adoption: Chapter3 denominator','optional_adoption.csv'),('Level / gate diagnosis','progression_diagnosis.csv'),('Observable multi-session features','python_features.csv'),('Correlated signal families','feature_correlations.csv'),('Logistic interpretation','python_logistic_coefficients.csv'),('Segments','python_segments.csv'),('Gate experiment & power','experiment_design.csv')]:
        cells += [nbf.v4.new_markdown_cell('## '+title),nbf.v4.new_code_cell(f"display(pd.read_csv(root/'outputs/tables/{file}').head(12))")]
    cells += [nbf.v4.new_markdown_cell('## Corrected evaluation and session semantics\nD7 core-loop unlock uses D0-D7 events; distinct from exact D7 retention. Threshold0.5 is diagnostic, ranking respects the budget.'),nbf.v4.new_code_cell("f=pd.read_csv(root/'outputs/tables/python_features.csv')\nassert (f.sessions_d0_7>=f.active_days_d0_7).all()\ndisplay(f[['sessions_d0_7','active_days_d0_7']].describe())\nfor runtime in ['wolfram','python']:\n    em=json.loads((root/f'outputs/models/{runtime}_evaluation.json').read_text())\n    assert sum(map(sum,em['logistic']['confusion_matrix']))==em['test_n']\n    display(em)\ndisplay(Image(filename=str(root/'outputs/figures/python/14_risk_decile_lift.png')))")]
    for cell in cells:
        if cell.cell_type=='code':
            cell.source=cell.source.replace("root=Path.cwd()\nif not (root/'outputs').exists(): root=root.parent", "from python_src.config import OUT, ARTIFACT_ROOT\nroot=ARTIFACT_ROOT")
            cell.source=cell.source.replace("root/'outputs/", "OUT/'").replace("root/f'outputs/", "OUT/f'")
            if not dual:
                cell.source=cell.source.replace("s['parity']['status']=='PASS'", "s['parity']['status']=='SKIPPED'")
                cell.source=cell.source.replace("['wolfram','python']",repr([engine]))
    nb.cells=cells;nb.metadata['kernelspec']=dict(display_name='Python3',language='python',name='python3')
    (ARTIFACT_ROOT/'notebooks').mkdir(parents=True,exist_ok=True)
    for name in ['python_analysis_walkthrough.ipynb','analysis_walkthrough.ipynb']:nbf.write(nb,ARTIFACT_ROOT/'notebooks'/name)
