"""Explicitly separate current mode checks from cross-engine/release checks."""
import os
import pytest

def pytest_collection_modifyitems(items):
    mode=os.environ.get('HORIZON_ANALYSIS_MODE')
    if not mode:return
    cross={'test_wolfram_seed_and_compiled_state','test_experiment_primary_and_independent_power','test_gate_experiment_eligibility_and_independent_power'}
    historical={'test_markdown_report_consistency','test_readme_links_and_current_model_narrative','test_figures_and_portfolio'}
    for item in items:
        file=item.path.name;reason=None
        if os.environ.get('HORIZON_DATASET_LOCKED')=='1' and item.name in {'test_future_mutation_cannot_change_early_minutes','test_drop_and_create_sql_transactionally'}:reason='Run holds SHARE locks; mutation regressions run separately after analysis'
        elif file=='test_release.py' or item.name in historical:reason='Release/historical checks run separately; current outputs verified by mode_validation'
        elif mode!='dual' and (item.name in cross or file=='test_wolfram_python_parity.py'):reason='Cross-engine comparison requires both current analysis engines'
        elif mode=='wolfram' and (file in {'test_no_leakage.py','test_python_acceptance.py'} or item.name in {'test_labels_from_separate_sql','test_classification_counts_and_metrics','test_multi_session_observation_semantics'}):reason='Python-specific analysis is not selected'
        if reason:item.add_marker(pytest.mark.skip(reason=reason))
