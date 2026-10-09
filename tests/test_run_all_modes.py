"""Shared contract and actual wrapper dispatch without Wolfram."""
import itertools
import os
from pathlib import Path
import shutil
import subprocess
import pytest
from python_src.runner import parse_args, select_plan, probe_wolfram
ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('flags',[[],['--fast','--full'],['--fast','--fast'],['--fast','--python-only','--wolfram-only'],['--full','--generate-only','--analyze-only']])
def test_invalid_shared_cli(flags):
    with pytest.raises(SystemExit) as error:parse_args(flags)
    assert error.value.code==2

@pytest.mark.parametrize('scale,engine,stage',list(itertools.product(['--fast','--full'],['','--python-only','--wolfram-only'],['','--generate-only','--analyze-only'])))
@pytest.mark.parametrize('available',[True,False])
def test_routing_matrix(scale,engine,stage,available):
    calls=[]
    def probe():calls.append(True);return available
    args=parse_args([x for x in [scale,engine,stage] if x])
    if not available and engine!='--python-only' and stage!='--generate-only':
        with pytest.raises(RuntimeError,match='PythonOnly'):select_plan(args,probe)
        return
    plan=select_plan(args,probe);assert plan['scale']==scale[2:]
    if stage=='--generate-only':
        assert plan['generator']==('Wolfram' if available else 'Python')
        assert any('ignored' in x for x in plan['warnings'])==bool(engine)
        assert any('逐条相同' in x for x in plan['warnings'])==(not available)
        assert len(calls)==1
    elif engine=='--python-only':
        assert not calls
        assert plan['generator']==(None if stage=='--analyze-only' else 'Python')
    else:assert len(calls)==1

def test_probe_checks_actual_kernel_output(monkeypatch):
    monkeypatch.setattr('python_src.runner.wolfram_command',lambda:['mock'])
    class Result: returncode=0;stdout='installed but not licensed'
    monkeypatch.setattr(subprocess,'run',lambda *a,**k:Result())
    assert not probe_wolfram()
    Result.stdout='HORIZON_WOLFRAM_READY';assert probe_wolfram()
    Result.returncode=1;assert not probe_wolfram()

@pytest.mark.skipif(not shutil.which('pwsh'),reason='PowerShell unavailable')
@pytest.mark.parametrize('flags,expected',[
    (['-Fast','-PythonOnly'],['--fast','--python-only']),
    (['-Full','-WolframOnly','-AnalyzeOnly'],['--full','--wolfram-only','--analyze-only']),
    (['-Fast','-GenerateOnly','-PythonOnly'],['--fast','--python-only','--generate-only'])])
def test_powershell_wrapper(tmp_path,flags,expected):
    shutil.copy2(ROOT/'run_all.ps1',tmp_path/'run_all.ps1')
    wrapper=tmp_path/'wrapper.ps1'
    wrapper.write_text("function global:mockPython { $args | ConvertTo-Json -Compress; $global:LASTEXITCODE=17 }; $env:HORIZON_PYTHON='mockPython'; & \"$PSScriptRoot/run_all.ps1\" @args; exit $LASTEXITCODE",encoding='utf8')
    result=subprocess.run(['pwsh','-NoProfile','-File',str(wrapper),*flags],capture_output=True,text=True,encoding='utf8')
    import json
    assert result.returncode==17
    assert json.loads(result.stdout)==['-m','python_src.runner',*expected]

@pytest.mark.skipif(not shutil.which('pwsh'),reason='PowerShell unavailable')
@pytest.mark.parametrize('output_codepage',[None,65001,936],ids=['default','utf8','cp936'])
@pytest.mark.parametrize('flags',[[],['-Fast','-Full'],['-Fast','-Fast'],['-Fast','-PythonOnly','-WolframOnly'],['-Full','-GenerateOnly','-AnalyzeOnly']])
def test_powershell_parameter_errors_before_dispatch(tmp_path,flags,output_codepage):
    shutil.copy2(ROOT/'run_all.ps1',tmp_path/'run_all.ps1')
    env=os.environ.copy();env['HORIZON_PYTHON']='must_not_be_invoked'
    command=['pwsh','-NoProfile','-File',str(tmp_path/'run_all.ps1'),*flags]
    if output_codepage is not None:
        script=str(tmp_path/'run_all.ps1').replace("'","''")
        command=['pwsh','-NoProfile','-Command',
                 f"[Console]::OutputEncoding=[System.Text.Encoding]::GetEncoding({output_codepage}); & '{script}' "+' '.join(flags)]
    # Localized PowerShell errors need not be UTF-8. Inspect the ASCII sentinel
    # in raw bytes so a reader-thread decode error cannot hide dispatch failures.
    result=subprocess.run(command,env=env,capture_output=True)
    assert result.returncode!=0
    assert result.stderr.strip(), 'PowerShell must report the parameter error'
    assert b'must_not_be_invoked' not in result.stdout+result.stderr
    assert len(list(tmp_path.iterdir()))==1

def test_python_mode_never_probes_wolfram():
    def forbidden():pytest.fail('PythonOnly checked Wolfram')
    plan=select_plan(parse_args(['--full','--python-only']),forbidden)
    assert plan['engine']=='python' and plan['generator']=='Python'


def bash_path():
    candidate=Path(os.environ.get('ProgramFiles',''))/'Git/bin/bash.exe'
    return str(candidate) if candidate.is_file() else shutil.which('bash')


@pytest.mark.skipif(not bash_path(),reason='Bash unavailable on this host')
@pytest.mark.parametrize('flags',[
    ['--fast','--python-only'],['--full','--wolfram-only','--analyze-only'],
    ['--fast','--generate-only','--python-only'],['--full'],['--fast','--analyze-only']])
def test_shell_wrapper(tmp_path,flags):
    import json
    shutil.copy2(ROOT/'run_all.sh',tmp_path/'run_all.sh')
    package=tmp_path/'python_src';package.mkdir();(package/'__init__.py').write_text('')
    (package/'runner.py').write_text('import sys,json;print(json.dumps(sys.argv[1:]));sys.exit(19)',encoding='utf8')
    env=os.environ.copy();env['HORIZON_PYTHON']=str(Path(__import__('sys').executable).as_posix())
    result=subprocess.run([bash_path(),'./run_all.sh',*flags],cwd=tmp_path,env=env,capture_output=True,text=True,encoding='utf8')
    assert result.returncode==19,result.stderr
    assert json.loads(result.stdout)==flags
def test_auc_comparison_reports_negative_gain_honestly():
    from python_src.portfolio import auc_comparison
    assert '低 0.004936' in auc_comparison(-.004936)
    assert '高 0.004936' in auc_comparison(.004936)
    assert '几乎没有变化' in auc_comparison(-.004936)
def test_missing_dependency_reports_selected_interpreter_and_install_command(tmp_path,monkeypatch,capsys):
    from python_src import runner
    monkeypatch.setattr(runner,'__file__',str(tmp_path/'python_src/runner.py'))
    monkeypatch.setattr(runner.os,'environ',dict(runner.os.environ))
    def missing(plan):raise ModuleNotFoundError("No module named 'yaml'",name='yaml')
    monkeypatch.setattr(runner,'execute',missing)
    assert runner.main(['--fast','--python-only'])==1
    message=capsys.readouterr().err
    assert 'dependency missing: yaml' in message
    assert runner.sys.executable in message and 'pip install -r' in message and 'requirements-lock.txt' in message
