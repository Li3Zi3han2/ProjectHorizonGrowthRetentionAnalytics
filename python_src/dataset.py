"""Completed dataset manifests, content digests and non-destructive publication."""
import hashlib
import json
from datetime import datetime, timezone
from psycopg import sql
from .config import CONFIG, ROOT, OUT
from .database import connect, schema_name, resolve_sql, save_json

TABLE_KEYS = {'users': 'user_id', 'sessions': 'session_id', 'progression': 'user_id,event_date',
              'gameplay_events': 'event_id', 'monetization': 'transaction_id',
              'acquisition': 'user_id', 'content_exposure': 'user_id,date,content_id'}
SCHEMA_VERSION = 'horizon-1'


def content(con, prefix=None):
    counts, digests = {}, {}
    with con.cursor() as cur:
        for table, key in TABLE_KEYS.items():
            cur.execute(resolve_sql(f'SELECT count(*) FROM horizon.{table}'))
            counts[table] = cur.fetchone()[0]
            where = f'WHERE user_id<={int(prefix)}' if prefix is not None else ''
            digest = hashlib.sha256()
            with cur.copy(resolve_sql(f'COPY (SELECT * FROM horizon.{table} {where} ORDER BY {key}) TO STDOUT WITH (FORMAT CSV, HEADER TRUE)')) as stream:
                for block in stream:
                    digest.update(block)
            digests[table] = digest.hexdigest()
    fingerprint = hashlib.sha256(json.dumps(digests, sort_keys=True).encode()).hexdigest()
    return dict(row_counts=counts, table_sha256=digests, dataset_sha256=fingerprint)


def structure(con):
    rows = con.execute('SELECT table_name,column_name,data_type,is_nullable FROM information_schema.columns WHERE table_schema=%s ORDER BY table_name,ordinal_position', (schema_name(),)).fetchall()
    # pg_get_constraintdef omits schemas visible through search_path, including
    # the default "$user" entry when role and schema are both horizon.
    # Force qualified definitions while preserving the caller's connection state.
    previous=con.execute('SHOW search_path').fetchone()[0]
    try:
        con.execute("SELECT set_config('search_path','pg_catalog',false)")
        constraints = con.execute('SELECT c.relname,pg_get_constraintdef(k.oid) FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid WHERE k.connamespace=%s::regnamespace ORDER BY c.relname,pg_get_constraintdef(k.oid)', (schema_name(),)).fetchall()
    finally:
        con.execute("SELECT set_config('search_path',%s,false)",(previous,))
    constraints=[(table,definition.replace(schema_name()+'.','<dataset>.')) for table,definition in constraints]
    return dict(columns=rows, constraints=constraints)


def checks(con, expected):
    queries = {
        'user_identity': f'SELECT CASE WHEN count(*)={expected} AND min(user_id)=1 AND max(user_id)={expected} THEN 0 ELSE 1 END FROM horizon.users',
        'acquisition_complete': 'SELECT count(*) FROM horizon.users u LEFT JOIN horizon.acquisition a USING(user_id) WHERE a.user_id IS NULL',
        'registration_session': 'SELECT count(*) FROM horizon.users u WHERE NOT EXISTS(SELECT 1 FROM horizon.sessions s WHERE s.user_id=u.user_id AND s.session_date=u.register_date)',
        'registration_range': "SELECT count(*) FROM horizon.users WHERE register_date<DATE '2026-01-01' OR register_date>DATE '2026-06-29' OR acquisition_quality NOT BETWEEN 0.05 AND 0.95",
        'session_dates': "SELECT count(*) FROM horizon.sessions s JOIN horizon.users u USING(user_id) WHERE session_date<register_date OR session_date>DATE '2026-06-29' OR session_minutes<=0 OR session_minutes='NaN'::float8",
        'session_sequence': 'SELECT count(*) FROM (SELECT session_number,row_number() OVER(PARTITION BY user_id ORDER BY session_id) n FROM horizon.sessions) s WHERE session_number<>n',
        'progression_rules': 'SELECT count(*) FROM (SELECT *,lag(chapter) OVER(PARTITION BY user_id ORDER BY event_date) previous FROM horizon.progression) p WHERE chapter<previous OR chapter NOT BETWEEN 0 AND 6 OR boss_failures>boss_attempts OR boss_failures<0 OR boss_attempts<0 OR tutorial_completed NOT IN(0,1) OR core_loop_unlocked NOT IN(0,1)',
        'event_dates': "SELECT count(*) FROM horizon.gameplay_events e JOIN horizon.users u USING(user_id) WHERE event_time::date<register_date OR event_time::date>DATE '2026-06-29'",
        'progression_dates': "SELECT count(*) FROM horizon.progression p JOIN horizon.users u USING(user_id) WHERE event_date<register_date OR event_date>DATE '2026-06-29'",
        'payment_dates': "SELECT count(*) FROM horizon.monetization p JOIN horizon.users u USING(user_id) WHERE transaction_date<register_date OR transaction_date>DATE '2026-06-29' OR amount_usd<0",
        'exposure_dates': "SELECT count(*) FROM horizon.content_exposure p JOIN horizon.users u USING(user_id) WHERE date<register_date OR date>DATE '2026-06-29' OR exposed NOT IN(0,1) OR clicked NOT IN(0,1)",
    }
    values = {key: con.execute(resolve_sql(query)).fetchone()[0] for key, query in queries.items()}
    foreign_keys = con.execute("SELECT count(*) FROM pg_constraint WHERE contype='f' AND connamespace=%s::regnamespace AND convalidated", (schema_name(),)).fetchone()[0]
    values['foreign_keys'] = int(foreign_keys != 6)
    if any(values.values()):
        raise ValueError(f'Dataset integrity failed: {values}')
    return values


def register(scale, generator, run_id):
    """Called only after an explicit generation/adoption, never by AnalyzeOnly."""
    expected = CONFIG['fast_users' if scale == 'fast' else 'users']
    from .validation import fingerprint
    source_files = ['config/config.yaml', 'sql/00_create_schema.sql',
                    'python_src/generate.py' if generator == 'Python' else 'wolfram/GenerateData.wl']
    digest = hashlib.sha256()
    for name in source_files:
        digest.update(name.encode()); digest.update((ROOT/name).read_bytes())
    with connect() as con:
        result = content(con)
        result.update(scale=scale, expected_users=expected, actual_users=result['row_counts']['users'],
                      generator=generator, seed=CONFIG['seed'], parameters=CONFIG, schema_version=SCHEMA_VERSION,
                      generator_sha256=digest.hexdigest(), code_sha256=fingerprint(), schema=structure(con),
                      checks=checks(con, expected), status='COMPLETE', run_id=run_id,
                      generated_at=datetime.now(timezone.utc).isoformat(),
                      location={'database':con.info.dbname,'schema':schema_name()},
                      random_algorithm='NumPy RandomState MT19937 per user; different draws from Wolfram' if generator == 'Python' else 'Wolfram MersenneTwister per user')
        con.execute(resolve_sql("INSERT INTO horizon.run_metadata VALUES('dataset_manifest',%s) ON CONFLICT(key) DO UPDATE SET value=excluded.value"), (json.dumps(result, default=str),))
        for table in TABLE_KEYS:
            con.execute(resolve_sql(f'ANALYZE horizon.{table}'))
    save_json(OUT/'dataset_manifest.json', result)
    return result


def validate(scale, con=None):
    own = con is None
    con = con or connect()
    try:
        exists = con.execute('SELECT to_regclass(%s)', (schema_name()+'.run_metadata',)).fetchone()[0]
        if exists is None:
            raise ValueError('Existing dataset/manifest missing; use -GenerateOnly or a complete generation run first')
        row = con.execute(resolve_sql("SELECT value FROM horizon.run_metadata WHERE key='dataset_manifest'")).fetchone()
        if row is None:
            raise ValueError('Completed dataset manifest missing; AnalyzeOnly will not rebuild or adopt data')
        manifest = json.loads(row[0])
        expected = CONFIG['fast_users' if scale == 'fast' else 'users']
        if manifest['status'] != 'COMPLETE' or manifest['scale'] != scale or manifest['expected_users'] != expected or manifest['schema_version'] != SCHEMA_VERSION:
            raise ValueError('Existing dataset scale/completion/schema version does not match requested Fast/Full')
        if json.loads(json.dumps(structure(con))) != manifest['schema']:
            raise ValueError('Dataset SQL schema or constraints changed since generation')
        checks(con, expected)
        actual = content(con)
        if actual['dataset_sha256'] != manifest['dataset_sha256'] or actual['row_counts'] != manifest['row_counts']:
            raise ValueError('Dataset content fingerprint changed; AnalyzeOnly cannot consume modified facts')
        return manifest
    finally:
        if own: con.close()


def publish(build_schema, target_schema, run_id, allow_replace=False):
    """Rename atomically; preserve a complete old schema as a recoverable backup."""
    with connect() as con:
        exists = con.execute('SELECT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname=%s)', (target_schema,)).fetchone()[0]
        backup = None
        if exists:
            if not allow_replace:
                raise ValueError('Target schema already exists. Choose an empty HORIZON_DB_SCHEMA, or explicitly set HORIZON_ALLOW_REPLACE=1 to keep a backup and replace it')
            backup = target_schema[:30]+'_backup_'+run_id.replace('-', '')[:12]
            con.execute(sql.SQL('ALTER SCHEMA {} RENAME TO {}').format(sql.Identifier(target_schema), sql.Identifier(backup)))
        con.execute(sql.SQL('ALTER SCHEMA {} RENAME TO {}').format(sql.Identifier(build_schema), sql.Identifier(target_schema)))
        return backup
