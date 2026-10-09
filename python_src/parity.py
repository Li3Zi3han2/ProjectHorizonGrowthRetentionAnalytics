"""Hard acceptance gate: no report or full run before independent parity succeeds."""
import json
import numpy as np
import pandas as pd
from .config import OUT
from .database import save_json

def check() -> dict:
    wl=json.loads((OUT/'metrics/wolfram.json').read_text())
    py=json.loads((OUT/'metrics/python.json').read_text())
    assert set(wl)==set(py), (set(wl)-set(py),set(py)-set(wl))
    rows=[]
    for key in sorted(wl):
        w,p=float(wl[key]),float(py[key]); diff=abs(w-p);rel=diff/max(abs(w),abs(p),1e-15)
        rows.append(dict(metric=key,wolfram_value=w,python_value=p,absolute_difference=diff,relative_difference=rel,status='PASS' if diff<=1e-10 or rel<=1e-8 else 'FAIL'))
    # Every feature and label is independently derived, aligned by user_id.
    wf=pd.read_csv(OUT/'tables/wolfram_features.csv').set_index('user_id').sort_index()
    pf=pd.read_csv(OUT/'tables/python_features.csv').set_index('user_id').sort_index()
    assert wf.index.equals(pf.index),'feature identities'
    from .churn import NUMERIC
    for col in NUMERIC+['churn_30','max_feature_day']:
        delta=np.abs(wf[col].to_numpy()-pf[col].to_numpy())
        rows.append(dict(metric=f'feature/{col}/max_diff',wolfram_value=0,python_value=float(delta.max()),absolute_difference=float(delta.max()),relative_difference=float(delta.max()/max(1,np.abs(wf[col]).max())),status='PASS' if np.allclose(wf[col],pf[col],atol=1e-10,rtol=1e-8) else 'FAIL'))
    df=pd.DataFrame(rows);df.to_csv(OUT/'parity/wolfram_python_parity.csv',index=False)
    wp=pd.read_csv(OUT/'models/wolfram_predictions.csv').set_index('user_id').sort_index()
    pp=pd.read_csv(OUT/'models/python_predictions.csv').set_index('user_id').sort_index()
    assert wp.index.equals(pp.index),'model test population'
    wc=pd.read_csv(OUT/'tables/logistic_coefficients.csv').set_index('feature').coefficient
    pc=pd.read_csv(OUT/'tables/python_logistic_coefficients.csv').set_index('feature').coefficient
    stable=wc.abs().gt(.03)&pc.abs().gt(.03)
    direction=float((np.sign(wc[stable])==np.sign(pc[stable])).mean())
    rank=float(wc.abs().rank().corr(pc.abs().rank()))
    wem=json.loads((OUT/'models/wolfram_evaluation.json').read_text());pem=json.loads((OUT/'models/python_evaluation.json').read_text())
    model=[]
    def record(comparison,w,p,rule,passed): model.append(dict(comparison=comparison,wolfram_result=w,python_result=p,agreement_rule=rule,status='PASS' if passed else 'FAIL'))
    record('logistic_coefficient_direction',direction,1,'all stable |coefficient|>0.03 have identical sign',direction==1)
    record('logistic_risk_rank_spearman',rank,1,'absolute coefficient rank correlation >=0.9',rank>=.9)
    for name in ['logistic','nonlinear']:
        for metric,tolerance in [('roc_auc',.045),('pr_auc',.05),('brier',.035),('lift_at_10pct',.20)]:
            w,p=wem[name][metric],pem[name][metric]
            record(f'{name}/{metric}',w,p,f'absolute difference <={tolerance}',abs(w-p)<=tolerance)
        for runtime,em in [('wolfram',wem),('python',pem)]:
            cm=np.asarray(em[name]['confusion_matrix']);tn,fp,fn,tp=cm.ravel()
            precision=tp/max(1,tp+fp);recall=tp/max(1,tp+fn);f1=2*precision*recall/max(1e-12,precision+recall)
            valid=cm.shape==(2,2) and cm.sum()==em['test_n'] and (cm>=0).all()
            valid=valid and all(np.isfinite(em[name][k]) and abs(em[name][k]-v)<=1e-10 for k,v in [('precision',precision),('recall',recall),('f1',f1)])
            record(f'{runtime}/{name}/classification_sanity',int(cm.sum()),em['test_n'],'counts and recomputed precision/recall/F1',bool(valid))
        if name=='logistic':
            for metric in ['precision','recall','f1']:
                w,p=wem[name][metric],pem[name][metric]
                record(f'{name}/{metric}',w,p,'absolute difference <=0.02',abs(w-p)<=.02)
        k=int(np.ceil(len(wp)/10))
        wt=set(wp.sort_values(name,ascending=False).head(k).index);pt=set(pp.sort_values(name,ascending=False).head(k).index)
        overlap=len(wt&pt)/k
        minimum=.95 if name=='logistic' else .60
        record(f'{name}/top_decile_overlap',overlap,1,f'overlap >={minimum}',overlap>=minimum)
    # Derived conclusions: largest drop, device risk and leading logistic predictors.
    wfunnel=pd.read_csv(OUT/'tables/funnel.csv');pfunnel=pd.read_csv(OUT/'tables/python_funnel.csv')
    drop=lambda f:f.loc[(f.dimension=='overall')&f.stage_type.eq('core')&f.step.gt(1)].sort_values('dropoff',ascending=False).iloc[0]['name']
    record('largest_core_funnel_drop',drop(wfunnel),drop(pfunnel),'same core transition',drop(wfunnel)==drop(pfunnel))
    device=lambda m:min(['Android','PC','iOS'],key=lambda d:m[f'retention/device/{d}/d7'])
    record('highest_risk_device',device(wl),device(py),'same D7 lowest retention device',device(wl)==device(py))
    wt=set(wc.abs().nlargest(5).index);pt=set(pc.abs().nlargest(5).index)
    record('leading_churn_signals',', '.join(sorted(wt)),', '.join(sorted(pt)),'at least 4 of top5 identical',len(wt&pt)>=4)
    md=pd.DataFrame(model);md.to_csv(OUT/'parity/model_parity.csv',index=False)
    failed=int((df.status=='FAIL').sum()+(md.status=='FAIL').sum())
    content=f'# Wolfram / Python parity\n\nBoth implementations recompute from the same PostgreSQL raw facts. Python never imports Wolfram KPI results before comparison.\n\n{len(df)} descriptive / feature checks; {len(md)} model / conclusion checks; failures: {failed}.\n\n```text\n{md.to_string(index=False)}\n```\n\nFull deterministic comparison: wolfram_python_parity.csv. Stable coefficient rule excludes coefficients whose absolute value is below 0.03 in either language. Nonlinear model differences reflect LightGBM versus sklearn histogram boosting; predeclared acceptance bounds are in parity.py.\n'
    (OUT/'parity/wolfram_python_parity.md').write_text(content,encoding='utf-8')
    result=dict(descriptive_checks=len(df),model_checks=len(md),failures=failed,status='PASS' if failed==0 else 'FAIL')
    save_json(OUT/'parity/status.json',result)
    assert failed==0,content
    return result
