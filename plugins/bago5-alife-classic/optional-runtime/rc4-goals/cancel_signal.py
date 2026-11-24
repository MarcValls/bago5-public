"""Per-run memory cancellation latch, independent of TaskStore SQLite writes.

The owner creates it before round admission. The worker must attach before CLI
launch. The single byte moves only from 0 to 1. This is cancellation, not authority.
"""
from multiprocessing.shared_memory import SharedMemory
import inspect,secrets

class CancelSignal:
    def __init__(self,name=None,create=False):
        args={'name':name,'create':create}
        if create:args.update(name='bago_cancel_'+secrets.token_hex(16),size=1)
        if 'track' in inspect.signature(SharedMemory).parameters:args['track']=False
        self.memory=SharedMemory(**args)
        self.owner=create
        if create:self.memory.buf[0]=0
    @property
    def name(self):return self.memory.name
    def set(self):self.memory.buf[0]=1
    def is_set(self):return self.memory.buf[0]!=0
    def close(self):
        self.memory.close()
        if self.owner:
            try:self.memory.unlink()
            except FileNotFoundError:pass
