"""Full-output acceptance gates and coherent model business conclusions."""
import json
import pandas as pd
from python_src.config import OUT, ROOT

def test_deterministic_and_model_parity():
    for name in ['wolfram_python_parity.csv','model_parity.csv']:
        frame=pd.read_csv(OUT/'parity'/name)
        assert frame.status.eq('PASS').all()
    assert json.loads((OUT/'parity/status.json').read_text())['status']=='PASS'

def test_model_evaluation_artifacts():
    for name in ['wolfram_evaluation.json','python_evaluation.json']:
        models=json.loads((OUT/'models'/name).read_text())
        for model in ['logistic','nonlinear']:
            for metric in ['roc_auc','pr_auc','brier','precision','recall','f1','capture_at_10pct']:
                assert 0<=models[model][metric]<=1
            assert len(models[model]['confusion_matrix'])==2

def test_figures_and_portfolio():
    from tools.release_checks import check_links
    links=check_links(ROOT)
    assert links['portfolio_data_figures']==11 and links['portfolio_qr_images']==1
    assert (ROOT/'portfolio/Project_Horizon_Portfolio.md').stat().st_size>5000
    assert (OUT/'executive_summary.json').exists()
