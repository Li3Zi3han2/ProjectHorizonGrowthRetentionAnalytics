"""Presentation and distribution acceptance against actual release inputs."""
import zipfile
import pytest
from tools.release_checks import collect_files, is_banned, check_notebooks, scan_tree
from python_src.config import ROOT

def test_release_whitelist_excludes_user_level_and_local_files():
    files=collect_files(ROOT)
    assert len(files)==len(set(files))
    assert all(not is_banned(name) for name in files)
    assert "sql/09_gate_experiment.sql" in files
    assert "tools/build_github_release.ps1" in files
    assert "notebooks/analysis_walkthrough.ipynb" not in files
    assert "outputs/figures/python/14_risk_decile_lift.png" in files
    assert not any(x.startswith("outputs/report/") for x in files)

def test_notebook_evidence_matches_current_artifacts():
    assert check_notebooks(ROOT)["python_executed_cells"]==11

def test_zip_contents_match_the_validated_release_tree():
    path=ROOT/"release/ProjectHorizonGrowthRetentionAnalytics.zip"
    if not path.exists():
        # Source reproduction does not require an existing packaged distribution.
        return
    files=collect_files(ROOT)
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        assert z.namelist()==["Project-Horizon/"+name for name in files]
        for name in files:
            assert z.read("Project-Horizon/"+name)==(ROOT/"release/github/Project-Horizon"/name).read_bytes()

def test_real_release_extracted_source_matches_current_certificates(tmp_path):
    from tools.release_checks import check_source_provenance
    from python_src.provenance import source_fingerprint
    archive=ROOT/'release/ProjectHorizonGrowthRetentionAnalytics.zip'
    if not archive.exists():pytest.skip('No packaged distribution in source reproduction')
    with zipfile.ZipFile(archive) as z:z.extractall(tmp_path)
    extracted=tmp_path/'Project-Horizon'
    checks=check_source_provenance(extracted)
    assert checks['code_sha256']==source_fingerprint(ROOT)==source_fingerprint(extracted)

def test_release_scanner_rejects_literal_credentials(tmp_path):
    candidate=tmp_path/"config.py"
    candidate.write_text("password=os.getenv('HORIZON_DB_PASSWORD', '')",encoding="utf8")
    assert scan_tree(tmp_path)["secrets"]=="PASS"
    candidate.write_text("password=unexpected_test_credential",encoding="utf8")
    with pytest.raises(AssertionError,match="Credential assignment"):
        scan_tree(tmp_path)

def test_release_scanner_rejects_raw_exports(tmp_path):
    (tmp_path/"d7_risk_scores.csv").write_text("user_id,score",encoding="utf8")
    with pytest.raises(AssertionError,match="Banned release file"):
        scan_tree(tmp_path)


def test_release_rejects_pdf_without_current_numbers(tmp_path):
    import shutil
    from pypdf import PdfWriter
    from tools.release_checks import check_pdf_numeric_content
    (tmp_path/'portfolio').mkdir();(tmp_path/'outputs/models').mkdir(parents=True)
    shutil.copy2(ROOT/'outputs/executive_summary.json',tmp_path/'outputs/executive_summary.json')
    shutil.copy2(ROOT/'outputs/models/wolfram_evaluation.json',tmp_path/'outputs/models/wolfram_evaluation.json')
    pdf=PdfWriter();pdf.add_blank_page(width=595,height=842)
    pdf.write(tmp_path/'portfolio/Project_Horizon_Portfolio.pdf')
    with pytest.raises(AssertionError,match='Stale PDF'):check_pdf_numeric_content(tmp_path)
