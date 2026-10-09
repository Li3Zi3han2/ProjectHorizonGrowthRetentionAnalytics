"""Independent database QA, full foreign keys, missingness and maturity audit."""
from .config import OUT
from .database import query

def calculate() -> None:
    checks = {
      'orphan_events': 'SELECT count(*) n FROM horizon.gameplay_events e LEFT JOIN horizon.users u USING(user_id) WHERE u.user_id IS NULL',
      'bad_progression_date': "SELECT count(*) n FROM horizon.progression p JOIN horizon.users u USING(user_id) WHERE p.event_date<u.register_date OR p.event_date>DATE '2026-06-29'",
      'bad_payment_date': "SELECT count(*) n FROM horizon.monetization p JOIN horizon.users u USING(user_id) WHERE p.transaction_date<u.register_date OR p.transaction_date>DATE '2026-06-29'",
      'bad_exposure_date': "SELECT count(*) n FROM horizon.content_exposure p JOIN horizon.users u USING(user_id) WHERE p.date<u.register_date OR p.date>DATE '2026-06-29'",
      'bad_sessions': "SELECT count(*) n FROM horizon.sessions s JOIN horizon.users u USING(user_id) WHERE session_date<u.register_date OR session_date>DATE '2026-06-29' OR session_minutes<=0",
      'bad_session_sequence': 'SELECT count(*) n FROM (SELECT session_number,row_number() OVER(PARTITION BY user_id ORDER BY session_id) expected FROM horizon.sessions) x WHERE session_number<>expected',
      'duplicate_progression_day': 'SELECT count(*) n FROM (SELECT user_id,event_date FROM horizon.progression GROUP BY 1,2 HAVING count(*)>1) x',
      'null_users': 'SELECT count(*) n FROM horizon.users WHERE register_date IS NULL OR market IS NULL OR device IS NULL',
      'null_sessions': 'SELECT count(*) n FROM horizon.sessions WHERE session_minutes IS NULL OR crash_flag IS NULL',
    }
    rows = [dict(check_name=name,failures=int(query(sql).iloc[0,0])) for name,sql in checks.items()]
    import pandas as pd
    pd.DataFrame(rows).to_csv(OUT / 'tables/python_data_quality.csv',index=False)
    assert all(r['failures']==0 for r in rows), rows
    query("SELECT 'D'||d horizon,count(*) eligible FROM horizon.users CROSS JOIN (VALUES(1),(7),(30)) h(d) WHERE register_date+d<=DATE '2026-06-29' GROUP BY d ORDER BY d").to_csv(OUT / 'tables/cohort_maturity.csv',index=False)
