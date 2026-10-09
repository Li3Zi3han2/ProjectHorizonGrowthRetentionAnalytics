"""Current-run artifact and numerical requirements, independent of historical PASS."""
import json
import re
import os
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
from .config import OUT, ARTIFACT_ROOT
from .database import query

def verify(engine):
    runtime='python' if engine=='python' else 'wolfram'
    m=json.loads((OUT/f'metrics/{runtime}.json').read_text(encoding='utf8'));s=json.loads((OUT/'executive_summary.json').read_text(encoding='utf8'))
    e=json.loads((OUT/f'models/{runtime}_evaluation.json').read_text(encoding='utf8'));parity=json.loads((OUT/'parity/status.json').read_text(encoding='utf8'))
    assert parity['status']==('PASS' if engine=='dual' else 'SKIPPED')
    users=int(query('SELECT count(*) FROM horizon.users').iloc[0,0]);assert users==s['users']==m['users']
    for d in [1,7,30]:assert abs(s[f'overall_d{d}']-m[f'retention/d{d}'])<=1e-10
    for name in ['daily_kpis','retention_curve','retention_breakdown','weekly_retention','funnel','core_funnel','optional_adoption','progression_diagnosis','segments','device_performance','feature_correlations','experiment_design','risk_decile_lift']:assert (OUT/f'tables/{name}.csv').is_file(),name
    for model in ['logistic','nonlinear']:
        cm=np.array(e[model]['confusion_matrix']);assert cm.shape==(2,2) and (cm>=0).all() and cm.sum()==e['test_n']
        for key in ['roc_auc','pr_auc','brier','precision','recall','f1','capture_at_10pct']:assert 0<=e[model][key]<=1
    md=ARTIFACT_ROOT/'portfolio/Project_Horizon_Portfolio.md';text=md.read_text(encoding='utf8')
    assert len(re.findall(r'^## \d+\.',text,re.M))==11
    for target in re.findall(r'!\[[^\]]*\]\(([^)]+)\)',text):assert (md.parent/target).is_file()
    for key in ['overall_d1','overall_d7','overall_d30','payer_conversion','chapter3_gate_failure_rate','reactivation_rate']:assert f'{s[key]:.2%}' in text
    for model in ['logistic','nonlinear']:
        for key in ['roc_auc','pr_auc','brier']:assert f'{e[model][key]:.4f}' in text
    pdf_pages=None
    manual=os.environ.get('HORIZON_PDF_MODE')=='manual'
    if manual:
        request=json.loads((OUT/'validation/pdf_render_request.json').read_text(encoding='utf8'))
        import hashlib
        assert request['status']=='PENDING_USER_RENDER' and request['markdown_sha256']==hashlib.sha256(md.read_bytes()).hexdigest()
        assert not md.with_suffix('.pdf').exists()
    else:
        from pypdf import PdfReader
        reader=PdfReader(md.with_suffix('.pdf'));pdf_text='\n'.join(page.extract_text() for page in reader.pages)
        for key in ['overall_d1','overall_d7','overall_d30']:assert f'{s[key]:.2%}' in pdf_text
        pdf_pages=len(reader.pages)
    from PIL import Image
    figures=list((OUT/'figures/python').glob('*.png'));assert len(figures)>=(17 if engine=='dual' else 18)
    native=list((OUT/'figures/wolfram').glob('*.png'))
    if engine!='python':assert len(native)>=19
    for path in figures+native:
        with Image.open(path) as im:im.verify()
    if engine=='python':assert not [p for p in OUT.rglob('*wolfram*') if p.is_file()], 'Python run contains stale/foreign Wolfram outputs'
    if engine=='wolfram':
        assert not (OUT/'metrics/python.json').exists() and not (OUT/'models/python_evaluation.json').exists(), 'Wolfram-only contains Python analysis artifacts'
    tests=ET.parse(OUT/'metrics/pytest.xml').getroot().find('testsuite')
    assert tests is not None and int(tests.attrib['failures'])==int(tests.attrib['errors'])==0
    passed=int(tests.attrib['tests'])-int(tests.attrib['skipped']);assert passed>0
    assert f'本次 pytest 通过 {passed} 项、跳过 {tests.attrib["skipped"]} 项。' in text
    return dict(status='PASS',scope=engine,tests=passed,skipped=int(tests.attrib['skipped']),figures=len(figures),wolfram_figures=len(native),pdf_pages=pdf_pages,input_fingerprint=s['dataset_sha256'],pdf_numeric_content='PENDING_USER_RENDER' if manual else 'PASS')
