#!/usr/bin/env python3
"""REST submission serialized by a POSIX file lock shared by all local invocations."""
import fcntl, hashlib, json, os, sys, time, urllib.request, urllib.error, uuid
from pathlib import Path
BASE=os.getenv('FLINK_URL','http://flink-jobmanager:8081')
STATE=Path(os.getenv('STATE_DIR','/state')); STATE.mkdir(parents=True,exist_ok=True)
NAME='postgres-to-iceberg-current'
TERMINAL={'FAILED','CANCELED','FINISHED','SUSPENDED'}
def request(path,body=None,method=None,headers=None):
    if isinstance(body,dict):body=json.dumps(body).encode();headers={'Content-Type':'application/json'}
    try:
        with urllib.request.urlopen(urllib.request.Request(BASE+path,data=body,method=method,headers=headers or {}),timeout=30) as response:return json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f'Flink REST {error.code}: '+error.read().decode()[:12000]) from error
def wait_for(label,fn,timeout=240):
    end=time.monotonic()+timeout; last=None
    while time.monotonic()<end:
        try:
            value=fn()
            if value:return value
        except (urllib.error.URLError,TimeoutError) as exc:last=str(exc)
        time.sleep(2)
    raise RuntimeError(f'{label}: timeout; last={last}')
def state_write(data):
    tmp=STATE/'job.json.tmp';tmp.write_text(json.dumps(data,indent=2));tmp.replace(STATE/'job.json')
def main():
    action=sys.argv[1] if len(sys.argv)>1 else 'submit'
    artifact=Path('/app/pipeline.jar');sha=hashlib.sha256(artifact.read_bytes()).hexdigest()
    with (STATE/'submit.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        jobs=request('/jobs/overview')['jobs']
        active=[j for j in jobs if j['name']==NAME and j['state'] not in TERMINAL]
        if len(active)>1:raise RuntimeError('Multiple active pipelines: refuse any further submission')
        old=json.loads((STATE/'job.json').read_text()) if (STATE/'job.json').exists() else None
        if action=='submit' and active:
            if old and old.get('artifactSha256')!=sha:raise RuntimeError('Active job uses another artifact; planned migration required')
            state_write({'jobId':active[0]['jid'],'artifactSha256':sha,'name':NAME});print('Already active:',active[0]['jid']);return
        if action in ('savepoint','stop'):
            if len(active)!=1:raise RuntimeError('Expected exactly one active job')
            jid=active[0]['jid'];stop=action=='stop'
            payload={'targetDirectory':'s3://savepoints/baseline/','drain':False} if stop else {'target-directory':'s3://savepoints/baseline/','cancel-job':False}
            trigger=request(f'/jobs/{jid}/'+('stop' if stop else 'savepoints'),payload)['request-id']
            def done():
                r=request(f'/jobs/{jid}/savepoints/{trigger}')
                if r['status']['id']!='COMPLETED':return None
                if 'failure-cause' in r.get('operation',{}):raise RuntimeError(str(r['operation']))
                return r['operation']['location']
            location=wait_for('savepoint',done)
            record={'path':location,'jobId':jid,'artifactSha256':sha,'stopped':stop}
            (STATE/'savepoint.json').write_text(json.dumps(record,indent=2))
            if stop:wait_for('job FINISHED',lambda:request(f'/jobs/{jid}')['state']=='FINISHED')
            print(location);return
        if active:raise RuntimeError('Restore requires a stopped pipeline')
        restore=os.getenv('SAVEPOINT','') if action=='restore' else ''
        if action=='restore':
            if not restore:raise RuntimeError('SAVEPOINT is required')
            if not old or old.get('artifactSha256')!=sha:raise RuntimeError('Restore requires identical saved artifact SHA256')
        elif old:
            raise RuntimeError('A previous job exists but is not active. Use restore from a verified recent checkpoint/savepoint; never silently resnapshot.')
        jid=uuid.uuid4().hex
        boundary=uuid.uuid4().hex
        body=(f'--{boundary}\r\nContent-Disposition: form-data; name="jarfile"; filename="pipeline.jar"\r\nContent-Type: application/java-archive\r\n\r\n'.encode()+artifact.read_bytes()+f'\r\n--{boundary}--\r\n'.encode())
        upload=request('/jars/upload',body,'POST',{'Content-Type':f'multipart/form-data; boundary={boundary}'})
        jarid=upload['filename'].split('/')[-1]
        # Persist intent BEFORE network submit: an uncertain response must not lead to another reader.
        state_write({'jobId':jid,'artifactSha256':sha,'name':NAME,'submission':'pending'})
        payload={'jobId':jid,'entryClass':'lab.PostgresToIcebergJob','allowNonRestoredState':False}
        if restore:payload['savepointPath']=restore
        result=request(f'/jars/{jarid}/run',payload)
        state_write({'jobId':result['jobid'],'artifactSha256':sha,'name':NAME,'restoredFrom':restore})
        wait_for('job RUNNING',lambda:running(result['jobid']))
        print(json.dumps(result))
def running(jid):
    status=request('/jobs/'+jid)['state']
    if status in TERMINAL:raise RuntimeError('Job entered '+status+'; inspect exceptions')
    return status=='RUNNING'
if __name__=='__main__':main()
