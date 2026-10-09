"""Executed PostgreSQL chronology, integrity and missingness acceptance."""
import pandas as pd
import os
from python_src.config import OUT,ROOT
from python_src.database import query,connect,resolve_sql

def test_quality_checks_pass():
    for name in (['data_quality_summary.csv'] if os.environ.get('HORIZON_ANALYSIS_MODE')=='wolfram' else ['data_quality_summary.csv','python_data_quality.csv']):
        f=pd.read_csv(OUT/'tables'/name)
        assert f.failures.sum()==0

def test_foreign_keys_enforced():
    with connect() as con:
        with con.cursor() as cur:
            cur.execute(resolve_sql("SELECT count(*) FROM pg_constraint WHERE contype='f' AND connamespace='horizon'::regnamespace"))
            assert cur.fetchone()[0]==6

def test_payment_dates_and_values():
    assert query("SELECT count(*) FROM horizon.monetization m JOIN horizon.users u USING(user_id) WHERE transaction_date<register_date OR transaction_date>DATE '2026-06-29' OR amount_usd<0").iloc[0,0]==0

def test_drop_and_create_sql_transactionally():
    # Execute the exact reset schema SQL then roll back: existing run stays intact.
    con=connect()
    try:
        with con.cursor() as cur:
            cur.execute(resolve_sql((ROOT/'sql/00_drop_schema.sql').read_text()))
            cur.execute(resolve_sql((ROOT/'sql/00_create_schema.sql').read_text()))
            cur.execute(resolve_sql('SELECT count(*) FROM horizon.users'))
            assert cur.fetchone()[0]==0
        con.rollback()
    finally:con.close()
    assert query('SELECT count(*) FROM horizon.users').iloc[0,0]>0
def test_manifest_structure_independent_of_search_path():
    from python_src.dataset import structure
    from python_src.database import connect, schema_name
    with connect() as con:
        expected=structure(con)
        for path in [schema_name()+', public', 'pg_catalog', '"$user", public']:
            con.execute("SELECT set_config('search_path',%s,false)",(path,))
            before=con.execute('SHOW search_path').fetchone()[0]
            assert structure(con)==expected
            assert con.execute('SHOW search_path').fetchone()[0]==before
        con.rollback()
