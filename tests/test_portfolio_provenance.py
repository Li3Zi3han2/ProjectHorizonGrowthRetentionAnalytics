"""Current-mode paragraphs, Mermaid and counts are derived from execution evidence."""
import json
from pathlib import Path
import pytest
from python_src import portfolio

@pytest.mark.parametrize('engine,dual,generator,passed,skipped',[('python',False,'Python',88,16),('wolfram',False,'Wolfram',78,26),('wolfram',True,'Wolfram',93,11),('python',False,'Wolfram',88,16)])
def test_portfolio_mode_provenance_matches_certificate(tmp_path,monkeypatch,engine,dual,generator,passed,skipped):
    out=tmp_path/'outputs';(out/'metrics').mkdir(parents=True);(out/'parity').mkdir();(out/'validation').mkdir()
    monkeypatch.setattr(portfolio,'OUT',out);monkeypatch.setattr(portfolio,'ARTIFACT_ROOT',tmp_path)
    def write(name,data):(out/name).write_text(json.dumps(data),encoding='utf8')
    (tmp_path/'run.json').write_text(json.dumps(dict(run_id='current')),encoding='utf8')
    write('dataset_manifest.json',dict(run_id='generation',generator=generator,dataset_sha256='input'))
    write('parity/status.json',dict(status='PASS' if dual else 'SKIPPED',descriptive_checks=1601,model_checks=22))
    (out/'metrics/pytest.xml').write_text(f'<testsuites><testsuite tests="{passed+skipped}" skipped="{skipped}" failures="0" errors="0"/></testsuites>')
    if dual or engine=='python':write('metrics/notebook_execution.json',dict(status='PASS'))
    if dual or engine=='wolfram':write('metrics/wolfram_selftest.json',dict(notebook_input_cells_executed=13))
    scope='dual_engine' if dual else 'python_only' if engine=='python' else 'wolfram_only'
    write('validation/certificate.json',dict(scope=scope,run_id='current',dataset_sha256='input',validation=dict(tests=passed,skipped=skipped)))
    overview,title,flow,summary=portfolio.execution_provenance(engine,dual)
    assert f'本次数据由 {generator} 生成' in overview and scope in overview
    assert f'{generator} 生成数据' in flow and '本次' in title
    assert f'通过 {passed} 项、跳过 {skipped} 项' in summary and '27 项' not in summary
    if not dual:
        assert '跨语言 parity 为 SKIPPED' in summary
        assert ('Wolfram 分析' in flow)==(engine=='wolfram')
        assert ('Python 分析' in flow)==(engine=='python')
        assert ('Python Notebook：SKIPPED' in summary)==(engine=='wolfram')
        assert ('Wolfram 自检与原生 Notebook：SKIPPED' in summary)==(engine=='python')
    else:assert 'parity PASS' in summary and 'Wolfram 分析' in flow and 'Python 分析' in flow
    # Generate the complete Markdown from public aggregate fixtures, not only a helper.
    import shutil
    root=portfolio.ROOT
    for name in ['executive_summary.json',f'models/{engine}_evaluation.json','validation/feature_diagnostics.json','metrics/generation.json','tables/funnel.csv','tables/progression_diagnosis.csv','tables/experiment_design.csv','tables/device_performance.csv','tables/retention_breakdown.csv','tables/segments.csv','tables/daily_kpis.csv']:
        destination=out/name;destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(root/'outputs'/name,destination)
    generation=json.loads((out/'metrics/generation.json').read_text(encoding='utf8'));generation['generator']=generator
    write('metrics/generation.json',generation)
    portfolio.generate_presentation(engine,dual)
    md=(tmp_path/'portfolio/Project_Horizon_Portfolio.md').read_text(encoding='utf8')
    assert overview in md and flow in md and summary in md
    assert 'Wolfram Language 负责数据生成和主分析' not in md
    assert '原完整运行通过 27 项' not in md
    write('validation/certificate.json',dict(scope=scope,run_id='other',dataset_sha256='input',validation=dict(tests=passed,skipped=skipped)))
    with pytest.raises(AssertionError):portfolio.execution_provenance(engine,dual)
