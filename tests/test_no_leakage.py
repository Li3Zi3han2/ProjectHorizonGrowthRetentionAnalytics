"""Check predictor lineage and temporal partitions, plus a future-data mutation."""
import pandas as pd
from python_src.config import OUT,END,START
from python_src.churn import NUMERIC,design
from python_src.database import connect,query,resolve_sql

def test_feature_window_and_latent_exclusion():
    f=pd.read_csv(OUT/'tables/python_features.csv')
    assert f.max_feature_day.between(0,7).all()
    assert (pd.to_datetime(f.register_date)+pd.Timedelta(days=30)<=pd.Timestamp(END)).all()
    x=design(f)
    assert not any(any(bad in col for bad in ['latent','quality','propensity','churn','future','label']) for col in x.columns if col!='fps_quality')
    assert 'churn_30' not in x.columns

def test_temporal_split():
    f=pd.read_csv(OUT/'tables/python_features.csv')
    train=f.loc[f.registration_day.le(89)];val=f.loc[f.registration_day.between(90,119)];test=f.loc[f.registration_day.gt(119)]
    assert train.registration_day.max()<val.registration_day.min()<test.registration_day.min()
    assert test.registration_day.max()<=149

def test_future_mutation_cannot_change_early_minutes():
    uid=int(query("SELECT s.user_id FROM horizon.sessions s JOIN horizon.users u USING(user_id) WHERE session_date-register_date>7 LIMIT 1").iloc[0,0])
    sql="SELECT sum(session_minutes) FROM horizon.sessions s JOIN horizon.users u USING(user_id) WHERE s.user_id=%s AND session_date-register_date BETWEEN 0 AND 7"
    with connect() as con,con.cursor() as cur:
        cur.execute(resolve_sql(sql),(uid,));before=cur.fetchone()[0]
        cur.execute(resolve_sql('UPDATE horizon.sessions s SET session_minutes=session_minutes+1000 FROM horizon.users u WHERE s.user_id=u.user_id AND s.user_id=%s AND s.session_date-u.register_date>7'),(uid,))
        assert cur.rowcount>0
        cur.execute(resolve_sql(sql),(uid,));assert cur.fetchone()[0]==before
        con.rollback()
