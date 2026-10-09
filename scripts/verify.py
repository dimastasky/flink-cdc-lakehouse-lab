"""Independent read paths: psql/JSON for expected state, Trino REST for Iceberg."""
import datetime as dt
from decimal import Decimal
import json, re, time, urllib.request, urllib.parse
from pathlib import Path
from lab import compose, environment, poll
TABLES={'customers':'customer_id','accounts':'account_id','payments':'payment_id'}
def pg(sql,admin=False):
    # Feed a script so SELECT results survive a trailing COMMIT. Quiet mode
    # suppresses transaction/row-count tags while preserving query output.
    result=compose('exec','-T','postgres-oltp','psql','-X','-U','postgres' if admin else 'lab_app','-d','payments','-v','ON_ERROR_STOP=1','-qAt','-f','-',input=sql,capture=True,timeout=45)
    return result.stdout.strip()
def query(sql,timeout=90):
    base='http://127.0.0.1:'+environment()['TRINO_PORT'];end=time.monotonic()+timeout
    req=urllib.request.Request(base+'/v1/statement',data=sql.encode(),headers={'X-Trino-User':'lab','X-Trino-Time-Zone':'UTC','Content-Type':'text/plain'})
    rows=[];columns=[];next_uri=None
    try:
        while True:
            with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req,timeout=min(15,max(1,end-time.monotonic()))) as r:page=json.loads(r.read(),parse_float=Decimal)
            if 'error' in page:raise RuntimeError(json.dumps(page['error']))
            columns=page.get('columns',columns);rows.extend(page.get('data',[]));next_uri=page.get('nextUri')
            if not next_uri:return [dict(zip([c['name'] for c in columns],row)) for row in rows]
            if time.monotonic()>end:raise TimeoutError('Trino query deadline: '+sql[:100])
            uri=urllib.parse.urlsplit(next_uri);req=urllib.request.Request(base+uri.path+('?' +uri.query if uri.query else ''),headers={'X-Trino-User':'lab'})
            time.sleep(0.1)
    except Exception:
        if next_uri:
            try:urllib.request.build_opener(urllib.request.ProxyHandler({})).open(urllib.request.Request(base+urllib.parse.urlsplit(next_uri).path,method='DELETE'),timeout=3).close()
            except Exception:pass
        raise

def normalize(row):
    result={}
    for key,value in row.items():
        if value is None:result[key]=None
        elif key in ('created_at','updated_at','event_time'):
            s=str(value).replace(' UTC','+00:00').replace('Z','+00:00')
            def fraction(match):
                digits=match.group(2)
                if any(d!='0' for d in digits[3:]):
                    raise AssertionError('Sub-millisecond value: '+s)
                # Python 3.9 accepts three/six fractional digits, whereas
                # PostgreSQL JSON can shorten .130 to .13 or .100 to .1.
                return match.group(1)+'.'+digits[:6].ljust(6,'0')
            s=re.sub(r'([T ]\d{2}:\d{2}:\d{2})\.(\d+)',fraction,s)
            parsed=dt.datetime.fromisoformat(s)
            if parsed.tzinfo is None:raise AssertionError('Timestamp lost its timezone: '+s)
            if parsed.microsecond%1000:raise AssertionError('Sub-millisecond value: '+s)
            result[key]=parsed.astimezone(dt.timezone.utc)
        elif key=='amount':result[key]=Decimal(str(value))
        else:result[key]=value
    return result

def expected_state():
    # ONE repeatable-read source snapshot, after generator/processes have completed.
    parts=','.join(f"'{t}',(SELECT coalesce(json_agg(x),'[]'::json) FROM (SELECT * FROM {t} ORDER BY {pk}) x)" for t,pk in TABLES.items())
    raw=pg('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY; SELECT json_build_object('+parts+'); COMMIT;')
    # json_agg can produce multiline JSON; parse the complete result.
    try:
        expected=json.loads(raw,parse_float=Decimal)
    except json.JSONDecodeError as e:
        raise RuntimeError('PostgreSQL snapshot returned empty or invalid JSON') from e
    if not isinstance(expected,dict) or any(not isinstance(expected.get(t),list) for t in TABLES):
        raise RuntimeError('PostgreSQL snapshot must contain an array for every source table')
    return expected

def difference(expected,actual,pk):
    left={r[pk]:normalize(r) for r in expected};right={r[pk]:normalize(r) for r in actual}
    if len(left)!=len(expected):return {'sourceDuplicate':True}
    if len(right)!=len(actual):return {'sinkDuplicate':True}
    missing=sorted(left.keys()-right.keys());extra=sorted(right.keys()-left.keys())
    changed=[{'key':k,'expected':left[k],'actual':right[k]} for k in left.keys()&right.keys() if left[k]!=right[k]]
    return {'missing':missing[:10],'extra':extra[:10],'changed':changed[:3]} if missing or extra or changed else None

def reconcile(timeout=240):
    expected=expected_state();last={}
    def same():
        last.clear()
        for table,pk in TABLES.items():
            diff=difference(expected[table],query('SELECT * FROM iceberg.oltp_mirror.'+table+'_current'),pk)
            if diff:last[table]=diff
        if last:print('Waiting for CDC:',json.dumps(last,default=str),flush=True);return False
        return True
    try:poll('full-state reconciliation',same,timeout=timeout,interval=3)
    except Exception as e:raise AssertionError(json.dumps(last,default=str)) from e
    result={t:len(rows) for t,rows in expected.items()};print('Exact keys/fields match:',result,flush=True);return result
