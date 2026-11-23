from pathlib import Path
import argparse,sys,runpy,unittest
HERE=Path(__file__).resolve().parent
CORE=HERE.parent/'bago-operating-suite/runtime/BAGO-4.11.10/backend/.bago/core'
sys.path.insert(0,str(CORE))
p=argparse.ArgumentParser(description='SPBE reference compiler; no execution permission or project mutation')
p.add_argument('operation',choices=['test','example']);a=p.parse_args()
if a.operation=='test':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.TestLoader().discover(str(HERE/'tests')))
 sys.exit(0 if result.wasSuccessful() else 1)
runpy.run_path(str(HERE/'examples/minimal_example.py'),run_name='__main__')
