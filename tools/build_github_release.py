"""Build an explicit whitelist, verify it, and reopen the completed ZIP."""
import hashlib
import json
import shutil
import sys
import zipfile
import tempfile
from pathlib import Path
from release_checks import collect_files, validate_tree, source_manifest

def build(root):
    root=root.resolve()
    release=root/"release"
    tree=release/"github"/"Project-Horizon"
    archive=release/"ProjectHorizonGrowthRetentionAnalytics.zip"
    for target in [release,tree,archive]:
        assert target.resolve().is_relative_to(root) and target.resolve()!=root, "Release path escapes workspace"
        assert target.resolve()==target.absolute(), "Release path must not traverse a junction or symbolic link"
        assert not target.is_symlink(), "Release target must not be a symbolic link"
    selected=collect_files(root)
    # The only recursively removed directory is this fixed, verified release tree.
    if tree.exists(): shutil.rmtree(tree)
    tree.mkdir(parents=True)
    for name in selected:
        dest=tree/name
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(root/name,dest)
    checks=validate_tree(tree)
    assert checks['source_provenance']==dict(source_manifest(root),status='PASS',certificates=checks['source_provenance']['certificates']), 'Worktree/release source inputs differ'
    with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in selected:
            info=zipfile.ZipInfo("Project-Horizon/"+name,date_time=(2026,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=(0o755 if name.endswith(".sh") else 0o644)<<16
            z.writestr(info,(tree/name).read_bytes())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert z.namelist()==["Project-Horizon/"+name for name in selected]
        for name in selected:
            assert z.read("Project-Horizon/"+name)==(tree/name).read_bytes()
        with tempfile.TemporaryDirectory(prefix='horizon-release-verify-') as directory:
            z.extractall(directory)
            reopened=validate_tree(Path(directory)/'Project-Horizon')
            assert reopened['source_provenance']==checks['source_provenance'], 'Extracted source identity changed'
            checks['independent_extracted_fingerprint']=reopened['source_provenance']['code_sha256']
    checks.update(zip_name=archive.name,zip_bytes=archive.stat().st_size,file_count=len(selected),
                  zip_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),zip_integrity="PASS")
    (release/"release_manifest.txt").write_text("\n".join("Project-Horizon/"+x for x in selected)+"\n",encoding="utf-8")
    (release/"release_validation.txt").write_text(json.dumps(checks,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"zip":str(archive),"file_count":len(selected),"bytes":archive.stat().st_size,"validation":"PASS"},ensure_ascii=False))
    return checks

if __name__=="__main__":
    build(Path(__file__).resolve().parents[1])
