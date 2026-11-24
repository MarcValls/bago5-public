#!/usr/bin/env python3
"""Deliver a JSON decision authored by the actual reasoning host.
This transports a reply; it neither reasons nor calls an external model.
"""
from __future__ import annotations
import argparse,hashlib,json,os,re
from pathlib import Path

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work',required=True,type=Path)
    ap.add_argument('--request',required=True)
    ap.add_argument('--content',required=True,type=Path,help='Native task JSON authored after reading the request')
    ap.add_argument('--author',required=True,help='Actual host/provider identity; not inferred by this script')
    a=ap.parse_args()
    if not re.fullmatch(r'cycle0[123]-(propose|reflect)-[0-9]{2}',a.request):ap.error('Invalid request identifier')
    work=a.work.resolve();box=work/'mailbox'
    request=box/f'{a.request}.request.json';output=box/f'{a.request}.response.json'
    if request.is_symlink() or not request.is_file():ap.error('Missing or unsafe request')
    if output.exists():ap.error('Refusing to overwrite a delivered reply')
    q=json.loads(request.read_text(encoding='utf-8'))
    if q.get('mode')!='live':ap.error('This helper delivers live decisions only; use replay_mission.py for recordings')
    content=json.loads(a.content.read_text(encoding='utf-8'))
    if not isinstance(content,dict):ap.error('Reply content must be an object')
    digest=hashlib.sha256(json.dumps(q,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    result={'schema':'bago.cognitive.host-response.v1','request_id':q['id'],'request_sha256':digest,
            'mode':'live','content':content,'author':a.author}
    tmp=output.with_suffix('.tmp')
    with tmp.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False)
    os.replace(tmp,output)
    print(json.dumps({'status':'DELIVERED_NOT_YET_ACCEPTED','response':str(output),'request_sha256':digest}))
    return 0
if __name__=='__main__':raise SystemExit(main())
