"""Discover full metric IDs first, then query only supported returned IDs."""
import urllib.parse
from lab import http
NAMES={'numRestarts','numberOfCompletedCheckpoints','numberOfFailedCheckpoints','lastCheckpointDuration','lastCheckpointSize','numRecordsIn','numRecordsOut','numRecordsInPerSecond','numRecordsOutPerSecond','busyTimeMsPerSecond','backPressuredTimeMsPerSecond','idleTimeMsPerSecond','isSnapshotting','isStreamReading','snapshotStartTime','snapshotEndTime'}
def selected(path):
    available=http(path)
    ids=[v['id'] for v in available if v['id'].split('.')[-1] in NAMES]
    return http(path+'?get='+urllib.parse.quote(','.join(ids),safe='')) if ids else []
def collect(jid):
    result={'job':selected('/jobs/'+jid+'/metrics'),'vertices':{}}
    for v in http('/jobs/'+jid)['vertices']:
        result['vertices'][v['id']]={'name':v['name'],'metrics':selected('/jobs/'+jid+'/vertices/'+v['id']+'/metrics')}
    return result
