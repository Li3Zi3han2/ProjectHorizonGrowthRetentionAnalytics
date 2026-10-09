"""Generator provenance and actual seeded Wolfram self-tests."""
import json
from python_src.config import OUT
from python_src.database import query

def test_generator_provenance():
    meta=query('SELECT key,value FROM horizon.run_metadata').set_index('key').value
    assert meta['generator'] in {'Wolfram Language','Python'}
    assert int(meta['seed'])==20261005
    assert int(meta['users'])==int(query('SELECT count(*) FROM horizon.users').iloc[0,0])

def test_wolfram_seed_and_compiled_state():
    result=json.loads((OUT/'metrics/wolfram_selftest.json').read_text())
    assert result['same_seed_same_simulation']
    assert result['different_seed_changes_simulation']
    assert result['no_progression_regression']
    assert result['positive_session_minutes']
    assert result['notebook_input_cells_executed']>=7

def test_all_expected_facts_present():
    for table in ['users','sessions','progression','gameplay_events','monetization','acquisition','content_exposure']:
        assert query(f'SELECT count(*) FROM horizon.{table}').iloc[0,0]>0
