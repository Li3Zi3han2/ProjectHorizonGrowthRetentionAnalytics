"""I/O adapter only: COPY Wolfram-generated CSV, never generate or analyze data."""
import argparse
from .config import ROOT, OUT
from .database import connect, resolve_sql

TABLES = ['users', 'sessions', 'progression', 'gameplay_events', 'monetization', 'acquisition', 'content_exposure']

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['reset', 'load', 'finalize'])
    parser.add_argument('--users', type=int)
    parser.add_argument('--seed', type=int)
    args = parser.parse_args()
    with connect() as con, con.cursor() as cur:
        if args.action == 'reset':
            cur.execute(resolve_sql((ROOT / 'sql/00_create_schema.sql').read_text()))
            cur.execute(resolve_sql('TRUNCATE horizon.users,horizon.sessions,horizon.progression,horizon.gameplay_events,horizon.monetization,horizon.acquisition,horizon.content_exposure,horizon.run_metadata'))
        elif args.action == 'load':
            for table in TABLES:
                with cur.copy(resolve_sql(f'COPY horizon.{table} FROM STDIN WITH (FORMAT CSV, HEADER TRUE)')) as copy:
                    with (OUT / 'staging' / f'{table}.csv').open('rb') as stream:
                        while block := stream.read(1024 * 1024):
                            copy.write(block)
        else:
            cur.executemany(resolve_sql('INSERT INTO horizon.run_metadata VALUES(%s,%s) ON CONFLICT(key) DO UPDATE SET value=excluded.value'),
                            [('users', str(args.users)), ('seed', str(args.seed)), ('generator', 'Wolfram Language'), ('status', 'generated')])
            for table in TABLES:
                cur.execute(resolve_sql(f'ANALYZE horizon.{table}'))

if __name__ == '__main__':
    main()
