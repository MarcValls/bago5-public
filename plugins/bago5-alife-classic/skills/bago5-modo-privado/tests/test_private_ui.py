"""Actual Tk events in Xvfb; synthetic host/launcher, no real credentials."""
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from private_mode import Coordinator, Gate, State
from test_private_mode import SyntheticHost, SyntheticLauncher

@unittest.skipUnless(os.environ.get('DISPLAY') or os.name=='nt','UI needs a display')
class DialogTests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from private_ui import PrivateDialog
        self.tmp=tempfile.TemporaryDirectory()
        self.gate=Gate(Path(self.tmp.name)/'gate.sqlite');self.gate.bootstrap()
        self.host=SyntheticHost();self.launcher=SyntheticLauncher(self.gate)
        self.c=Coordinator(self.gate,self.launcher,self.host)
        self.root=tk.Tk();self.dialog=PrivateDialog(self.root,self.c)
        self.root.update()
    def tearDown(self):
        try:self.root.destroy()
        except Exception:pass
        self.tmp.cleanup()
    def pump(self,predicate,timeout=3):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            self.root.update()
            if predicate():return
            time.sleep(.01)
        self.fail('UI event did not complete')
    def test_controls_connected_to_private_and_done(self):
        self.dialog.open_button.invoke()
        self.pump(lambda:not self.dialog.busy)
        self.assertEqual(self.gate.snapshot().state,State.PRIVATE)
        self.assertEqual(str(self.dialog.done_button['state']),'disabled')
        self.dialog.confirm.invoke()
        self.assertEqual(str(self.dialog.done_button['state']),'normal')
        self.dialog.done_button.invoke()
        self.assertEqual(self.gate.snapshot().state,State.NORMAL)
        self.assertIn('NO VERIFICADO',self.dialog.note.get())
    def test_cancel_button_retains_gate_and_requires_checkbox(self):
        self.dialog.open_button.invoke();self.pump(lambda:not self.dialog.busy)
        self.dialog.cancel_button.invoke()
        self.assertEqual(self.gate.snapshot().state,State.CANCELLED)
        self.assertEqual(str(self.dialog.resume_button['state']),'disabled')
        self.dialog.confirm.invoke();self.dialog.resume_button.invoke()
        self.assertEqual(self.gate.snapshot().state,State.NORMAL)
        self.assertIn('sin confirmar',self.dialog.note.get())
    def test_window_close_retains_cancelled_latch(self):
        self.dialog.open_button.invoke();self.pump(lambda:not self.dialog.busy)
        self.dialog.close()
        self.assertEqual(Gate(self.gate.path).snapshot().state,State.CANCELLED)
    def test_missing_host_shows_blocked_and_never_launches(self):
        from private_mode import MissingHost
        self.c.host=MissingHost()
        self.dialog.open_button.invoke();self.pump(lambda:not self.dialog.busy)
        self.assertEqual(self.dialog.state.get(),'BLOCKED')
        self.assertIn('HOST_UNAVAILABLE',self.dialog.note.get())
        self.assertEqual(self.launcher.opened,0)
    def test_no_free_text_secret_inputs(self):
        classes=[]
        def visit(widget):
            classes.append(widget.winfo_class())
            for child in widget.winfo_children():visit(child)
        visit(self.root)
        self.assertNotIn('Entry',classes);self.assertNotIn('TEntry',classes)
        self.assertNotIn('Text',classes);self.assertNotIn('TCombobox',classes)
    def test_window_close_during_preparation_cancels_launch(self):
        started=threading.Event();release=threading.Event()
        def freeze():started.set();release.wait(2)
        self.host.freeze_callback=freeze
        self.dialog.open_button.invoke();self.assertTrue(started.wait(2))
        self.dialog.close();release.set()
        # Wait without querying a destroyed window.
        deadline=time.monotonic()+3
        while self.dialog._alive and time.monotonic()<deadline:
            self.root.update();time.sleep(.01)
        self.assertFalse(self.dialog._alive)
        self.assertEqual(self.launcher.opened,0)
        self.assertEqual(self.gate.snapshot().state,State.CANCELLED)

if __name__=='__main__':unittest.main()
