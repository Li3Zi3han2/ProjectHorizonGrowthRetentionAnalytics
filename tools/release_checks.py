"""Portable release checks using standard-library readers; no database mutations."""
import csv
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from python_src.provenance import ALGORITHM, source_manifest

ROOT_FILES = [
    "README.md","PROJECT_SPEC.md","DATA_DICTIONARY.md","LIMITATIONS.md",
    "requirements.txt","requirements-lock.txt","pyproject.toml",".env.example",
    ".gitignore",".gitattributes","run_all.ps1","run_all.sh",
]
TABLES = [
    "cohort_maturity.csv","core_funnel.csv","daily_kpis.csv","data_quality_summary.csv",
    "device_performance.csv","experiment_design.csv","feature_correlations.csv",
    "funnel_early_behavior.csv","funnel.csv","logistic_coefficients.csv",
    "optional_adoption.csv","permutation_importance.csv","progression_diagnosis.csv",
    "python_daily_kpis.csv","python_data_quality.csv","python_funnel.csv",
    "python_logistic_coefficients.csv","python_retention_breakdown.csv",
    "python_retention_curve.csv","python_segments.csv","reactivation_device.csv",
    "reactivation_profile.csv","retention_breakdown.csv","retention_curve.csv",
    "risk_decile_lift.csv","segments.csv","weekly_retention.csv","wolfram_reactivation_profile.csv",
]
METRICS = [
    "environment.json","experiments_wolfram.json","generation.json",
    "notebook_execution.json","power_analysis.json","pytest.xml","python.json",
    "python_reactivation.json","reactivation.json","wolfram_environment.json",
    "wolfram_selftest.json","wolfram.json",
]
VALIDATIONS = [
    "synthetic_calibration.json","synthetic_calibration.csv","feature_diagnostics.json",
    "final_release.json","final_pytest.xml",
]
HISTORICAL = [
    "certificate.json","generation.json","pytest.xml","status.json",
    "wolfram_python_parity.md","wolfram_selftest.json","notebook_execution.json",
    "synthetic_calibration.json","synthetic_calibration.csv","feature_diagnostics.json",
]
PORTFOLIO = "portfolio/Project_Horizon_Portfolio.md"
PORTFOLIO_PDF = "portfolio/Project_Horizon_Portfolio.pdf"
TEXT_EXT = {".md",".py",".ps1",".sh",".wl",".wls",".nb",".json",".ipynb",".csv",".txt",".toml",".sql",".yaml",".xml",".mjs"}

def load(root, name):
    return json.loads((root/name).read_text(encoding="utf-8"))

def table(root, name):
    with (root/"outputs/tables"/name).open(encoding="utf-8",newline="") as f:
        return list(csv.DictReader(f))

def is_banned(name):
    p=Path(name)
    components=set(p.parts)
    if components & {".git",".env",".venv",".local",".pytest_cache","__pycache__","tmp",".tmp.driveupload","staging"}:
        return True
    if p.name.upper().startswith("CODEX") or p.suffix.lower() in {".zip",".pyc",".joblib",".wxf",".dump",".bak",".sql.gz"}:
        return True
    return bool(re.search(r"(features|risk[_-]?scores|predictions|gate_eligibility)\.csv$",p.name,re.I))

def check_links(root):
    counts={"portfolio_images":0,"portfolio_data_figures":0,"portfolio_qr_images":0,"readme_local_links":0,"markdown_local_links":0}
    for name in ["README.md",PORTFOLIO,"PROJECT_SPEC.md","DATA_DICTIONARY.md","LIMITATIONS.md"]:
        path=root/name
        text=path.read_text(encoding="utf-8")
        # Also recognize an image nested inside a clickable Markdown link.
        for match in re.finditer(r"(!?)\[(?![!\[])[^\]]*\]\(([^)]+)\)",text):
            image,target=match.groups()
            target=target.split("#")[0]
            if not target or re.match(r"https?://",target): continue
            assert not (re.match(r"(?:[A-Za-z]:|/)",target) or target.startswith("file:"+"/"*2)), f"Nonportable link in {name}"
            resolved=(path.parent/target).resolve()
            assert resolved.is_relative_to(root.resolve()), f"Link escapes release in {name}"
            assert resolved.exists(), f"Missing link: {name} -> {target}"
            counts["markdown_local_links"]+=1
            if name=="README.md": counts["readme_local_links"]+=1
            if image:
                assert name==PORTFOLIO, "Unexpected image source"
                counts["portfolio_images"]+=1
                counts["portfolio_qr_images" if target=="assets/github_qr.png" else "portfolio_data_figures"]+=1
    return counts

def check_numeric_content(root):
    s=load(root,"outputs/executive_summary.json")
    e=load(root,"outputs/models/wolfram_evaluation.json")
    text=(root/PORTFOLIO).read_text(encoding="utf-8")
    readme=(root/"README.md").read_text(encoding="utf-8")
    assert len(re.findall(r"^## \d+\.",text,re.M))==11
    for key, label in [("overall_d1","第1日留存"),("overall_d7","第7日留存"),("overall_d30","第30日留存"),("payer_conversion","曾付费用户比例")]:
        val=f"{s[key]:.2%}"
        assert f"| {label} | {val} |" in text, label
        assert val in readme, label
    for key in ["chapter3_completion_given_chapter2","chapter3_gate_failure_rate","capture_at_10pct","reactivation_rate"]:
        val=f"{s[key]:.2%}"
        assert val in text and val in readme, key
    for val in [f"{s['users']:,}",f"{s['reactivation_eligible']:,}",f"{s['reactivation_count']:,}",f"{s['post_return_active_days']:.2f}",f"{s['lift_at_10pct']:.2f}×",f"{s['device_d7_gap']*100:.2f}"]:
        assert val in text and val in readme, val
    for model in ["logistic","nonlinear"]:
        for key in ["roc_auc","pr_auc","brier"]:
            val=f"{e[model][key]:.4f}"
            assert val in text, f"{model}/{key}"
    assert e["logistic"]["roc_auc"]==s["model_auc"] and e["nonlinear"]["roc_auc"]==s["nonlinear_auc"]
    gate=next(r for r in table(root,"progression_diagnosis.csv") if int(r["level"])==12)
    assert abs(float(gate["failure_rate"])-s["chapter3_gate_failure_rate"])<1e-10
    assert abs(float(gate["failures"])/float(gate["attempts"])-s["chapter3_gate_failure_rate"])<1e-10
    f=[r for r in table(root,"funnel.csv") if r["dimension"]=="overall" and r["stage_type"]=="core"]
    byname={r["name"]:r for r in f}
    for name in ["chapter_2","chapter_3"]:
        val=f"{float(byname[name]['dropoff']):.2%}"
        assert val in text and val in readme
    assert abs(float(byname["chapter_3"]["conversion"])-s["chapter3_completion_given_chapter2"])<1e-10
    powers=load(root,"outputs/metrics/power_analysis.json")["experiments"]
    for r,power in zip(table(root,"experiment_design.csv"),powers):
        assert int(r["eligible_n"])==power["eligible_n"]
        assert int(r["per_arm"])==power["per_arm"]
        assert abs(float(r["baseline"])-power["baseline"])<1e-10
        for val in [f"{int(r['eligible_n']):,}",f"{int(r['per_arm']):,}",f"{float(r['baseline']):.2f}" if r["experiment"]=="C" else f"{float(r['baseline']):.2%}"]:
            assert val in text and val in readme
    assert "chapter_2" not in text and "sessions_d0_7" not in text
    assert "控制其他特征后的条件预测关联" in text and "实验尚未执行" in text
    return {"status":"PASS","users":s["users"],"numeric_content":"summary, progression, model and experiment values agree after rounding"}

def check_notebooks(root):
    nb=load(root,"notebooks/python_analysis_walkthrough.ipynb")
    code=[c for c in nb["cells"] if c["cell_type"]=="code"]
    assert code and all(c.get("execution_count") is not None for c in code)
    assert not any(o.get("output_type")=="error" for c in code for o in c.get("outputs",[]))
    source="\n".join("".join(c["source"]) for c in nb["cells"])
    assert "New registrations randomized at D0" not in source
    w=(root/"wolfram/AnalysisWalkthrough.nb").read_text(encoding="utf-8")
    assert "Notebook[" in w and "single session per day" not in w
    summary=load(root,"outputs/executive_summary.json")
    # Executed display of the summary in the Python notebook must contain current user count.
    displays=json.dumps([c.get("outputs",[]) for c in code],ensure_ascii=False)
    assert str(summary["users"]) in displays
    return {"status":"PASS","python_executed_cells":len(code),"wolfram_static":"PASS"}

def collect_files(root):
    paths=list(ROOT_FILES)
    if (root/"LICENSE").is_file(): paths.append("LICENSE")
    for folder,extensions in [("config",{".yaml",".wl",".json"}),("sql",{".sql"}),("wolfram",{".wl",".wls",".nb"}),("python_src",{".py"}),("tests",{".py"}),("tools",{".py",".ps1",".mjs"})]:
        paths.extend(p.relative_to(root).as_posix() for p in sorted((root/folder).iterdir()) if p.is_file() and p.suffix in extensions)
    paths+=["notebooks/python_analysis_walkthrough.ipynb",PORTFOLIO,PORTFOLIO_PDF,"outputs/executive_summary.json"]
    paths += ["outputs/tables/"+x for x in TABLES]
    paths += ["outputs/metrics/"+x for x in METRICS]
    paths += ["outputs/validation/"+x for x in VALIDATIONS]
    paths += [f"outputs/validation/{mode}/{x}" for mode in ["fast","full"] for x in HISTORICAL]
    for mode in ['python_fast','python_full','dual_fast','dual_full','wolfram_fast','generate_python','generate_wolfram','clean_source_fast']:
        for name in ['certificate.json','dataset_manifest.json','executive_summary.json','Project_Horizon_Portfolio.md']:
            relative=f'outputs/validation/modes/{mode}/{name}'
            if (root/relative).is_file():paths.append(relative)
        mode_md=root/f'outputs/validation/modes/{mode}/Project_Horizon_Portfolio.md'
        if mode_md.is_file():
            for image in re.findall(r'!\[[^\]]*\]\(([^)]+)\)',mode_md.read_text(encoding='utf8')):
                paths.append((mode_md.parent/image).relative_to(root).as_posix())
    paths += ["outputs/models/"+x+"_evaluation.json" for x in ["wolfram","python"]]
    paths += ["outputs/parity/"+x for x in ["wolfram_python_parity.md","wolfram_python_parity.csv","model_parity.csv","status.json"]]
    md=(root/PORTFOLIO).read_text(encoding="utf-8")
    paths += [(Path(PORTFOLIO).parent/m).as_posix() for m in re.findall(r"!\[[^\]]*\]\(([^)]+)\)",md)]
    # Notebook figure references are relative to root; include only referenced figures.
    nb=load(root,"notebooks/python_analysis_walkthrough.ipynb")
    source="\n".join("".join(c["source"]) for c in nb["cells"])
    paths += re.findall(r"outputs/figures/(?:python|wolfram)/[^'\"\s]+\.png",source)
    paths=sorted(set(paths))
    for name in paths:
        assert not is_banned(name), f"Banned whitelist entry: {name}"
        p=root/name
        assert p.is_file() and p.resolve().is_relative_to(root.resolve()), f"Missing or nonlocal whitelist file: {name}"
    return paths

def scan_tree(root):
    files=sorted(p for p in root.rglob("*") if p.is_file())
    for p in files:
        rel=p.relative_to(root).as_posix()
        assert not is_banned(rel), f"Banned release file: {rel}"
        if p.suffix not in TEXT_EXT and p.name not in {".env.example",".gitignore",".gitattributes","LICENSE"}: continue
        text=p.read_text(encoding="utf-8")
        assert not (re.search(r"\b[A-Za-z]:[\\/]",text) or "file:"+"/"*2 in text or "Google"+" Drive:" in text), f"Absolute path in {rel}"
        # Report filenames only; never expose candidate secrets in diagnostics.
        assert not re.search(r"postgres(?:ql)?://[^\s/:]+:[^\s@/]+@",text), f"Credential URI in {rel}"
        for line in text.splitlines():
            m=re.match(r"\s*['\"]?(?:password|HORIZON_DB_PASSWORD)['\"]?\s*[:=]\s*(.*)$",line,re.I)
            if m:
                value=m.group(1).strip().rstrip(",").strip().strip("'\"")
                placeholders={"","your_password","<password>","changeme"}
                environment_read=bool(re.match(r"os\.getenv\(['\"]HORIZON_DB_PASSWORD['\"],\s*['\"]['\"]\)",value))
                assert value=="" or environment_read or (p.name==".env.example" and value in placeholders), f"Credential assignment in {rel}"
    return {"banned_files":"PASS","secrets":"PASS","absolute_paths":"PASS","files_scanned":len(files)}

def validate_tree(root):
    result=scan_tree(root)
    result['source_provenance']=check_source_provenance(root)
    result.update(check_links(root))
    result["numeric_content"]=check_numeric_content(root)
    result["notebooks"]=check_notebooks(root)
    result["pdf_numeric_content"]=check_pdf_numeric_content(root)
    sizes=[{"path":p.relative_to(root).as_posix(),"bytes":p.stat().st_size} for p in sorted((p for p in root.rglob("*") if p.is_file()),key=lambda p:p.stat().st_size,reverse=True)]
    result["largest_files"]=sizes[:10]
    result["over_10mb"]=[x for x in sizes if x["bytes"]>10*1024*1024]
    assert not result["over_10mb"], "Unnecessary release files exceed 10 MiB"
    return result


def check_source_provenance(root):
    """Fail closed for every certificate distributed as current mode evidence."""
    def require(condition,message):
        if not condition:raise AssertionError(message)
    root=Path(root);actual=source_manifest(root)
    release=load(root,'outputs/validation/final_release.json')
    require(release.get('code_sha256')==actual['code_sha256'], 'Release source fingerprint mismatch')
    require(release.get('fingerprint_algorithm')==ALGORITHM, 'Release fingerprint algorithm missing/mismatch')
    registry=release.get('mode_certificates')
    require(isinstance(registry,dict) and registry, 'Current mode registry missing')
    certificates=list((root/'outputs/validation/modes').glob('*/certificate.json'))
    require({p.parent.name for p in certificates}==set(registry), 'Current mode certificates missing/unregistered')
    for path in certificates:
        certificate=load(root,path.relative_to(root));manifest=load(root,path.parent.relative_to(root)/'dataset_manifest.json')
        require(certificate.get('status')=='PASS', f'Current mode not PASS: {path.parent.name}')
        require(certificate.get('fingerprint_algorithm')==ALGORITHM, f'Certificate algorithm mismatch: {path.parent.name}')
        require(certificate.get('code_sha256')==actual['code_sha256'], f'Certificate source fingerprint mismatch: {path.parent.name}')
        require(isinstance(certificate.get('dataset_sha256'),str) and bool(certificate['dataset_sha256']), f'Certificate dataset fingerprint missing: {path.parent.name}')
        require(certificate.get('dataset_sha256')==manifest.get('dataset_sha256'), f'Certificate dataset fingerprint mismatch: {path.parent.name}')
        require(manifest.get('status')=='COMPLETE' and certificate.get('scale')==manifest.get('scale'), f'Incomplete/mismatched dataset: {path.parent.name}')
        entry=registry[path.parent.name]
        for key in ['run_id','scope','scale','dataset_sha256']:
            require(entry.get(key)==certificate.get(key), f'Release registry mismatch: {path.parent.name}/{key}')
    return dict(status='PASS',**actual,certificates=len(certificates))


def check_pdf_numeric_content(root):
    """A readable but stale PDF must not pass release acceptance."""
    from pypdf import PdfReader
    reader=PdfReader(root/PORTFOLIO_PDF)
    text='\n'.join(page.extract_text() for page in reader.pages)
    summary=load(root,'outputs/executive_summary.json')
    models=load(root,'outputs/models/wolfram_evaluation.json')
    for key in ['overall_d1','overall_d7','overall_d30','payer_conversion','chapter3_gate_failure_rate','reactivation_rate']:
        assert f'{summary[key]:.2%}' in text, f'Stale PDF metric: {key}'
    for model in ['logistic','nonlinear']:
        for key in ['roc_auc','pr_auc','brier']:
            assert f'{models[model][key]:.4f}' in text, f'Stale PDF model: {model}/{key}'
    return dict(status='PASS',pages=len(reader.pages),source='current published summary and model evaluations')
