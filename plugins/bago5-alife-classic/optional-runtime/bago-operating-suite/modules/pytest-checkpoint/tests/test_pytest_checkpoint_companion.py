"""Black-box, process-bound contract tests for the opt-in pytest companion."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


PLUGIN_PARENT = Path(__file__).resolve().parents[3]
PLUGIN_FILE = PLUGIN_PARENT / "scripts" / "pytest_checkpoint.py"


def _git(root: Path, *args: str) -> None:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def _workspace(tmp_path: Path, source: str) -> Path:
    root = tmp_path / "source"
    root.mkdir()
    (root / "test_flow.py").write_text(source, encoding="utf-8")
    (root / ".gitignore").write_text(".pytest_cache/\n__pycache__/\n*.pyc\n", encoding="utf-8")
    _git(root, "init", "-q")
    _git(root, "add", "test_flow.py", ".gitignore")
    _git(root, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "fixture")
    return root


def _run(root: Path, state: Path, *options: str, **env_overrides: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["PYTHONPATH"] = str(PLUGIN_PARENT) + os.pathsep + env.get("PYTHONPATH", "")
    env.update(env_overrides)
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "scripts.pytest_checkpoint",
         "--bago-checkpoint", str(state), "-q", "test_flow.py", *options],
        cwd=root, env=env, capture_output=True, text=True, timeout=40,
    )


def _status(state: Path) -> dict:
    result = subprocess.run(
        [sys.executable, str(PLUGIN_FILE), "status", str(state)],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_crash_resume_replays_only_unfinished_test(tmp_path: Path) -> None:
    root = _workspace(tmp_path, '''
from pathlib import Path
import os

def test_01_done():
    p = Path('.pytest_cache/counter.txt')
    p.parent.mkdir(exist_ok=True)
    p.write_text(str(int(p.read_text()) + 1 if p.exists() else 1))
    assert True

def test_02_kill():
    if os.environ.get('RELEASE_TEST') != 'yes':
        os._exit(17)
    assert True
''')
    state = root / ".pytest_cache" / "resume.sqlite3"
    interrupted = _run(root, state)
    assert interrupted.returncode == 17, interrupted.stdout + interrupted.stderr
    assert _status(state)["passed"] == 1
    assert _status(state)["remaining"] == 1
    resumed = _run(root, state, "--bago-resume", RELEASE_TEST="yes")
    assert resumed.returncode == 0, resumed.stdout + resumed.stderr
    assert (root / ".pytest_cache" / "counter.txt").read_text() == "1"
    assert _status(state)["checkpoint_complete"] is True
    assert _status(state)["attempts"] == 2
    repeated = _run(root, state, "--bago-resume", RELEASE_TEST="yes")
    assert repeated.returncode == 0, repeated.stdout + repeated.stderr
    assert _status(state)["attempts"] == 2


def test_changed_source_refuses_stale_pass(tmp_path: Path) -> None:
    root = _workspace(tmp_path, "def test_pass():\n    assert True\n")
    state = root / ".pytest_cache" / "stale.sqlite3"
    first = _run(root, state)
    assert first.returncode == 0, first.stdout + first.stderr
    (root / "test_flow.py").write_text("def test_pass():\n    assert 2 == 2\n")
    second = _run(root, state, "--bago-resume")
    assert second.returncode != 0
    assert "identity mismatch: files_sha256" in second.stderr + second.stdout
    assert _status(state)["attempts"] == 1


def test_teardown_failure_not_checkpointed_as_pass(tmp_path: Path) -> None:
    root = _workspace(tmp_path, '''
import os
import pytest

@pytest.fixture
def resource():
    yield
    if os.environ.get('TEARDOWN_GOOD') != 'yes':
        raise RuntimeError('teardown broken')

def test_teardown(resource):
    assert True
''')
    state = root / ".pytest_cache" / "teardown.sqlite3"
    first = _run(root, state)
    assert first.returncode == 1, first.stdout + first.stderr
    assert _status(state)["statuses"] == {"FAILED": 1}
    second = _run(root, state, "--bago-resume", TEARDOWN_GOOD="yes")
    assert second.returncode == 0, second.stdout + second.stderr
    assert _status(state)["statuses"] == {"PASSED": 1}
    assert _status(state)["attempts"] == 2


def test_skipped_test_never_claims_pass(tmp_path: Path) -> None:
    root = _workspace(tmp_path, "import pytest\n\ndef test_skipped():\n    pytest.skip('not verified')\n")
    state = root / ".pytest_cache" / "skip.sqlite3"
    result = _run(root, state)
    assert result.returncode == 0, result.stdout + result.stderr
    report = _status(state)
    assert report["statuses"] == {"SKIPPED": 1}
    assert report["checkpoint_complete"] is False


def test_existing_checkpoint_requires_explicit_resume(tmp_path: Path) -> None:
    root = _workspace(tmp_path, "def test_pass():\n    assert True\n")
    state = root / ".pytest_cache" / "fixed.sqlite3"
    assert _run(root, state).returncode == 0
    second = _run(root, state)
    assert second.returncode != 0
    assert "checkpoint exists" in second.stderr + second.stdout
    assert _status(state)["attempts"] == 1


def test_changed_selector_refuses_stale_pass(tmp_path: Path) -> None:
    root = _workspace(tmp_path, "def test_pass():\n    assert True\n")
    state = root / ".pytest_cache" / "selector.sqlite3"
    assert _run(root, state).returncode == 0
    second = _run(root, state, "--bago-resume", "-x")
    assert second.returncode != 0
    assert "identity mismatch: arguments" in second.stderr + second.stdout
    assert _status(state)["attempts"] == 1


def test_mutual_exclusion(tmp_path: Path) -> None:
    root = _workspace(tmp_path, '''
from pathlib import Path
import time

def test_wait():
    Path('.pytest_cache/started').write_text('yes')
    time.sleep(4)
''')
    state = root / ".pytest_cache" / "busy.sqlite3"
    env = os.environ.copy()
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["PYTHONPATH"] = str(PLUGIN_PARENT) + os.pathsep + env.get("PYTHONPATH", "")
    process = subprocess.Popen(
        [sys.executable, "-m", "pytest", "-p", "scripts.pytest_checkpoint",
         "--bago-checkpoint", str(state), "-q", "test_flow.py"],
        cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        import time
        for _ in range(80):
            if (root / ".pytest_cache" / "started").exists():
                break
            assert process.poll() is None, "first runner ended before starting"
            time.sleep(0.05)
        else:
            pytest.fail("first runner not started")
        second = _run(root, state, "--bago-resume")
        assert second.returncode != 0
        assert "checkpoint already in use" in second.stderr + second.stdout
    finally:
        process.kill()
        process.communicate(timeout=10)


def test_external_context_change_refuses_old_pass(tmp_path: Path) -> None:
    root = _workspace(tmp_path, "def test_pass():\n    assert True\n")
    state = root / ".pytest_cache" / "external.sqlite3"
    first = _run(root, state, "--bago-context", "dataset-v1")
    assert first.returncode == 0, first.stdout + first.stderr
    retry = _run(root, state, "--bago-context", "dataset-v2", "--bago-resume")
    assert retry.returncode != 0
    assert "identity mismatch: context" in retry.stderr + retry.stdout
    assert _status(state)["attempts"] == 1


def test_collection_error_does_not_create_verified_manifest(tmp_path: Path) -> None:
    root = _workspace(tmp_path, "def broken(:\n    pass\n")
    state = root / ".pytest_cache" / "collect.sqlite3"
    result = _run(root, state)
    assert result.returncode != 0
    if state.exists():
        check = subprocess.run(
            [sys.executable, str(PLUGIN_FILE), "status", str(state)],
            capture_output=True, text=True,
        )
        assert check.returncode != 0, "failed collection must not be a complete checkpoint"
