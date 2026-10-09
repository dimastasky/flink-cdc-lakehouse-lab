"""Ordered destructive tests, confined to the fresh per-run Compose project."""
import json,os,subprocess,threading,time
from pathlib import Path
from decimal import Decimal
import pytest
from lab import ROOT,compose,environment,generate,http,poll,bootstrap
from verify import pg,query,reconcile

def record(name,value):
    (Path(environment()['LAB_STATE_DIR'])/(name+'.json')).write_text(json.dumps(value,default=str,indent=2))
def submit(action='submit'):
    return compose('run','--rm','job-submitter',action,timeout=360)
def job():
    active=[j for j in http('/jobs/overview')['jobs'] if j['name']=='postgres-to-iceberg-current' and j['state'] not in ('FINISHED','CANCELED','FAILED','SUSPENDED')]
    assert len(active)==1;return active[0]['jid']
def checkpoint():
    data=http('/jobs/'+job()+'/checkpoints');record('checkpoints',data)
    return data.get('latest',{}).get('completed')
def snapshot():
    rows=query('SELECT snapshot_id FROM iceberg.oltp_mirror."payments_current$snapshots" ORDER BY committed_at DESC LIMIT 1')
    assert rows;record('snapshot',rows);return rows[0]['snapshot_id']
def new_payment():
    return int(pg("INSERT INTO payments(account_id,amount,currency,status,event_time) VALUES (1,12.34,'EUR','CREATED','2026-01-02T03:04:05.678Z') RETURNING payment_id").splitlines()[0])
def single(id):return query(f'SELECT * FROM iceberg.oltp_mirror.payments_current WHERE payment_id={id}')
def load_in_background(duration=30):
    env=environment();env.update(DURATION=str(duration),RATE='40')
    path=Path(env['LAB_STATE_DIR'])/('workload-'+str(time.time_ns())+'.log');stream=path.open('w')
    p=subprocess.Popen([sys_executable(),str(ROOT/'scripts/lab.py'),'generate'],env=env,stdout=stream,stderr=subprocess.STDOUT)
    return p,stream
def sys_executable():
    import sys
    return sys.executable

def raise_submit_or_wait(errors):
    if errors:raise AssertionError('Submit failed: '+str(errors[0]))
    return int(pg("SELECT count(*) FROM pg_stat_activity WHERE usename='lab_cdc' AND wait_event_type='Lock' AND query ILIKE '%payments%'",admin=True))>0

def test_01_A_G_snapshot_and_concurrent_changes():
    # Hold an explicit source-table lock until the CDC snapshot reader actually waits.
    env=environment();cmd=['docker','compose','--env-file',str(ROOT/'versions.env'),'--env-file',str(ROOT/'.env'),'-f',str(ROOT/'compose.yaml'),'exec','-T','postgres-oltp','psql','-X','-U','lab_app','-d','payments','-v','ON_ERROR_STOP=1','-At']
    lock=subprocess.Popen(cmd,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
    lock.stdin.write("BEGIN; LOCK TABLE payments IN ACCESS EXCLUSIVE MODE;\n\\echo locked\n");lock.stdin.flush()
    # Readiness is queried via pg_locks with a deadline; no blocking readline.
    thread_errors=[]
    def send():
        try:submit()
        except BaseException as e:thread_errors.append(e)
    worker=threading.Thread(target=send,daemon=True)
    try:
        poll('lock acquired',lambda:pg("SELECT count(*) FROM pg_locks WHERE relation='payments'::regclass AND mode='AccessExclusiveLock' AND granted",admin=True)=='1',timeout=30)
        worker.start()
        poll('CDC reader blocked during initial scan',lambda:raise_submit_or_wait(thread_errors),timeout=180)
        from metrics import collect
        record('snapshot-reader-metrics',collect(job()))
        lock.stdin.write("UPDATE payments SET amount=777.77 WHERE payment_id=1; DELETE FROM payments WHERE payment_id=2; INSERT INTO payments(account_id,amount,currency,status,event_time) VALUES (1,5.67,'EUR','CREATED','2026-01-01T00:00:00.321Z'); COMMIT;\n\\q\n");lock.stdin.flush();lock.communicate(timeout=30)
        worker.join(timeout=360);assert not worker.is_alive();assert not thread_errors,thread_errors
    finally:
        if lock.poll() is None:lock.kill();lock.wait(timeout=5)
    result=reconcile();assert result=={'customers':100,'accounts':200,'payments':10000}
    cp=poll('completed S3 checkpoint',checkpoint,timeout=180);assert cp['external_path'].startswith('s3://checkpoints/')
    record('snapshot-concurrent-mutations',{'updated':1,'deleted':2,'checkpoint':cp})
    assert single(1)[0]['amount'] in (Decimal('777.77'),'777.77')
    assert not single(2)

def test_02_B_C_D_small_v2_update_delete_time_travel():
    id=new_payment();start=time.monotonic();poll('insert visible',lambda:single(id));record('control-latency',{'seconds':time.monotonic()-start,'origin':'source commit acknowledged to Trino visible','paymentId':id})
    pg(f"UPDATE payments SET status='PENDING' WHERE payment_id={id}")
    poll('update without duplicate',lambda:len(single(id))==1 and single(id)[0]['status']=='PENDING')
    previous=snapshot();pg(f'DELETE FROM payments WHERE payment_id={id}')
    poll('delete visible',lambda:not single(id));assert query(f'SELECT payment_id FROM iceberg.oltp_mirror.payments_current FOR VERSION AS OF {previous} WHERE payment_id={id}')==[{'payment_id':id}]
    files=query('SELECT content,file_format FROM iceberg.oltp_mirror."payments_current$files"')
    assert files and all(f['file_format']=='PARQUET' for f in files)
    assert any(f['content']==2 for f in files),'Must exercise equality deletes from Flink upsert'
    reconcile()

def test_03_E_F_repeated_update_and_rollback():
    id=new_payment();poll('new payment',lambda:single(id))
    pg(f"UPDATE payments SET status='PENDING' WHERE payment_id={id}; UPDATE payments SET status='COMPLETED' WHERE payment_id={id}; UPDATE payments SET amount=19.99 WHERE payment_id={id};")
    reconcile();before=single(id)
    # Assert rollback absence after subsequent committed sentinel crossed the pipeline.
    pg(f"BEGIN; UPDATE payments SET amount=999.99 WHERE payment_id={id}; INSERT INTO customers(full_name,status) VALUES ('Rollback only','ACTIVE'); ROLLBACK;")
    sentinel=new_payment();poll('post rollback sentinel',lambda:single(sentinel));assert single(id)==before
    assert single(id)[0]['row_version']==4;reconcile()

def test_04_multi_table_transaction():
    generate('finite');reconcile()

def test_05_H_taskmanager_failure():
    poll('baseline checkpoint',checkpoint);before=checkpoint()['id'];versions=int(pg('SELECT sum(row_version) FROM payments'));p,stream=load_in_background()
    try:
        poll('load has committed',lambda:int(pg('SELECT sum(row_version) FROM payments'))>versions)
        compose('kill','-s','SIGKILL','flink-taskmanager');compose('up','-d','flink-taskmanager')
        assert p.wait(timeout=150)==0
    finally:
        if p.poll() is None:p.terminate();p.wait(timeout=45)
        stream.close()
    poll('checkpoint after recovery',lambda:checkpoint() and checkpoint()['id']>before,timeout=240);reconcile()

def test_06_I_stop_savepoint_restore():
    reconcile();old=job();submit('stop')
    saved=json.loads((Path(environment()['LAB_STATE_DIR'])/'savepoint.json').read_text());assert saved['stopped']
    assert http('/jobs/'+old)['state']=='FINISHED'
    # Commit while stopped: these records must be recovered from retained WAL.
    id=new_payment();os.environ['SAVEPOINT']=saved['path']
    try:submit('restore')
    finally:os.environ.pop('SAVEPOINT',None)
    assert job()!=old;poll('WAL catch-up after restore',lambda:single(id));reconcile()
    cp=poll('restored checkpoint',checkpoint);restored=http('/jobs/'+job()+'/checkpoints')['latest'].get('restored');assert restored and restored['external_path']==saved['path'];record('restored',restored)

def test_07_J_persistent_catalog():
    before=query('SHOW TABLES FROM iceberg.oltp_mirror');snap=snapshot()
    compose('restart','gravitino-iceberg-rest');poll('catalog restarted',lambda:http('/iceberg/v1/config','CATALOG_PORT'))
    assert query('SHOW TABLES FROM iceberg.oltp_mirror')==before
    assert query(f'SELECT count(*) AS n FROM iceberg.oltp_mirror.payments_current FOR VERSION AS OF {snap}')
    reconcile()

@pytest.mark.parametrize('service,port,path',[('postgres-oltp',None,None),('minio','MINIO_PORT','/minio/health/ready'),('gravitino-iceberg-rest','CATALOG_PORT','/iceberg/v1/config')])
def test_08_K_short_outage(service,port,path):
    before=checkpoint();compose('stop','-t','5',service)
    try:
        if port:
            with pytest.raises(Exception):http(path,port)
        else:
            with pytest.raises(subprocess.CalledProcessError):pg('SELECT 1')
        record('outage-'+service,{'service':service,'observed':'client connection failure','checkpointBefore':before})
    finally:compose('start',service)
    if port:poll(service+' available',lambda:reachable(path,port),timeout=180)
    else:poll('Postgres available',lambda:pg('SELECT 1')=='1')
    id=new_payment();poll('CDC after outage',lambda:single(id),timeout=240);reconcile()

def reachable(path,port):
    try:http(path,port);return True
    except Exception:return False

def test_09_L_bootstrap_submit_idempotent():
    old=job();bootstrap();generate('seed')
    errors=[]
    def repeat():
        try:submit()
        except Exception as e:errors.append(e)
    workers=[threading.Thread(target=repeat) for _ in range(2)]
    for w in workers:w.start()
    for w in workers:w.join(timeout=120)
    assert not any(w.is_alive() for w in workers);assert not errors;assert job()==old
    slots=pg("SELECT count(*) FROM pg_replication_slots WHERE active AND slot_name IN ('lab_customers','lab_accounts','lab_payments')",admin=True);assert slots=='3'
    reconcile();record('final-snapshots',{t:query(f'SELECT * FROM iceberg.oltp_mirror."{t}_current$snapshots" ORDER BY committed_at DESC LIMIT 1') for t in ('customers','accounts','payments')})
