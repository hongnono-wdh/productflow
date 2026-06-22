"""Shared test harness for ProductFlow.

Isolation strategy: both pf_state.py and server.py compute
PF_HOME = expanduser("~/.productflow") at import time, and /api/create defaults
to ~/code. So overriding the HOME env var sandboxes EVERYTHING — registry,
pending queue, and new-project directories — into a throwaway temp dir. Tests
never touch the user's real ~/.productflow or the console running on :7717.

The server is started as a subprocess on a free port (never 7717). API calls go
through plain urllib: the server's anti-rebinding guard only rejects when an
Origin / Sec-Fetch-Site header is present AND mismatched, so header-less urllib
requests (Host=127.0.0.1) pass cleanly.
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)
SCRIPTS = os.path.join(SKILL_DIR, "scripts")
PF_STATE = os.path.join(SCRIPTS, "pf_state.py")
SERVER = os.path.join(SCRIPTS, "server.py")

# Known-good chromium for python-playwright (build number may not match the
# pinned default, so tests pass executable_path explicitly).
CHROMIUM_EXE = os.path.expanduser(
    "~/Library/Caches/ms-playwright/chromium_headless_shell-1169/chrome-mac/headless_shell"
)


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def make_home():
    """Throwaway HOME that sandboxes PF_HOME (~/.productflow) and ~/code.

    Also drops a no-op ``claude`` stub in ``<home>/bin``. server.py's
    _auto_gen_brief / _auto_explore spawn a real ``claude`` agent in the
    background on brief/explore requests; in tests that would cost real tokens,
    run slow non-deterministic agents (Dribbble, image-gen), and leak temp
    dirs. The stub makes the auto-spawn an instant no-op, so the server takes
    its degradation path and tests drive the flow deterministically via cli()
    simulating the agent. The real claude integration is verified manually.
    """
    home = tempfile.mkdtemp(prefix="pf-test-home-")
    os.makedirs(os.path.join(home, "code"), exist_ok=True)
    bindir = os.path.join(home, "bin")
    os.makedirs(bindir, exist_ok=True)
    stub = os.path.join(bindir, "claude")
    with open(stub, "w") as f:
        f.write("#!/bin/sh\nexit 0\n")
    os.chmod(stub, 0o755)
    return home


def rm_home(home):
    shutil.rmtree(home, ignore_errors=True)


def _env(home, project=None):
    e = dict(os.environ)
    e["HOME"] = home
    # Prepend <home>/bin so the no-op `claude` stub shadows the real binary,
    # keeping the server's auto-spawn from launching real claude agents.
    e["PATH"] = os.path.join(home, "bin") + os.pathsep + e.get("PATH", "")
    # 框选重绘默认调仓库自带的 scripts/edit.py（会真打网关）。测试里指向沙箱内的假 edit.py
    # （TestRedraw._fake_edit_py 写在这），既不走网络又能验证 server 真传了 --mask 蒙版。
    e["PF_EDIT_PY"] = os.path.join(home, ".claude", "skills", "openai-image-gen", "scripts", "edit.py")
    e.pop("PF_PROJECT", None)
    if project:
        e["PF_PROJECT"] = project
    return e


def cli(args, home, project=None, cwd=None):
    """Run pf_state.py. Returns CompletedProcess (.returncode/.stdout/.stderr)."""
    return subprocess.run(
        [sys.executable, PF_STATE] + list(args),
        env=_env(home, project), cwd=cwd,
        capture_output=True, text=True,
    )


def cli_json(args, home, project=None, cwd=None):
    """Run a pf_state command whose stdout is JSON; parse and return it."""
    r = cli(args, home, project=project, cwd=cwd)
    if r.returncode != 0:
        raise AssertionError(f"cli {args} failed rc={r.returncode}: {r.stderr}")
    return json.loads(r.stdout)


def start_server(home, port=None, extra_env=None):
    """Start server.py on a free port with sandboxed HOME. Returns (proc, port).

    extra_env: optional dict merged into the server env (e.g. {"PF_UI": "legacy"}
    to serve the legacy console.html instead of the default React dist)."""
    if port is None:
        port = free_port()
    env = _env(home)
    if extra_env:
        env.update(extra_env)
    proc = subprocess.Popen(
        [sys.executable, SERVER, "--port", str(port)],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    url = f"http://127.0.0.1:{port}/api/version"
    for _ in range(60):
        if proc.poll() is not None:
            out = proc.stdout.read() if proc.stdout else ""
            raise RuntimeError(f"server exited early: {out}")
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                if resp.status == 200:
                    return proc, port
        except Exception:
            time.sleep(0.1)
    stop_server(proc)
    raise RuntimeError("server did not come up in time")


def stop_server(proc):
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
    # Close the merged stdout/stderr PIPE to avoid ResourceWarning on GC.
    if proc.stdout is not None:
        try:
            proc.stdout.close()
        except Exception:
            pass


def http(port, path, method="GET", body=None):
    """HTTP request to the test server. Returns (status_code, parsed_body)."""
    url = f"http://127.0.0.1:{port}{path}"
    data, headers = None, {}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read().decode()
            return resp.status, (json.loads(raw) if raw.strip() else None)
    except urllib.error.HTTPError as ex:
        raw = ex.read().decode()
        ex.close()
        try:
            return ex.code, json.loads(raw)
        except Exception:
            return ex.code, raw


def create_project(port, name, slug=None):
    """POST /api/create (the wizard path). Returns the response dict {id, dir}."""
    body = {"name": name}
    if slug:
        body["slug"] = slug
    status, payload = http(port, "/api/create", method="POST", body=body)
    if status != 200 or not isinstance(payload, dict) or not payload.get("id"):
        raise AssertionError(f"create_project failed: {status} {payload}")
    return payload
