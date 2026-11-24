"""Test-only guard around the real entry point; not an OS sandbox."""
import os
import runpy
import sys

DENIED_READS = {os.path.abspath(p) for p in sys.argv[2:]}


def guard(event, args):
    forbidden = {"os.mkdir", "os.remove", "os.rename", "os.rmdir", "os.chmod",
                 "os.chown", "os.truncate", "os.utime", "os.link", "os.symlink",
                 "os.system", "os.exec", "os.posix_spawn", "subprocess.Popen"}
    if event in forbidden or event.startswith("socket."):
        raise RuntimeError("Forbidden hook side effect: " + event)
    if event == "open":
        path, mode, flags = args
        if isinstance(path, (str, bytes)) and os.path.abspath(os.fsdecode(path)) in DENIED_READS:
            raise RuntimeError("Forbidden unrelated read")
        if (isinstance(mode, str) and any(c in mode for c in "wax+")) or (
            isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
        ):
            raise RuntimeError("Forbidden hook write")


sys.addaudithook(guard)
runpy.run_path(sys.argv[1], run_name="__main__")
