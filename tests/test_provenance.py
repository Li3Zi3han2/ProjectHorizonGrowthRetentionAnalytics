"""Portable sorting and fail-closed publication, without a database or cached PASS."""
import hashlib
import json
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath
import pytest
from python_src.provenance import ALGORITHM, FOLDERS, source_files, source_fingerprint
from tools.release_checks import check_source_provenance

def fixture(root):
    for folder in FOLDERS:(root/folder).mkdir(parents=True)
    for name in ['config/config.yaml','sql/query.sql','tests/check.py','wolfram/Alpha.wl','wolfram/Zeta.wl','wolfram/lower.wl','python_src/module.py','run_all.ps1','run_all.sh']:
        (root/name).write_bytes((name+'\r\n').encode())
    code=source_fingerprint(root)
    dest=root/'outputs/validation/modes/python_fast';dest.mkdir(parents=True)
    certificate=dict(status='PASS',fingerprint_algorithm=ALGORITHM,code_sha256=code,dataset_sha256='data',run_id='run',scope='python_only',scale='fast')
    (dest/'certificate.json').write_text(json.dumps(certificate),encoding='utf8')
    (dest/'dataset_manifest.json').write_text(json.dumps(dict(status='COMPLETE',dataset_sha256='data',scale='fast')),encoding='utf8')
    (root/'outputs/validation/final_release.json').write_text(json.dumps(dict(code_sha256=code,fingerprint_algorithm=ALGORITHM,mode_certificates={'python_fast':certificate})),encoding='utf8')
    return code,dest

def test_portable_fingerprint_uses_explicit_order_and_raw_bytes(tmp_path):
    code,_=fixture(tmp_path)
    names=source_files(tmp_path)
    assert names==sorted(names)
    assert sorted(names,key=PureWindowsPath)!=sorted(names,key=PurePosixPath)
    digest=hashlib.sha256()
    for name in sorted(names):digest.update(name.encode());digest.update((tmp_path/name).read_bytes())
    assert code==digest.hexdigest()
    (tmp_path/'run_all.ps1').write_bytes(b'changed\n')
    assert source_fingerprint(tmp_path)!=code

@pytest.mark.parametrize('change',['source','missing_source','certificate','dataset','missing_manifest','missing_certificate','unregistered','algorithm'])
def test_release_provenance_fails_closed(tmp_path,change):
    _,dest=fixture(tmp_path);assert check_source_provenance(tmp_path)['status']=='PASS'
    if change=='source':(tmp_path/'run_all.sh').write_bytes(b'new')
    elif change=='missing_source':(tmp_path/'python_src/module.py').unlink()
    elif change=='missing_manifest':(dest/'dataset_manifest.json').unlink()
    elif change=='missing_certificate':(dest/'certificate.json').unlink()
    elif change=='unregistered':
        import shutil
        shutil.copytree(dest,dest.parent/'unexpected')
    else:
        path=dest/('dataset_manifest.json' if change=='dataset' else 'certificate.json')
        data=json.loads(path.read_text());data['dataset_sha256' if change=='dataset' else 'fingerprint_algorithm' if change=='algorithm' else 'code_sha256']='wrong'
        path.write_text(json.dumps(data))
    with pytest.raises((AssertionError,FileNotFoundError)):check_source_provenance(tmp_path)

def test_independent_zip_extraction_recomputes_fingerprint(tmp_path):
    root=tmp_path/'source';root.mkdir();code,_=fixture(root)
    archive=tmp_path/'release.zip'
    with zipfile.ZipFile(archive,'w') as z:
        for p in root.rglob('*'):
            if p.is_file():z.write(p,p.relative_to(root).as_posix())
    extracted=tmp_path/'extracted'
    with zipfile.ZipFile(archive) as z:z.extractall(extracted)
    assert source_fingerprint(extracted)==code
    assert check_source_provenance(extracted)['code_sha256']==code
    (extracted/'run_all.sh').write_bytes(b'corrupt after extraction')
    with pytest.raises(AssertionError):check_source_provenance(extracted)
