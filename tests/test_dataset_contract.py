"""Deterministic Python facts and manifest rejection paths without a database."""
import json
import pytest
from python_src.generate import player
from python_src import dataset

def test_same_seed_exact_rows_different_seed_changes():
    def run(seed):return player(1,seed,dict(sessions=0,gameplay_events=0,monetization=0))
    assert run(20261005)==run(20261005);assert run(20261005)!=run(20261006)

def test_player_business_contract():
    for uid in range(1,101):
        rows=player(uid,20261005,dict(sessions=0,gameplay_events=0,monetization=0));registration=rows['users'][0][1]
        assert rows['sessions'][0][2]==registration
        assert all(s[4]>0 and s[2]>=registration for s in rows['sessions'])
        chapters=[p[2] for p in rows['progression']];assert chapters==sorted(chapters)
        assert all(0<=p[7]<=p[6] for p in rows['progression'])

@pytest.mark.parametrize('mutation',['missing','scale','status','schema_version','schema','data'])
def test_analyze_only_rejects_invalid_manifests(monkeypatch,mutation):
    m=dict(status='COMPLETE',scale='fast',expected_users=20000,schema_version=dataset.SCHEMA_VERSION,schema={},dataset_sha256='correct',row_counts={'users':20000})
    if mutation in ['scale','status','schema_version']:m[mutation]='wrong'
    class Result:
        def __init__(self,value):self.value=value
        def fetchone(self):return self.value
    class Con:
        def execute(self,statement,params=None):return Result((None,) if mutation=='missing' else ('exists',)) if 'to_regclass' in statement else Result((json.dumps(m),))
    monkeypatch.setattr(dataset,'structure',lambda con:{'changed':True} if mutation=='schema' else {})
    monkeypatch.setattr(dataset,'checks',lambda *a:{})
    monkeypatch.setattr(dataset,'content',lambda con:dict(dataset_sha256='changed' if mutation=='data' else 'correct',row_counts={'users':20000}))
    with pytest.raises(ValueError):dataset.validate('fast',Con())
