"""Read raw PostgreSQL facts. No Wolfram computed tables are queried."""
import json
import os
import re
from typing import Any
import pandas as pd
import psycopg
from .config import connection_parameters, OUT

def connect() -> psycopg.Connection:
    return psycopg.connect(**connection_parameters())


def schema_name() -> str:
    name = os.environ.get('HORIZON_DB_SCHEMA', 'horizon')
    if not re.fullmatch(r'[a-z][a-z0-9_]{0,62}', name):
        raise ValueError('HORIZON_DB_SCHEMA must be a lowercase SQL identifier (max 63 characters)')
    return name


def resolve_sql(sql: str) -> str:
    """Keep existing metric SQL intact while selecting an isolated dataset."""
    return re.sub(r'\bhorizon\b', schema_name(), sql)

def query(sql: str, params: tuple | None = None) -> pd.DataFrame:
    with connect() as con, con.cursor() as cur:
        cur.execute(resolve_sql(sql), params)
        return pd.DataFrame(cur.fetchall(), columns=[c.name for c in cur.description])

def save_json(path, obj: Any) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False, default=lambda x: x.item()), encoding='utf-8')

def load_raw() -> dict[str, pd.DataFrame]:
    """One row per observed user-day; raw session measures remain unmodified."""
    users = query('SELECT user_id,register_date,market,acquisition_channel,device,campaign FROM horizon.users').set_index('user_id')
    users['register_date'] = pd.to_datetime(users['register_date'])
    sessions = query('SELECT user_id,session_date,session_minutes,fps_quality_bucket,crash_flag FROM horizon.sessions')
    sessions['session_date'] = pd.to_datetime(sessions['session_date'])
    return dict(users=users, sessions=sessions)
