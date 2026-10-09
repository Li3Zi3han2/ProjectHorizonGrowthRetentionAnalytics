"""Code-bound fast/full certification and actual notebook execution evidence."""
import argparse
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime,timezone
from pathlib import Path
from .config import ROOT,OUT,ARTIFACT_ROOT
from .database import save_json,query,connect

def fingerprint() -> str:
    from .provenance import source_fingerprint
    return source_fingerprint(ROOT)

def prefix_digests() -> dict:
    """Hash actual facts for identical seed prefix across fast and full runs."""
    keys={'users':'user_id','sessions':'session_id','progression':'user_id,event_date','gameplay_events':'event_id','monetization':'transaction_id','acquisition':'user_id','content_exposure':'user_id,date,content_id'}
    result={}
    with connect() as con,con.cursor() as cur:
        for table,key in keys.items():
            h=hashlib.sha256()
            with cur.copy(f'COPY (SELECT * FROM horizon.{table} WHERE user_id<=20000 ORDER BY {key}) TO STDOUT WITH (FORMAT CSV, HEADER TRUE)') as copy:
                for block in copy:h.update(block)
            result[table]=h.hexdigest()
    return result

def main() -> None:
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['gate','certify','notebook']);parser.add_argument('--mode',choices=['fast','full']);args=parser.parse_args()
    if args.action=='gate':
        cert=json.loads((OUT/'validation/fast/certificate.json').read_text())
        assert cert['status']=='PASS' and cert['users']==20000
        assert cert['code_sha256']==fingerprint(),'Code changed after fast validation: rerun fast first'
        print('Fast / pytest / parity gate passed')
    elif args.action=='notebook':
        import os
        for key,folder in [('IPYTHONDIR','ipython'),('JUPYTER_RUNTIME_DIR','jupyter/runtime'),('JUPYTER_CONFIG_DIR','jupyter/config')]:
            local=ROOT/'.local'/folder;local.mkdir(parents=True,exist_ok=True);os.environ[key]=str(local)
        import nbformat
        from nbclient import NotebookClient
        path=ARTIFACT_ROOT/'notebooks/python_analysis_walkthrough.ipynb'
        nb=nbformat.read(path,as_version=4)
        client=NotebookClient(nb,timeout=180,kernel_name='python3',resources={'metadata':{'path':str(ROOT)}})
        # Kernel uses this exact venv, independent of globally registered kernels.
        client.execute()
        nbformat.write(nb,path)
        nbformat.write(nb,ARTIFACT_ROOT/'notebooks/analysis_walkthrough.ipynb')
        save_json(OUT/'metrics/notebook_execution.json',dict(status='PASS',executed_cells=sum(c.cell_type=='code' for c in nb.cells)))
        print('Python notebook executed')
    else:
        parity=json.loads((OUT/'parity/status.json').read_text());assert parity['status']=='PASS'
        tests=ET.parse(OUT/'metrics/pytest.xml').getroot().find('testsuite')
        assert int(tests.attrib['failures'])==0 and int(tests.attrib['errors'])==0
        users=int(query('SELECT count(*) FROM horizon.users').iloc[0,0])
        expected=20000 if args.mode=='fast' else 200000
        assert users==expected
        dest=OUT/'validation'/args.mode;dest.mkdir(parents=True,exist_ok=True)
        import shutil
        for folder,file in [('metrics','generation.json'),('metrics','pytest.xml'),('parity','status.json'),('parity','wolfram_python_parity.md'),('metrics','wolfram_selftest.json'),('metrics','notebook_execution.json')]:shutil.copy2(OUT/folder/file,dest/file)
        for file in ['synthetic_calibration.json','synthetic_calibration.csv','feature_diagnostics.json']:shutil.copy2(OUT/'validation'/file,dest/file)
        digests=prefix_digests()
        import platform
        from importlib.metadata import version
        wlpath=OUT/'metrics/wolfram_environment.json'
        wl_runtime=json.loads(wlpath.read_text()) if wlpath.exists() else {'version':'not recorded in this certificate'}
        save_json(OUT/'metrics/environment.json',dict(python=sys.version,platform=platform.platform(),postgresql=query('SELECT version()').iloc[0,0],dependencies={p:version(p) for p in ['numpy','pandas','psycopg','scipy','scikit-learn','matplotlib','statsmodels','pytest','reportlab','nbclient']},wolfram=wl_runtime))
        if args.mode=='full':
            fast=json.loads((OUT/'validation/fast/certificate.json').read_text())
            assert digests==fast['first_20000_fact_sha256'],'Full / fast same-seed fact prefix differs'
        save_json(dest/'certificate.json',dict(status='PASS',mode=args.mode,users=users,code_sha256=fingerprint(),first_20000_fact_sha256=digests,same_seed_prefix_verified=True,tests=int(tests.attrib['tests']),parity=parity,executed_at=datetime.now(timezone.utc).isoformat()))
        print(f'{args.mode} validated: {users:,} users, {tests.attrib["tests"]} tests')

if __name__=='__main__':main()
