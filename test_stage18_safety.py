from pathlib import Path
import ast
import yaml

def test_manual_only_and_read_only():
    w=yaml.load(Path('.github/workflows/affiliate_v5_test.yml').read_text(),Loader=yaml.BaseLoader)
    assert set(w['on'])=={'workflow_dispatch'}
    assert w['permissions']=={'contents':'read','actions':'read'}
    assert w['on']['workflow_dispatch']['inputs']['run_live']['default']=='false'
    assert 'inputs.run_live == true' in w['jobs']['live-preview']['if']
    assert w['jobs']['live-preview']['needs']=='test-v5'
    for job in w['jobs'].values():
        assert 'feature-affiliate-v2-validation' in job['if']
        assert not job.get('permissions')
        for step in job['steps']:
            if 'checkout@' in step.get('uses',''): assert step['with']['persist-credentials']=='false'

def test_full_suite_in_ci():
    w=Path('.github/workflows/affiliate_v5_test.yml').read_text()
    assert 'pytest -q --junitxml=validation-results.xml' in w
    assert '--ignore=' not in w

def test_preview_write_guards():
    tree=ast.parse(Path('run_live_preview.py').read_text())
    guards={n.args[1].value for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='object' and len(n.args)==3 and isinstance(n.args[1],ast.Constant)}
    assert {'wp_draft','wp_review_gate_check','record_saved_draft','save_article','write_items'} <= guards

def test_no_wp_credentials_in_live_workflow():
    w=yaml.load(Path('.github/workflows/affiliate_v5_test.yml').read_text(),Loader=yaml.BaseLoader)
    for step in w['jobs']['live-preview']['steps']:
        assert not any(k.startswith('WP_') for k in step.get('env',{}))
