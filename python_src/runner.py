"""One stage/engine/scale contract for Windows, Linux and macOS entrypoints."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
import uuid
from datetime import datetime, timezone

WARNING = 'Python 生成的数据不保证与 Wolfram 生成的数据逐条相同，亦不能预先保证由不同数据得出的数值结论一致；但必须满足同一项目的数据契约及独立可复现要求。'


def parse_args(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    scale=parser.add_mutually_exclusive_group(required=True)
    scale.add_argument('--fast',action='store_true');scale.add_argument('--full',action='store_true')
    engine=parser.add_mutually_exclusive_group()
    engine.add_argument('--python-only',action='store_true');engine.add_argument('--wolfram-only',action='store_true')
    stage=parser.add_mutually_exclusive_group()
    stage.add_argument('--generate-only',action='store_true');stage.add_argument('--analyze-only',action='store_true')
    values=list(sys.argv[1:] if argv is None else argv)
    for option in ['--fast','--full','--python-only','--wolfram-only','--generate-only','--analyze-only']:
        if values.count(option)>1:parser.error(f'{option} cannot be repeated')
    return parser.parse_args(values)


def wolfram_command():
    path=os.environ.get('HORIZON_WOLFRAMSCRIPT') or shutil.which('wolframscript')
    if not path:raise RuntimeError('Wolfram CLI is missing')
    command=[path]
    if os.environ.get('HORIZON_WOLFRAM_KERNEL'):command+=['-local',os.environ['HORIZON_WOLFRAM_KERNEL']]
    return command


def probe_wolfram():
    try:
        result=subprocess.run(wolfram_command()+['-code','Print["HORIZON_WOLFRAM_READY"]'],capture_output=True,text=True,encoding='utf8',errors='replace',timeout=45)
        return result.returncode==0 and 'HORIZON_WOLFRAM_READY' in result.stdout
    except (RuntimeError,OSError,subprocess.TimeoutExpired):return False


def select_plan(args, probe=probe_wolfram):
    engine='python' if args.python_only else 'wolfram' if args.wolfram_only else 'dual'
    warnings=[]
    if args.generate_only:
        if args.python_only or args.wolfram_only:warnings.append('语言参数在 GenerateOnly 模式下被忽略 / language parameter ignored')
        generator='Wolfram' if probe() else 'Python'
        if generator=='Python':warnings.append(WARNING)
    else:
        if engine!='python' and not probe():
            scale='Full' if args.full else 'Fast'
            raise RuntimeError(f'Wolfram CLI/kernel/license unavailable. Use: .\\run_all.ps1 -{scale} -PythonOnly'+(' -AnalyzeOnly' if args.analyze_only else '')+f' (Unix: ./run_all.sh --{scale.lower()} --python-only)')
        generator=None if args.analyze_only else 'Python' if engine=='python' else 'Wolfram'
    return dict(engine=engine,generator=generator,scale='full' if args.full else 'fast',stage='generate' if args.generate_only else 'analyze' if args.analyze_only else 'complete',warnings=warnings)


def execute(plan):
    from .config import ROOT, OUT, ARTIFACT_ROOT, CONFIG
    from .database import connect, schema_name, save_json
    from . import dataset
    from .validation import fingerprint
    from psycopg import sql
    run_id=os.environ['HORIZON_RUN_ID'];started=time.monotonic()
    record=dict(run_id=run_id,**plan,status='RUNNING',started_at=datetime.now(timezone.utc).isoformat(),
                code_sha256=fingerprint(),input_dataset_sha256=None,stages={},artifacts=[],
                engines={'python':'NOT RUN','wolfram':'NOT RUN'},release_status='NOT ASSESSED')
    local=ROOT/'.local/runs';local.mkdir(parents=True,exist_ok=True)
    def persist():
        save_json(ARTIFACT_ROOT/'run.json',record);save_json(local/f'{run_id}.json',record)
    def stage(name, function):
        record['stages'][name]='RUNNING';persist()
        try: result=function()
        except Exception:
            record['stages'][name]='FAIL';persist();raise
        record['stages'][name]='PASS';persist();return result
    def command(name,argv):
        def call():
            with (ARTIFACT_ROOT/f'{name}.log').open('w',encoding='utf8') as log:
                process=subprocess.Popen(argv,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf8',errors='replace')
                for line in process.stdout:print(line,end='',flush=True);log.write(line);log.flush()
                code=process.wait()
            if code:raise RuntimeError(f'{name} failed with exit code {code}; see {name}.log')
        return stage(name,call)
    guard=None
    target=schema_name();build=target[:25]+'_build_'+run_id.replace('-','')[:12]
    os.environ['HORIZON_USERS']=str(CONFIG['fast_users' if plan['scale']=='fast' else 'users'])
    persist()
    try:
        guard=stage('database_connection',connect)
        locked=guard.execute('SELECT pg_try_advisory_lock(hashtext(%s))',(f'project_horizon:{target}',)).fetchone()[0]
        if not locked:raise RuntimeError('Another run holds this dataset; retry when it completes')
        guard.commit()
        if plan['generator']:
            exists=guard.execute('SELECT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname=%s)',(target,)).fetchone()[0];guard.commit()
            allow_replace=os.environ.get('HORIZON_ALLOW_REPLACE')=='1'
            if exists and not allow_replace:raise RuntimeError('Target schema exists. Choose a new HORIZON_DB_SCHEMA, or explicitly authorize backup-and-replacement with HORIZON_ALLOW_REPLACE=1')
            os.environ['HORIZON_DB_SCHEMA']=build
            if plan['generator']=='Python':
                from .generate import generate
                stage('generation',lambda:generate(int(os.environ['HORIZON_USERS'])))
            else:command('generation',wolfram_command()+['-script','wolfram/generate.wls'])
            manifest=stage('dataset_integrity',lambda:dataset.register(plan['scale'],plan['generator'],run_id))
            record['backup_schema']=stage('dataset_publish',lambda:dataset.publish(build,target,run_id,allow_replace))
            os.environ['HORIZON_DB_SCHEMA']=target
            manifest['location']['schema']=target
            with connect() as con:
                con.execute(sql.SQL("UPDATE {}.run_metadata SET value=%s WHERE key='dataset_manifest'").format(sql.Identifier(target)),(json.dumps(manifest),))
        for table in list(dataset.TABLE_KEYS)+['run_metadata']:
            guard.execute(sql.SQL('LOCK TABLE {}.{} IN SHARE MODE').format(sql.Identifier(target),sql.Identifier(table)))
        manifest=stage('dataset_validation',lambda:dataset.validate(plan['scale'],guard))
        save_json(OUT/'dataset_manifest.json',manifest)
        record['input_dataset_sha256']=manifest['dataset_sha256']
        record['dataset_location']=manifest['location'];record['row_counts']=manifest['row_counts']
        record['generator']=manifest['generator']
        save_json(OUT/'metrics/generation.json',dict(users=manifest['actual_users'],seed=manifest['seed'],generator=manifest['generator'],sessions=manifest['row_counts']['sessions'],events=manifest['row_counts']['gameplay_events'],transactions=manifest['row_counts']['monetization']))
        save_json(OUT/'parity/status.json',dict(status='SKIPPED',reason='GenerateOnly: no analysis' if plan['stage']=='generate' else 'Only one analysis engine selected') if plan['engine']!='dual' or plan['stage']=='generate' else dict(status='PENDING'))
        if plan['stage']=='generate':
            for name in ['python_analysis','wolfram_analysis','parity','reports','tests']:record['stages'][name]='SKIPPED'
            certificate_scope='dataset_generation'
        else:
            if plan['engine']!='python':
                command('wolfram_analysis',wolfram_command()+['-script','wolfram/run_all.wls','--users',os.environ['HORIZON_USERS'],'--analyze'])
                record['engines']['wolfram']='PASS'
            else:record['stages']['wolfram_analysis']='SKIPPED'
            if plan['engine']!='wolfram':
                argv=[sys.executable,'-m','python_src.pipeline']
                if plan['engine']=='python':argv+=['--python-only']
                command('python_analysis',argv);record['engines']['python']='PASS'
            else:
                record['stages']['python_analysis']='SKIPPED'
                stage('wolfram_presentation',wolfram_presentation)
            if plan['engine']=='dual':
                parity=json.loads((OUT/'parity/status.json').read_text());assert parity['status']=='PASS'
                record['stages']['parity']='PASS';record['parity']=parity
                from .presentation import pdf
                stage('pdf',pdf)
            else:record['stages']['parity']='SKIPPED'
            if plan['engine']!='python':
                command('wolfram_selftest',wolfram_command()+['-script','wolfram/selftest.wls'])
            else:record['stages']['wolfram_selftest']='SKIPPED'
            if plan['engine']!='wolfram':command('notebook',[sys.executable,'-m','python_src.validation','notebook'])
            else:record['stages']['notebook']='SKIPPED'
            os.environ['HORIZON_DATASET_LOCKED']='1'
            command('tests',[sys.executable,'-m','pytest','--junitxml='+str(OUT/'metrics/pytest.xml')])
            from .portfolio import generate_presentation
            from .presentation import pdf
            stage('portfolio_provenance',lambda:generate_presentation('python' if plan['engine']=='python' else 'wolfram',plan['engine']=='dual'))
            stage('final_pdf',pdf)
            from .mode_validation import verify
            record['validation']=stage('output_validation',lambda:verify(plan['engine']))
            stage('dataset_unchanged',lambda:dataset.validate(plan['scale'],guard))
            certificate_scope={'python':'python_only','wolfram':'wolfram_only','dual':'dual_engine'}[plan['engine']]
        if fingerprint()!=record['code_sha256']:raise RuntimeError('Source changed during execution; retain this failed run and repeat against the final source')
        record['stages']['code_unchanged']='PASS'
        record['status']='PASS';record['certificate_scope']=certificate_scope
        record['completed_at']=datetime.now(timezone.utc).isoformat()
        record['duration_seconds']=round(time.monotonic()-started,3)
        import hashlib
        for path in sorted(ARTIFACT_ROOT.rglob('*')):
            if path.is_file() and path.name!='run.json' and 'staging' not in path.parts:
                record['artifacts'].append(dict(path=path.relative_to(ARTIFACT_ROOT).as_posix(),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        from .provenance import ALGORITHM
        save_json(OUT/'validation/certificate.json',dict(status='PASS',fingerprint_algorithm=ALGORITHM,scope=certificate_scope,scale=plan['scale'],run_id=run_id,code_sha256=record['code_sha256'],dataset_sha256=record['input_dataset_sha256'],stages=record['stages'],validation=record.get('validation'),parity=record['stages']['parity'],executed_at=record['completed_at']))
        print(f'{certificate_scope} PASS; run report: {ARTIFACT_ROOT / "run.json"}',flush=True)
        return 0
    except Exception as error:
        record['status']='FAIL';record['error']=str(error);record['completed_at']=datetime.now(timezone.utc).isoformat()
        traceback.print_exc();return 1
    finally:
        os.environ['HORIZON_DB_SCHEMA']=target
        if guard:guard.rollback();guard.close()
        persist()


def wolfram_presentation():
    from . import report, visualization
    from .presentation import assets, pdf
    report.generate('wolfram',False)
    visualization.generate('wolfram',False);assets('wolfram');pdf()


def main(argv=None):
    args=parse_args(argv)
    root=Path(__file__).resolve().parents[1]
    if (root/'.env').exists():
        for line in (root/'.env').read_text(encoding='utf-8-sig').splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                key,value=line.split('=',1);os.environ.setdefault(key.strip(),value.strip())
    os.environ['HORIZON_PYTHON']=sys.executable;os.environ.setdefault('PYTHONIOENCODING','utf-8')
    for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ.setdefault(key,'4')
    try:plan=select_plan(args)
    except RuntimeError as error:print(str(error),file=sys.stderr);return 1
    for warning in plan['warnings']:print('WARNING: '+warning,flush=True)
    print(f'Scale: {plan["scale"]}; stage: {plan["stage"]}; analysis: {plan["engine"]}; selected generator: {plan["generator"]}',flush=True)
    run_id=str(uuid.uuid4());artifact=root/'outputs/runs'/run_id;artifact.mkdir(parents=True)
    (artifact/'wolfram').mkdir();(artifact/'notebooks').mkdir()
    os.environ['HORIZON_RUN_ID']=run_id;os.environ['HORIZON_ARTIFACT_ROOT']=str(artifact)
    os.environ['HORIZON_OUTPUT_DIR']=str(artifact/'outputs');os.environ['HORIZON_ANALYSIS_MODE']=plan['engine']
    try:return execute(plan)
    except ModuleNotFoundError as error:
        lock=root/'requirements-lock.txt'
        if os.name=='nt':
            command="& '"+sys.executable.replace("'","''")+"' -m pip install -r '"+str(lock).replace("'","''")+"'"
        else:
            import shlex
            command=shlex.quote(sys.executable)+' -m pip install -r '+shlex.quote(str(lock))
        print(f'Python dependency missing: {error.name}. Selected interpreter: {sys.executable}\nInstall project dependencies with:\n{command}',file=sys.stderr)
        return 1


if __name__=='__main__':sys.exit(main())
