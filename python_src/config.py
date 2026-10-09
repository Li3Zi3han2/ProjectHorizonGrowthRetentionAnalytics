"""Portable configuration; secrets are local environment values."""
from pathlib import Path
import os
import yaml

ROOT = Path(__file__).resolve().parents[1]
for line in (ROOT / '.env').read_text(encoding='utf-8-sig').splitlines() if (ROOT / '.env').exists() else []:
    if '=' in line and not line.lstrip().startswith('#'):
        key, value = line.split('=', 1)
        os.environ.setdefault(key.strip(), value.strip())
CONFIG = yaml.safe_load((ROOT / 'config/config.yaml').read_text(encoding='utf-8'))
START = CONFIG['start_date']
END = CONFIG['end_date']
OUT = Path(os.environ.get('HORIZON_OUTPUT_DIR', ROOT / 'outputs')).resolve()
ARTIFACT_ROOT = Path(os.environ.get('HORIZON_ARTIFACT_ROOT', ROOT)).resolve()
for sub in ['tables', 'metrics', 'models', 'parity', 'validation', 'figures/python', 'figures/wolfram', 'report', 'staging']:
    (OUT / sub).mkdir(parents=True, exist_ok=True)

def connection_parameters() -> dict:
    """Resolve PostgreSQL connection without logging credentials."""
    return dict(host=os.getenv('HORIZON_DB_HOST', 'localhost'), port=int(os.getenv('HORIZON_DB_PORT', '5432')),
                dbname=os.getenv('HORIZON_DB_NAME', 'project_horizon'), user=os.getenv('HORIZON_DB_USER', ''),
                password=os.getenv('HORIZON_DB_PASSWORD', ''), connect_timeout=10)
