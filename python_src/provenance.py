"""Portable source identity: ordinal POSIX relative names followed by raw bytes."""
import hashlib
from pathlib import Path

ALGORITHM = 'horizon-source-v2-posix-ordinal-raw-bytes'
FOLDERS = ('config', 'sql', 'wolfram', 'python_src', 'tests')
EXTENSIONS = {'.py', '.wl', '.wls', '.sql', '.yaml'}

def source_files(root):
    root = Path(root)
    names = [p.relative_to(root).as_posix() for folder in FOLDERS
             for p in (root / folder).iterdir() if p.is_file() and p.suffix in EXTENSIONS]
    return sorted(names + ['run_all.ps1', 'run_all.sh'])

def source_fingerprint(root):
    root = Path(root)
    digest = hashlib.sha256()
    for name in source_files(root):
        digest.update(name.encode('utf8'))
        digest.update((root / name).read_bytes())
    return digest.hexdigest()

def source_manifest(root):
    root = Path(root)
    return {'algorithm': ALGORITHM, 'code_sha256': source_fingerprint(root),
            'files': [{'path': name, 'bytes': (root / name).stat().st_size,
                       'sha256': hashlib.sha256((root / name).read_bytes()).hexdigest()}
                      for name in source_files(root)]}
