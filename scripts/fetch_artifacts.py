#!/usr/bin/env python3
"""Download only locked official release artifacts; reject mismatching bytes."""
import hashlib, json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def fetch():
    cache=ROOT/'.cache/artifacts'; cache.mkdir(parents=True,exist_ok=True)
    for item in json.loads((ROOT/'config/artifacts.lock.json').read_text()):
        path=cache/item['file']
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']:continue
        temp=path.with_suffix(path.suffix+'.part')
        subprocess.run(['curl','-fLsS','--retry','3','--connect-timeout','15','--max-time','600',item['url'],'-o',str(temp)],check=True)
        if hashlib.sha256(temp.read_bytes()).hexdigest()!=item['sha256']:raise RuntimeError('SHA256 mismatch: '+item['file'])
        temp.replace(path)
        print('verified',item['file'],flush=True)
if __name__=='__main__':fetch()
