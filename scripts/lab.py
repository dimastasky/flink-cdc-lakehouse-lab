#!/usr/bin/env python3
"""Small host-side command runner. No credentials in command arguments/log output."""
import json, os, platform, secrets, shutil, socket, subprocess, sys, time, urllib.request
from pathlib import Path
from string import Template
ROOT=Path(__file__).resolve().parents[1]
def read_env(path):
    return dict(line.split('=',1) for line in path.read_text().splitlines() if line and not line.startswith('#'))
def environment():
    result=dict(os.environ); result.update(read_env(ROOT/'versions.env'))
    if (ROOT/'.env').exists():
        for k,v in read_env(ROOT/'.env').items():result.setdefault(k,v)
    result.setdefault('LAB_STATE_DIR',str(ROOT/'.runtime'))
    return result
def compose(*args,capture=False,timeout=600,check=True,input=None):
    cmd=['docker','compose','--env-file',str(ROOT/'versions.env'),'--env-file',str(ROOT/'.env'),'-f',str(ROOT/'compose.yaml'),*args]
    if os.getenv('E2E_RUN_ID'):
        state=Path(environment()['LAB_STATE_DIR']);state.mkdir(parents=True,exist_ok=True)
        with (state/'commands.jsonl').open('a') as log:log.write(json.dumps({'time':time.time(),'argv':cmd})+'\n')
    return subprocess.run(cmd,cwd=ROOT,env=environment(),text=True,input=input,capture_output=capture,timeout=timeout,check=check)
def poll(label,fn,timeout=240,interval=2):
    end=time.monotonic()+timeout;last=None
    while time.monotonic()<end:
        try:
            value=fn()
            if value:return value
        except AssertionError:raise
        except Exception as e:last=str(e)
        time.sleep(interval)
    raise TimeoutError(f'{label}: deadline {timeout}s exceeded; last={last}')
def http(path,port='FLINK_PORT'):
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(f'http://127.0.0.1:{environment()[port]}{path}',timeout=5) as r:return json.load(r)
def init():
    path=ROOT/'.env'
    if not path.exists():
        vals=read_env(ROOT/'.env.example')
        for k in vals:
            if 'PASSWORD' in k or k.endswith('SECRET_KEY'):vals[k]=secrets.token_hex(32)
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as f:f.write('\n'.join(k+'='+v for k,v in vals.items())+'\n')
    # Add new settings to existing labs without rotating their credentials.
    existing=read_env(path)
    missing={k:v for k,v in read_env(ROOT/'.env.example').items() if k not in existing}
    if missing:
        for k in missing:
            if 'PASSWORD' in k or k.endswith('SECRET_KEY'):missing[k]=secrets.token_hex(32)
        with path.open('a') as f:
            f.write('\n'+'\n'.join(k+'='+v for k,v in missing.items())+'\n')
    env=environment();state=Path(env['LAB_STATE_DIR']);(state/'config').mkdir(parents=True,exist_ok=True)
    for source,dest in [('flink-conf.yaml.template','flink-conf.yaml'),('gravitino.conf.template','gravitino.conf'),('trino-iceberg.properties.template','iceberg.properties')]:
        # Secrets generated here are hex; reject config injection from manually edited environment.
        for k,v in env.items():
            if k.endswith('PASSWORD') or k in ('S3_ACCESS_KEY','S3_SECRET_KEY'):
                if not v or any(ch not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for ch in v):raise ValueError(k+': use alphanumeric/_/- local credential')
        rendered=Template((ROOT/'config'/source).read_text()).substitute(env)
        (state/'config'/dest).write_text(rendered)
    print('Initialized local config:',state)
def superset_up():
    init()
    env=environment()
    compose('--profile','bi','build','superset',timeout=3600)
    compose('--profile','bi','up','-d','--wait','--wait-timeout','180','superset-db','postgres-oltp','trino')
    # A separate SELECT-only user connects Superset to the OLTP database.
    # Send the credential on stdin; never put it into command arguments/logs.
    password=env['SUPERSET_BI_PASSWORD']
    if not password or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in password):
        raise ValueError('SUPERSET_BI_PASSWORD: use alphanumeric/_/- credential')
    sql="""SELECT 'CREATE ROLE lab_bi LOGIN' WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname='lab_bi') \\gexec
ALTER ROLE lab_bi LOGIN PASSWORD '%s';
GRANT CONNECT ON DATABASE payments TO lab_bi;
GRANT USAGE ON SCHEMA public TO lab_bi;
GRANT SELECT ON customers,accounts,payments TO lab_bi;
ALTER ROLE lab_bi SET default_transaction_read_only=on;
""" % password
    compose('exec','-T','postgres-oltp','psql','-X','-U','postgres','-d','payments','-v','ON_ERROR_STOP=1','-q','-f','-',input=sql,capture=True)
    compose('--profile','bi','run','--rm','superset-init',timeout=600)
    compose('--profile','bi','up','-d','--wait','--wait-timeout','240','superset')
    url='http://127.0.0.1:'+env['SUPERSET_PORT']
    state=Path(env['LAB_STATE_DIR']);state.mkdir(parents=True,exist_ok=True)
    login=state/'superset-login.txt'
    fd=os.open(login,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    os.fchmod(fd,0o600)
    with os.fdopen(fd,'w') as f:
        f.write('URL: '+url+'\nUsername: '+env['SUPERSET_ADMIN_USERNAME']+'\nPassword: '+env['SUPERSET_ADMIN_PASSWORD']+'\n')
    print('Superset ready:',url)
    print('Login credentials:',login)
def superset_status():
    compose('--profile','bi','ps','superset','superset-db')
    env=environment();base='http://127.0.0.1:'+env['SUPERSET_PORT']
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(base+'/health',timeout=5) as response:
        print('Superset health:',response.read().decode().strip())
    payload=json.dumps({'username':env['SUPERSET_ADMIN_USERNAME'],
                        'password':env['SUPERSET_ADMIN_PASSWORD'],'provider':'db'}).encode()
    request=urllib.request.Request(base+'/api/v1/security/login',data=payload,
                                   headers={'Content-Type':'application/json'})
    with opener.open(request,timeout=15) as response:
        token=json.load(response)['access_token']
    for resource in ('database','dataset'):
        request=urllib.request.Request(base+'/api/v1/'+resource+'/',
                                       headers={'Authorization':'Bearer '+token})
        with opener.open(request,timeout=15) as response:
            result=json.load(response)
        print('Superset '+resource+' count:',result['count'])
def doctor():
    print('Host:',platform.system(),platform.machine());subprocess.run(['docker','compose','version'],check=True)
    r=subprocess.run(['docker','info','--format','{{json .}}'],text=True,capture_output=True,check=True);info=json.loads(r.stdout)
    print('Docker:',info['Architecture'],'CPUs:',info['NCPU'],'memory GiB:',round(info['MemTotal']/2**30,2))
    print('Estimated baseline: 6–8 GiB Docker RAM, 4 CPU, 12 GiB free disk; stress: 12 GiB RAM.')
    print('Disk free GiB:',round(shutil.disk_usage(ROOT).free/2**30,2))
    env=environment()
    for k in ('PG_PORT','MINIO_PORT','MINIO_CONSOLE_PORT','CATALOG_PORT','FLINK_PORT','TRINO_PORT'):
        with socket.socket() as s:
            try:s.bind(('127.0.0.1',int(env.get(k,read_env(ROOT/'.env.example')[k]))));print(k,'free')
            except OSError:print(k,'occupied (may be this lab; inspect make status)')
    for k,v in read_env(ROOT/'versions.env').items():
        if k.endswith('_IMAGE'):
            r=subprocess.run(['docker','buildx','imagetools','inspect',v],capture_output=True,text=True,timeout=90)
            print(k,'available' if r.returncode==0 else 'UNAVAILABLE: '+r.stderr.strip())
            if r.returncode:raise RuntimeError('Image unavailable: '+k)
def up():
    # Catalog must not race user/bucket creation.
    compose('up','-d','--wait','--wait-timeout','180','postgres-oltp','postgres-catalog','minio')
    compose('run','--rm','minio-init',timeout=180)
    compose('up','-d','--wait','--wait-timeout','240','gravitino-iceberg-rest','flink-jobmanager','flink-taskmanager','trino')
    poll('registered task slots',lambda:http('/overview')['slots-total']>=int(environment()['PARALLELISM']))
def bootstrap():
    compose('exec','-T','postgres-oltp','psql','-U','postgres','-d','payments','-f','/sql/bootstrap.sql')
    compose('run','--rm','minio-init',timeout=180)
    compose('run','--rm','bootstrap',timeout=240)
    # The tables are loaded via REST and S3FileIO by the bootstrap Java client.
    from verify import query
    poll('Trino catalog',lambda:query('SHOW SCHEMAS FROM iceberg'),timeout=180)
    query('CREATE SCHEMA IF NOT EXISTS iceberg.lab_checks')
    query("CREATE TABLE IF NOT EXISTS iceberg.lab_checks.v2_probe (id BIGINT, amount DECIMAL(18,2)) WITH (format='PARQUET', format_version=2)")
    query('DELETE FROM iceberg.lab_checks.v2_probe')
    query('INSERT INTO iceberg.lab_checks.v2_probe VALUES (1, 12.34), (2, 2.00)')
    query('UPDATE iceberg.lab_checks.v2_probe SET amount=42.37 WHERE id=1')
    query('DELETE FROM iceberg.lab_checks.v2_probe WHERE id=2')
    rows=query('SELECT id, CAST(amount AS VARCHAR) AS amount FROM iceberg.lab_checks.v2_probe')
    if rows != [{'id':1,'amount':'42.37'}]:raise AssertionError('Independent Trino v2 CRUD probe failed: '+str(rows))
    print('Trino Iceberg v2 CRUD probe passed; Flink equality deletes are verified separately in E2E.')
def generate(mode='continuous'):
    e=environment();compose('run','--rm','workload-generator','--mode',mode,'--seed',e['SEED'],'--rate',e['RATE'],'--duration',e['DURATION'],'--batch-size',e['BATCH_SIZE'],timeout=int(e['DURATION'])+180)
def status():
    compose('ps');jobs=http('/jobs/overview');print(json.dumps(jobs,indent=2))
    for job in jobs['jobs']:
        if job['name']=='postgres-to-iceberg-current':
            print(json.dumps(http('/jobs/'+job['jid']+'/checkpoints'),indent=2))
            from metrics import collect
            print(json.dumps(collect(job['jid']),indent=2))
    compose('exec','-T','postgres-oltp','psql','-U','postgres','-d','payments','-f','/sql/diagnostics.sql')
    from verify import query
    for table in ('customers','accounts','payments'):
        print(table,query(f'SELECT snapshot_id,committed_at,summary FROM iceberg.oltp_mirror."{table}_current$snapshots" ORDER BY committed_at DESC LIMIT 1'))
        print(table,query(f'SELECT content,count(*) AS files,sum(file_size_in_bytes) AS bytes FROM iceberg.oltp_mirror."{table}_current$files" GROUP BY content'))
def main():
    action=sys.argv[1] if len(sys.argv)>1 else 'status'
    if action=='init':return init()
    if action=='doctor':return doctor()
    if action=='superset-up':return superset_up()
    if not (ROOT/'.env').exists():raise RuntimeError('Run make init first')
    if action=='build':
        from fetch_artifacts import fetch
        fetch();compose('--profile','tools','build','flink-jobmanager','workload-generator','job-submitter','gravitino-iceberg-rest','minio','minio-init',timeout=3600)
    elif action=='up':up()
    elif action=='bootstrap':bootstrap()
    elif action=='seed':generate('seed')
    elif action=='generate':generate()
    elif action=='finite':generate('finite')
    elif action in ('submit','savepoint','restore','stop-with-savepoint'):
        compose('run','--rm','job-submitter','stop' if action=='stop-with-savepoint' else action,timeout=360)
    elif action=='status':status()
    elif action=='superset-status':superset_status()
    elif action=='superset-down':compose('--profile','bi','stop','superset','superset-db')
    elif action=='query':
        from verify import query
        sql=(ROOT/'sql/trino/analytics.sql').read_text()
        for statement in sql.split(';'):
            if statement.strip():print(statement,query(statement))
    elif action=='reconcile':
        from verify import reconcile
        reconcile()
    elif action=='demo':
        up();bootstrap();generate('seed');compose('run','--rm','job-submitter',timeout=360)
        from verify import reconcile
        reconcile();generate('finite');reconcile()
        print('Demo complete: snapshot + finite CRUD reconciled. Generator stopped.')
    elif action=='logs':compose('logs','--no-color','--tail','200')
    elif action=='down':compose('--profile','bi','down','--timeout','30')
    elif action=='reset':
        if os.getenv('CONFIRM')!='YES':raise RuntimeError('Use make reset CONFIRM=YES. Deletes this project tables, slots, MinIO checkpoints/savepoints and catalog.')
        project=environment()['COMPOSE_PROJECT_NAME']
        if not project.startswith('flink-cdc-lakehouse-lab'):raise RuntimeError('Refusing reset outside lab project prefix')
        compose('--profile','tools','--profile','bi','down','--volumes','--remove-orphans','--timeout','30')
        state=Path(environment()['LAB_STATE_DIR']).resolve()
        if not state.is_relative_to(ROOT/'.runtime'):raise RuntimeError('Unexpected state directory')
        shutil.rmtree(state,ignore_errors=True);init()
    else:raise ValueError('Unknown action: '+action)
if __name__=='__main__':main()
