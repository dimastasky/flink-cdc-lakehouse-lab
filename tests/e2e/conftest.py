import json,os,sys,time
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
from lab import init,up,bootstrap,generate,compose,environment,http
@pytest.fixture(scope='session',autouse=True)
def cluster():
    if not os.getenv('E2E_RUN_ID'):pytest.fail('Use make test-e2e: it isolates project, ports and volumes')
    state=Path(environment()['LAB_STATE_DIR']);state.mkdir(parents=True,exist_ok=True)
    (state/'run.json').write_text(json.dumps({'started':time.time(),'seed':42,'project':environment()['COMPOSE_PROJECT_NAME'],'scenario':'A-L','command':'make test-e2e'},indent=2))
    try:
        init();up();bootstrap();generate('seed');yield
    finally:
        try:
            (state/'containers.log').write_text(compose('logs','--no-color',capture=True,check=False).stdout)
            (state/'jobs.json').write_text(json.dumps(http('/jobs/overview'),indent=2))
            for j in http('/jobs/overview')['jobs']:
                if j['name']=='postgres-to-iceberg-current':
                    (state/(j['jid']+'-checkpoints.json')).write_text(json.dumps(http('/jobs/'+j['jid']+'/checkpoints'),indent=2))
                    (state/(j['jid']+'-exceptions.json')).write_text(json.dumps(http('/jobs/'+j['jid']+'/exceptions'),indent=2))
        except Exception as error:
            (state/"diagnostics-error.txt").write_text(str(error))
        finally:
            # These volumes were created by THIS isolated test run, never the user's baseline.
            compose('--profile','tools','down','--volumes','--remove-orphans',check=False)

def pytest_runtest_logreport(report):
    if report.when=='call':
        p=Path(os.environ['LAB_STATE_DIR'])/'assertions.jsonl'
        with p.open('a') as f:f.write(json.dumps({'scenario':report.nodeid,'outcome':report.outcome,'duration':report.duration,'failure':str(report.longrepr) if report.failed else None})+'\n')
