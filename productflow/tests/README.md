# ProductFlow tests

Pure Python `stdlib unittest`. Zero non-stdlib deps for the CLI/HTTP layers;
`playwright` is only imported by the e2e layer, which self-skips when it (or the
pinned chromium build) is absent.

## How to run

```bash
# from the skill root
cd skills/productflow
python3 -m unittest discover -s tests -p 'test_*.py' -v

# or the wrapper (cds to the skill root itself, surfaces ResourceWarnings)
tests/run.sh        # quiet
tests/run.sh -v     # verbose

# a single module / class / test
python3 -m unittest tests.test_pf_state -v
python3 -m unittest tests.test_server.ServerTest.test_version
```

## Isolation (the important part)

`pf_state.py` and `server.py` both compute
`PF_HOME = expanduser("~/.productflow")` **at import time**, and `/api/create`
defaults new projects to `~/code`. So overriding the `HOME` environment variable
sandboxes *everything* — the project registry, the pending queue, and new-project
directories — into a throwaway temp dir.

`tests/helpers.py` is the shared harness and the only thing tests are built on:

- `make_home()` / `rm_home(home)` — create/destroy a temp `HOME`
  (`pf-test-home-*` under the system temp dir, with a `code/` subdir). It also
  drops a no-op `claude` stub in `<home>/bin` (prepended to `PATH`): `server.py`
  auto-spawns a real `claude` agent in the background on brief/explore requests
  (`_auto_gen_brief` / `_auto_explore`), which in tests would cost real tokens,
  run slow non-deterministic agents, and leak temp dirs. The stub makes that an
  instant no-op so the server takes its degradation path, and tests drive the
  brief/explore flow deterministically by simulating the agent via `cli()`. The
  real claude integration is verified manually, not in CI.
- `cli(args, home, project=…)` — subprocess `pf_state.py` with `HOME` (and
  optional `PF_PROJECT`) overridden; returns a `CompletedProcess`.
- `cli_json(...)` — same, parsing JSON stdout.
- `start_server(home, port=None)` / `stop_server(proc)` — launch `server.py` on
  a **free port** (never 7717) under the sandboxed `HOME`, waiting for
  `/api/version` to answer; teardown terminates it and closes its pipe.
- `http(port, path, method, body)` — header-less `urllib` request. The server's
  anti-rebinding guard only rejects when a mismatched `Origin` / `Sec-Fetch-Site`
  header is present, so header-less requests (`Host=127.0.0.1`) pass cleanly.
- `create_project(port, name, slug=…)` — the `/api/create` wizard path.
- `free_port()`, `CHROMIUM_EXE`, `PF_STATE`, `SERVER`, `SKILL_DIR`.

**Rules every test follows:**

- Each test (or `setUpClass`) builds a fresh sandbox `HOME`; `tearDown` /
  `tearDownClass` calls `rm_home` and `stop_server`.
- Servers always bind a `free_port()`, never the real console's `:7717`.
- HTTP tests give each project a distinct name/slug so the per-class shared
  registry can't cause cross-test interference.
- No test imports `pf_state`/`server` in-process — everything goes through
  subprocesses with `HOME` overridden, so the real `~/.productflow` and `~/code`
  are never reachable.

Verified: a full `discover` run leaves every real `~/.productflow/projects/*.json`
byte-identical (hash + mtime) and `~/code` membership unchanged, with no
`pf-test-home-*` temp dirs left behind.

## Coverage by layer

| File | Layer | What it covers |
|------|-------|----------------|
| `test_pf_state.py` | CLI state machine (subprocess, no server) | `init` (state.json, id format `slug-XXXX`, registry entry, artifact dirs, reinit/force), `phase`/`step` transitions + logging, `artifact` register/dedup/type-infer, `page` add/list/rm/set (+auto-done), `explore` refs/heroes/summary/clear, `brief` set-summary/done-request, `inbox`/`reply` (web-only filtering, cursor, `--peek`), `unregister`, `--dir` vs `$PF_PROJECT` resolution |
| `test_server.py` | HTTP API (real server subprocess, urllib) | `/api/version`, `/api/projects` shape, security guard (Host / Origin / Sec-Fetch → 403, GET ignores Origin), `/api/create` (slug, Chinese fallback, dup suffix), `/api/pending`, per-project GET defaults, brief/explore/canvas/pages/inbox round-trips + inbox request entries, bad ids / path traversal / disallowed subs / bad JSON → 404/400 |
| `test_e2e_console.py` | Browser e2e (headless chromium via playwright) | Full wizard journey (create → brief → visual explore) driving `assets/console.html`, with the CLI side backfilling state at each agent checkpoint; project-view `switchView` board/canvas. Asserts zero JS runtime errors. **Skips** if playwright import fails or the pinned chromium build is missing. |

The e2e layer is allowed to skip in headless/CI environments; the CLI and HTTP
layers must always be green.
