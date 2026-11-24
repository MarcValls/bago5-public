#!/usr/bin/env python3
"""Reproduce mechanics using RECORDED host replies. This is NOT fresh reasoning.

Always creates a new root. Never marks replay as live; never replaces evidence.
"""
from __future__ import annotations
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',required=True,type=Path)
    ap.add_argument('--skill',type=Path,default=ROOT.parents[1])
    ap.add_argument('--recorded',type=Path,default=ROOT/'recordings/COG-REPAIR-002')
    args=ap.parse_args();work=args.output.resolve();recorded=args.recorded.resolve()
    transcript={}
    for n in range(1,4):
        for stage in ('propose','reflect'):
            key=f'cycle{n:02}-{stage}-01'
            p=recorded/f'{key}.response.json'
            data=json.loads(p.read_text(encoding='utf-8'))
            if data.get('mode')!='live' or data.get('schema')!='bago.cognitive.host-response.v1':
                raise ValueError('Expected authentic packaged live transcript as a recording; not a fresh reply')
            transcript[key]=(data,p,hashlib.sha256(p.read_bytes()).hexdigest())
    runner=[sys.executable,'-B',str(ROOT/'run_mission.py')]
    subprocess.run([*runner,'init','--output',str(work),'--skill',str(args.skill.resolve()),'--mode','replay'],check=True)
    deliveries=[]
    for n in range(1,4):
        logpath=work/'evidence'/f'replay-cycle-{n}.log'
        with logpath.open('w',encoding='utf-8') as log:
            proc=subprocess.Popen([*runner,'cycle','--work',str(work),'--number',str(n)],stdout=log,stderr=subprocess.STDOUT)
            deadline=time.monotonic()+240
            try:
                while proc.poll() is None:
                    if time.monotonic()>deadline:raise TimeoutError('Replay cycle timed out')
                    for request in (work/'mailbox').glob(f'cycle{n:02}-*.request.json'):
                        key=request.name.removesuffix('.request.json')
                        out=request.with_name(f'{key}.response.json')
                        if out.exists():continue
                        if key not in transcript:raise ValueError('Unexpected request; recordings do not supply an answer')
                        q=json.loads(request.read_text(encoding='utf-8'))
                        if q.get('mode')!='replay':raise ValueError('Refusing replay into a live request')
                        old,p,oldhash=transcript[key]
                        response={'schema':'bago.cognitive.host-response.v1','request_id':q['id'],
                            'request_sha256':hashlib.sha256(canonical(q).encode()).hexdigest(),
                            'mode':'replay','content':old['content'],
                            'recorded_response_sha256':oldhash,'author':'recorded host content; no new inference'}
                        tmp=out.with_suffix('.tmp');tmp.write_text(json.dumps(response,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(tmp,out)
                        deliveries.append({'id':key,'origin_sha256':oldhash,'mode':'REPLAY'})
                    time.sleep(.1)
                if proc.returncode!=0:raise RuntimeError(f'Cycle {n} failed; inspect {logpath}')
            finally:
                if proc.poll() is None:
                    subprocess.run([*runner,'stop','--work',str(work),'--reason','Explicit replay error cleanup'],capture_output=True)
                    try:proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:proc.kill();proc.wait()
        subprocess.run([*runner,'consume','--work',str(work),'--check',f'cycle{n}'],check=True)
    subprocess.run([*runner,'verify','--work',str(work)],check=True)
    subprocess.run([*runner,'consume','--work',str(work),'--check','final-verification'],check=True)
    subprocess.run([*runner,'close','--work',str(work)],check=True)
    result={'schema':'bago.cognitive.replay.v1','status':'PASS','mode':'REPLAY',
        'new_reasoning':False,'learning_evaluated':False,'deliveries':deliveries}
    (work/'evidence/REPLAY_RESULT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False));return 0
if __name__=='__main__':raise SystemExit(main())
