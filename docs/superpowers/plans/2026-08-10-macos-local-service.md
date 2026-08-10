# macOS Local Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Daibu Content Brain start automatically after macOS login and recover automatically when its Streamlit process exits.

**Architecture:** Add one focused Python service manager that renders and installs a per-user LaunchAgent plist, checks local prerequisites, creates a protected `.env` skeleton only when missing, and exposes install/status/uninstall commands. The LaunchAgent directly runs the repository virtual environment's Streamlit executable on `127.0.0.1:8501`; macOS `launchd` owns restart behavior and log redirection.

**Tech Stack:** Python 3.11 (`argparse`, `dataclasses`, `pathlib`, `plistlib`, `subprocess`, `urllib`), macOS `launchctl`, pytest.

## Global Constraints

- The service is available only while this Mac is on, awake, and the user is logged in.
- Bind only to `127.0.0.1:8501`; do not expose the app to LAN or internet clients.
- LaunchAgent label is exactly `io.daibu.content-brain`.
- Use `RunAtLoad = true`, `KeepAlive = true`, and `ThrottleInterval = 10`.
- Logs live under `~/Library/Logs/DaibuContentBrain/`.
- Never place Gemini, Groq, or Tavily API keys in Git, plist, commands, or logs.
- Create `.env` from `.env.example` only when `.env` is absent; set a newly created file to mode `600`; never overwrite an existing `.env`.
- `uninstall` removes only this LaunchAgent and its plist. It must preserve `.env`, databases, logos, and logs.
- Do not modify the user's unrelated uncommitted build-story files.
- Follow vertical TDD: one failing test, one minimal implementation, green, then the next test.

## File Map

- Create `daibu/local_service.py`: paths, plist rendering, prerequisite checks, protected `.env` creation, launchctl boundary, health status, install/status/uninstall CLI.
- Create `tests/test_local_service.py`: unit and boundary tests for the local service manager.
- Modify `README.md`: nontechnical install, status, logs, and uninstall commands.
- Modify `HANDOFF.md`: final root cause, product behavior, verification evidence, limits, and installed service location.

---

### Task 1: Render a safe LaunchAgent plist

**Files:**
- Create: `daibu/local_service.py`
- Create: `tests/test_local_service.py`

**Interfaces:**
- Produces: `ServicePaths`, `resolve_paths(project_root=None, user_home=None) -> ServicePaths`, and `build_plist(paths: ServicePaths) -> dict[str, object]`.
- Consumes: no earlier task interface.

- [ ] **Step 1: Write the failing plist test**

```python
# tests/test_local_service.py
from pathlib import Path

from daibu import local_service


def test_build_plist_runs_the_supported_server_only_on_localhost(tmp_path):
    project = tmp_path / "daibu-content-brain"
    home = tmp_path / "home"
    paths = local_service.resolve_paths(project, home)

    plist = local_service.build_plist(paths)

    assert plist["Label"] == "io.daibu.content-brain"
    assert plist["RunAtLoad"] is True
    assert plist["KeepAlive"] is True
    assert plist["ThrottleInterval"] == 10
    assert plist["WorkingDirectory"] == str(project)
    assert plist["ProgramArguments"] == [
        str(project / ".venv/bin/streamlit"),
        "run",
        str(project / "server.py"),
        "--server.address=127.0.0.1",
        "--server.port=8501",
        "--server.headless=true",
    ]
    serialized = repr(plist)
    assert "API_KEY" not in serialized
    assert plist["StandardOutPath"].endswith("/DaibuContentBrain/stdout.log")
    assert plist["StandardErrorPath"].endswith("/DaibuContentBrain/stderr.log")
```

- [ ] **Step 2: Run the test and verify RED**

Run: `.venv/bin/pytest -q tests/test_local_service.py::test_build_plist_runs_the_supported_server_only_on_localhost`

Expected: FAIL during import because `daibu.local_service` does not exist.

- [ ] **Step 3: Add the minimal path and plist implementation**

```python
# daibu/local_service.py
"""Install and inspect Daibu's per-user macOS LaunchAgent."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


LABEL = "io.daibu.content-brain"
PORT = 8501


@dataclass(frozen=True)
class ServicePaths:
    project_root: Path
    user_home: Path
    streamlit: Path
    server: Path
    env_example: Path
    env_file: Path
    launch_agent_dir: Path
    plist: Path
    log_dir: Path
    stdout_log: Path
    stderr_log: Path


def resolve_paths(
    project_root: Path | None = None,
    user_home: Path | None = None,
) -> ServicePaths:
    project = (project_root or Path(__file__).resolve().parents[1]).resolve()
    home = (user_home or Path.home()).resolve()
    log_dir = home / "Library/Logs/DaibuContentBrain"
    launch_agent_dir = home / "Library/LaunchAgents"
    return ServicePaths(
        project_root=project,
        user_home=home,
        streamlit=project / ".venv/bin/streamlit",
        server=project / "server.py",
        env_example=project / ".env.example",
        env_file=project / ".env",
        launch_agent_dir=launch_agent_dir,
        plist=launch_agent_dir / f"{LABEL}.plist",
        log_dir=log_dir,
        stdout_log=log_dir / "stdout.log",
        stderr_log=log_dir / "stderr.log",
    )


def build_plist(paths: ServicePaths) -> dict[str, object]:
    return {
        "Label": LABEL,
        "ProgramArguments": [
            str(paths.streamlit),
            "run",
            str(paths.server),
            "--server.address=127.0.0.1",
            f"--server.port={PORT}",
            "--server.headless=true",
        ],
        "WorkingDirectory": str(paths.project_root),
        "RunAtLoad": True,
        "KeepAlive": True,
        "ThrottleInterval": 10,
        "StandardOutPath": str(paths.stdout_log),
        "StandardErrorPath": str(paths.stderr_log),
        "EnvironmentVariables": {"PYTHONUNBUFFERED": "1"},
    }
```

- [ ] **Step 4: Run the test and verify GREEN**

Run: `.venv/bin/pytest -q tests/test_local_service.py::test_build_plist_runs_the_supported_server_only_on_localhost`

Expected: `1 passed`.

- [ ] **Step 5: Commit Task 1**

```bash
git add daibu/local_service.py tests/test_local_service.py
git commit -m "feat: render macOS launch agent"
```

---

### Task 2: Refuse installation when the project cannot run

**Files:**
- Modify: `daibu/local_service.py`
- Modify: `tests/test_local_service.py`

**Interfaces:**
- Consumes: `ServicePaths` from Task 1.
- Produces: `InvalidLocalService(ValueError)` and `validate_project(paths: ServicePaths) -> None`.

- [ ] **Step 1: Write one failing validation test**

```python
import pytest


def test_validate_project_lists_every_missing_runtime_file(tmp_path):
    paths = local_service.resolve_paths(tmp_path / "project", tmp_path / "home")

    with pytest.raises(local_service.InvalidLocalService) as error:
        local_service.validate_project(paths)

    message = str(error.value)
    assert str(paths.streamlit) in message
    assert str(paths.server) in message
    assert str(paths.env_example) in message
```

- [ ] **Step 2: Run the test and verify RED**

Run: `.venv/bin/pytest -q tests/test_local_service.py::test_validate_project_lists_every_missing_runtime_file`

Expected: FAIL because `InvalidLocalService` or `validate_project` is missing.

- [ ] **Step 3: Implement prerequisite validation**

```python
class InvalidLocalService(ValueError):
    pass


def validate_project(paths: ServicePaths) -> None:
    required = (paths.streamlit, paths.server, paths.env_example)
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise InvalidLocalService(
            "無法安裝呆一布背景服務，缺少：" + "、".join(missing)
        )
```

- [ ] **Step 4: Run the current test file and verify GREEN**

Run: `.venv/bin/pytest -q tests/test_local_service.py`

Expected: `2 passed`.

- [ ] **Step 5: Commit Task 2**

```bash
git add daibu/local_service.py tests/test_local_service.py
git commit -m "feat: validate local service prerequisites"
```

---

### Task 3: Create a protected `.env` skeleton without overwriting secrets

**Files:**
- Modify: `daibu/local_service.py`
- Modify: `tests/test_local_service.py`

**Interfaces:**
- Consumes: `ServicePaths` from Task 1.
- Produces: `ensure_env_file(paths: ServicePaths) -> bool`; returns `True` only when it creates `.env`.

- [ ] **Step 1: Write the failing creation test**

```python
def test_ensure_env_file_copies_the_example_with_owner_only_permissions(tmp_path):
    paths = local_service.resolve_paths(tmp_path / "project", tmp_path / "home")
    paths.project_root.mkdir(parents=True)
    paths.env_example.write_text("GEMINI_API_KEY=\n", encoding="utf-8")

    created = local_service.ensure_env_file(paths)

    assert created is True
    assert paths.env_file.read_text(encoding="utf-8") == "GEMINI_API_KEY=\n"
    assert paths.env_file.stat().st_mode & 0o777 == 0o600
```

- [ ] **Step 2: Run the creation test and verify RED**

Run: `.venv/bin/pytest -q tests/test_local_service.py::test_ensure_env_file_copies_the_example_with_owner_only_permissions`

Expected: FAIL because `ensure_env_file` is missing.

- [ ] **Step 3: Implement create-only behavior**

```python
import os
import shutil


def ensure_env_file(paths: ServicePaths) -> bool:
    shutil.copyfile(paths.env_example, paths.env_file)
    os.chmod(paths.env_file, 0o600)
    return True
```

- [ ] **Step 4: Run the creation test and verify GREEN**

Run: `.venv/bin/pytest -q tests/test_local_service.py::test_ensure_env_file_copies_the_example_with_owner_only_permissions`

Expected: `1 passed`.

- [ ] **Step 5: Write the next failing preservation test**

```python
def test_ensure_env_file_never_replaces_an_existing_secret_file(tmp_path):
    paths = local_service.resolve_paths(tmp_path / "project", tmp_path / "home")
    paths.project_root.mkdir(parents=True)
    paths.env_example.write_text("GEMINI_API_KEY=\n", encoding="utf-8")
    paths.env_file.write_text("GEMINI_API_KEY=existing-local-value\n", encoding="utf-8")

    created = local_service.ensure_env_file(paths)

    assert created is False
    assert paths.env_file.read_text(encoding="utf-8") == (
        "GEMINI_API_KEY=existing-local-value\n"
    )
```

- [ ] **Step 6: Run the preservation test and verify RED**

`.venv/bin/pytest -q tests/test_local_service.py::test_ensure_env_file_never_replaces_an_existing_secret_file`

Expected: FAIL because the minimal implementation from the first slice overwrites the existing value.

- [ ] **Step 7: Add the preservation guard and verify GREEN**

Add at the start of `ensure_env_file`:

```python
if paths.env_file.exists():
    return False
```

Then run the current test file:

Run: `.venv/bin/pytest -q tests/test_local_service.py`

Expected: `4 passed`.

- [ ] **Step 8: Commit Task 3**

```bash
git add daibu/local_service.py tests/test_local_service.py
git commit -m "feat: protect local service environment file"
```

---

### Task 4: Install and start the per-user LaunchAgent

**Files:**
- Modify: `daibu/local_service.py`
- Modify: `tests/test_local_service.py`

**Interfaces:**
- Consumes: `resolve_paths`, `validate_project`, `ensure_env_file`, and `build_plist`.
- Produces: `Command = Callable[[list[str]], int]`, `default_command(args: list[str]) -> int`, `service_domain(uid=None) -> str`, `service_target(uid=None) -> str`, and `install(paths, command=default_command) -> bool`.

- [ ] **Step 1: Write the failing install boundary test**

```python
import plistlib


def _runnable_paths(tmp_path):
    paths = local_service.resolve_paths(tmp_path / "project", tmp_path / "home")
    paths.streamlit.parent.mkdir(parents=True)
    paths.streamlit.write_text("#!/bin/sh\n", encoding="utf-8")
    paths.server.write_text("# server\n", encoding="utf-8")
    paths.env_example.write_text("GEMINI_API_KEY=\n", encoding="utf-8")
    return paths


def test_install_writes_the_plist_then_reloads_and_starts_the_service(tmp_path):
    paths = _runnable_paths(tmp_path)
    calls = []

    created_env = local_service.install(paths, command=lambda args: calls.append(args) or 0)

    assert created_env is True
    with paths.plist.open("rb") as handle:
        assert plistlib.load(handle) == local_service.build_plist(paths)
    target = local_service.service_target()
    domain = local_service.service_domain()
    assert calls == [
        ["launchctl", "bootout", target],
        ["launchctl", "bootstrap", domain, str(paths.plist)],
        ["launchctl", "kickstart", "-k", target],
    ]
```

- [ ] **Step 2: Run the install test and verify RED**

Run: `.venv/bin/pytest -q tests/test_local_service.py::test_install_writes_the_plist_then_reloads_and_starts_the_service`

Expected: FAIL because `install` is missing.

- [ ] **Step 3: Implement atomic plist writing and launchctl calls**

```python
import os
import plistlib
import subprocess
import tempfile
from collections.abc import Callable


Command = Callable[[list[str]], int]


def default_command(args: list[str]) -> int:
    return subprocess.run(
        args,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode


def service_domain(uid: int | None = None) -> str:
    return f"gui/{uid if uid is not None else os.getuid()}"


def service_target(uid: int | None = None) -> str:
    return f"{service_domain(uid)}/{LABEL}"


def _write_plist(paths: ServicePaths) -> None:
    paths.launch_agent_dir.mkdir(parents=True, exist_ok=True)
    paths.log_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=paths.launch_agent_dir,
        prefix=f".{LABEL}.",
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        plistlib.dump(build_plist(paths), handle)
    temporary.replace(paths.plist)


def install(paths: ServicePaths, command: Command = default_command) -> bool:
    validate_project(paths)
    created_env = ensure_env_file(paths)
    _write_plist(paths)
    command(["launchctl", "bootout", service_target()])
    if command(["launchctl", "bootstrap", service_domain(), str(paths.plist)]):
        raise InvalidLocalService("macOS 無法載入呆一布背景服務")
    if command(["launchctl", "kickstart", "-k", service_target()]):
        raise InvalidLocalService("macOS 無法啟動呆一布背景服務")
    return created_env
```

- [ ] **Step 4: Run the current test file and verify GREEN**

Run: `.venv/bin/pytest -q tests/test_local_service.py`

Expected: `5 passed`.

- [ ] **Step 5: Commit Task 4**

```bash
git add daibu/local_service.py tests/test_local_service.py
git commit -m "feat: install daibu launch agent"
```

---

### Task 5: Report health and uninstall without deleting user data

**Files:**
- Modify: `daibu/local_service.py`
- Modify: `tests/test_local_service.py`

**Interfaces:**
- Consumes: `ServicePaths`, `Command`, `service_target`.
- Produces: `ServiceStatus`, `health_check(url=...) -> bool`, `status(paths, command=..., health=...) -> ServiceStatus`, and `uninstall(paths, command=...) -> None`.

- [ ] **Step 1: Write the failing status test**

```python
def test_status_requires_both_launchctl_and_the_health_endpoint(tmp_path):
    paths = _runnable_paths(tmp_path)
    paths.launch_agent_dir.mkdir(parents=True)
    paths.plist.write_bytes(plistlib.dumps(local_service.build_plist(paths)))
    calls = []

    result = local_service.status(
        paths,
        command=lambda args: calls.append(args) or 0,
        health=lambda url: url == "http://127.0.0.1:8501/_stcore/health",
    )

    assert result.loaded is True
    assert result.healthy is True
    assert result.plist_path == paths.plist
    assert result.stderr_log == paths.stderr_log
    assert calls == [["launchctl", "print", local_service.service_target()]]
```

- [ ] **Step 2: Run the status test and verify RED**

Run: `.venv/bin/pytest -q tests/test_local_service.py::test_status_requires_both_launchctl_and_the_health_endpoint`

Expected: FAIL because `status` is missing.

- [ ] **Step 3: Implement health and status**

```python
from urllib.error import URLError
from urllib.request import urlopen


@dataclass(frozen=True)
class ServiceStatus:
    loaded: bool
    healthy: bool
    plist_path: Path
    stderr_log: Path


def health_check(
    url: str = f"http://127.0.0.1:{PORT}/_stcore/health",
) -> bool:
    try:
        with urlopen(url, timeout=2) as response:
            return response.status == 200 and response.read().strip() == b"ok"
    except (OSError, URLError):
        return False


def status(
    paths: ServicePaths,
    command: Command = default_command,
    health: Callable[[str], bool] = health_check,
) -> ServiceStatus:
    loaded = command(["launchctl", "print", service_target()]) == 0
    url = f"http://127.0.0.1:{PORT}/_stcore/health"
    return ServiceStatus(loaded, health(url), paths.plist, paths.stderr_log)
```

- [ ] **Step 4: Run the status test and verify GREEN**

Run: `.venv/bin/pytest -q tests/test_local_service.py::test_status_requires_both_launchctl_and_the_health_endpoint`

Expected: `1 passed`.

- [ ] **Step 5: Write the next failing foreign-listener status test**

```python
def test_status_identifies_a_healthy_listener_not_owned_by_the_launch_agent(tmp_path):
    paths = _runnable_paths(tmp_path)

    result = local_service.status(
        paths,
        command=lambda _args: 1,
        health=lambda _url: True,
    )

    assert result.loaded is False
    assert result.healthy is True
    assert result.occupied_by_other_process is True
```

- [ ] **Step 6: Run the foreign-listener test and verify RED**

Run: `.venv/bin/pytest -q tests/test_local_service.py::test_status_identifies_a_healthy_listener_not_owned_by_the_launch_agent`

Expected: FAIL because `ServiceStatus` does not yet expose `occupied_by_other_process`.

- [ ] **Step 7: Add the derived foreign-listener state and verify GREEN**

Add `occupied_by_other_process: bool` after `healthy` in `ServiceStatus`, then update `status`:

```python
healthy = health(url)
return ServiceStatus(
    loaded,
    healthy,
    healthy and not loaded,
    paths.plist,
    paths.stderr_log,
)
```

Run: `.venv/bin/pytest -q tests/test_local_service.py::test_status_identifies_a_healthy_listener_not_owned_by_the_launch_agent`

Expected: `1 passed`.

- [ ] **Step 8: Write the next failing uninstall preservation test**

```python
def test_uninstall_removes_only_the_service_plist(tmp_path):
    paths = _runnable_paths(tmp_path)
    paths.launch_agent_dir.mkdir(parents=True)
    paths.plist.write_text("plist", encoding="utf-8")
    paths.env_file.write_text("GEMINI_API_KEY=keep-me\n", encoding="utf-8")
    database = paths.project_root / "daibu.db"
    database.write_bytes(b"database")
    paths.log_dir.mkdir(parents=True)
    paths.stderr_log.write_text("old log", encoding="utf-8")
    calls = []

    local_service.uninstall(paths, command=lambda args: calls.append(args) or 0)

    assert calls == [["launchctl", "bootout", local_service.service_target()]]
    assert not paths.plist.exists()
    assert paths.env_file.read_text(encoding="utf-8") == "GEMINI_API_KEY=keep-me\n"
    assert database.read_bytes() == b"database"
    assert paths.stderr_log.read_text(encoding="utf-8") == "old log"
```

- [ ] **Step 9: Run the uninstall test and verify RED**

Run: `.venv/bin/pytest -q tests/test_local_service.py::test_uninstall_removes_only_the_service_plist`

Expected: FAIL because `uninstall` is missing.

- [ ] **Step 10: Implement uninstall**

```python
def uninstall(paths: ServicePaths, command: Command = default_command) -> None:
    command(["launchctl", "bootout", service_target()])
    paths.plist.unlink(missing_ok=True)
```

- [ ] **Step 11: Run the current test file and verify GREEN**

Run: `.venv/bin/pytest -q tests/test_local_service.py`

Expected: `8 passed`.

- [ ] **Step 12: Commit Task 5**

```bash
git add daibu/local_service.py tests/test_local_service.py
git commit -m "feat: inspect and remove local service"
```

---

### Task 6: Add the CLI and user-facing instructions

**Files:**
- Modify: `daibu/local_service.py`
- Modify: `tests/test_local_service.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: `resolve_paths`, `install`, `status`, `uninstall`.
- Produces: `main(argv: list[str] | None = None) -> int` and commands `python -m daibu.local_service install|status|uninstall`.

- [ ] **Step 1: Write the failing CLI status test**

```python
def test_main_status_returns_failure_until_the_service_is_healthy(monkeypatch, capsys):
    monkeypatch.setattr(
        local_service,
        "status",
        lambda _paths: local_service.ServiceStatus(
            loaded=True,
            healthy=False,
            occupied_by_other_process=False,
            plist_path=Path("agent.plist"),
            stderr_log=Path("stderr.log"),
        ),
    )

    exit_code = local_service.main(["status"])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "已載入：是" in output
    assert "網站健康：否" in output
    assert "stderr.log" in output
```

- [ ] **Step 2: Run the CLI test and verify RED**

Run: `.venv/bin/pytest -q tests/test_local_service.py::test_main_status_returns_failure_until_the_service_is_healthy`

Expected: FAIL because `main` is missing.

- [ ] **Step 3: Implement CLI dispatch and human-readable output**

```python
import argparse


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="管理呆一布本機背景服務")
    parser.add_argument("action", choices=("install", "status", "uninstall"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    paths = resolve_paths()
    if args.action == "install":
        created_env = install(paths)
        print("背景服務已安裝並要求啟動。")
        if created_env:
            print(f"已建立 {paths.env_file}；API key 必須在本機填入。")
        return 0
    if args.action == "uninstall":
        uninstall(paths)
        print("背景服務已移除；資料庫、.env 與紀錄均保留。")
        return 0
    current = status(paths)
    print(f"已載入：{'是' if current.loaded else '否'}")
    print(f"網站健康：{'是' if current.healthy else '否'}")
    if current.occupied_by_other_process:
        print("8501 已由其他程序使用；不會自動終止該程序。")
    print(f"設定：{current.plist_path}")
    print(f"錯誤紀錄：{current.stderr_log}")
    return 0 if current.loaded and current.healthy else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the current test file and verify GREEN**

Run: `.venv/bin/pytest -q tests/test_local_service.py`

Expected: `9 passed`.

- [ ] **Step 5: Write the next failing human-readable install error test**

```python
def test_main_install_reports_a_short_error_without_a_traceback(monkeypatch, capsys):
    def fail_install(_paths):
        raise local_service.InvalidLocalService("缺少 Streamlit")

    monkeypatch.setattr(local_service, "install", fail_install)

    exit_code = local_service.main(["install"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert captured.err == "錯誤：缺少 Streamlit\n"
```

- [ ] **Step 6: Run the install error test and verify RED**

Run: `.venv/bin/pytest -q tests/test_local_service.py::test_main_install_reports_a_short_error_without_a_traceback`

Expected: FAIL because `main` lets `InvalidLocalService` escape as a traceback.

- [ ] **Step 7: Catch known service errors at the CLI boundary**

Import `sys`, wrap the action dispatch inside `main` in `try`, and add:

```python
except InvalidLocalService as error:
    print(f"錯誤：{error}", file=sys.stderr)
    return 2
```

Run: `.venv/bin/pytest -q tests/test_local_service.py::test_main_install_reports_a_short_error_without_a_traceback`

Expected: `1 passed`.

- [ ] **Step 8: Document the exact commands in README**

Add after `快速開始`:

```markdown
## Mac 登入後自動保持開啟

```bash
.venv/bin/python -m daibu.local_service install
.venv/bin/python -m daibu.local_service status
```

工具網址：<http://localhost:8501>

錯誤紀錄位於 `~/Library/Logs/DaibuContentBrain/`。若要移除自動啟動但保留
資料與 API key：

```bash
.venv/bin/python -m daibu.local_service uninstall
```
```

- [ ] **Step 9: Run focused tests and syntax checks**

Run:

```bash
.venv/bin/pytest -q tests/test_local_service.py
.venv/bin/python -m py_compile daibu/local_service.py
git diff --check
```

Expected: `10 passed`; compilation and diff check exit 0.

- [ ] **Step 10: Commit Task 6**

```bash
git add daibu/local_service.py tests/test_local_service.py README.md
git commit -m "feat: manage daibu local service"
```

---

### Task 7: Install on the real Mac and verify automatic recovery

**Files:**
- Modify: `HANDOFF.md`
- Runtime write: `~/Library/LaunchAgents/io.daibu.content-brain.plist`
- Runtime write: `~/Library/Logs/DaibuContentBrain/`
- Conditional runtime write: `.env` copied from `.env.example` only because it is currently absent

**Interfaces:**
- Consumes: `python -m daibu.local_service install|status` from Task 6.
- Produces: a loaded per-user LaunchAgent and an evidence-backed handoff.

- [ ] **Step 1: Calibrate the health check before installation**

Run:

```bash
curl --fail --silent --show-error http://127.0.0.1:8501/_stcore/health
```

Expected before install: connection failure. This proves the check can distinguish the current broken state.

- [ ] **Step 2: Install the real LaunchAgent**

Run:

```bash
.venv/bin/python -m daibu.local_service install
```

Expected: service installed; if `.env` is created, it contains only blank example fields and mode `600`.

- [ ] **Step 3: Poll the condition instead of sleeping blindly**

Run a bounded loop for up to 30 seconds that calls the health endpoint once per second and exits as soon as it returns `ok`.

Expected: `ok` before the deadline.

- [ ] **Step 4: Verify launchctl, port binding, plist, and secrets boundary**

Run:

```bash
.venv/bin/python -m daibu.local_service status
launchctl print "gui/$(id -u)/io.daibu.content-brain"
lsof -nP -iTCP:8501 -sTCP:LISTEN
plutil -lint "$HOME/Library/LaunchAgents/io.daibu.content-brain.plist"
```

Inspect the plist keys and program path. Search the plist and logs for key *names* only; do not print `.env` or any secret value. Expected: loaded, healthy, `127.0.0.1:8501`, valid plist, no API key names in plist or logs.

- [ ] **Step 5: Verify restart behavior from the user's point of view**

Resolve the PID that is listening on 8501, record it, send that exact PID `TERM`, and poll for up to 30 seconds until both conditions hold:

1. 8501 has a different listening PID.
2. `/_stcore/health` returns `ok`.

Expected: a new PID and restored health. Do not kill by broad process-name pattern.

- [ ] **Step 6: Verify the browser page**

Open `http://localhost:8501` in the in-app browser. Confirm the home page renders and has no critical browser/server error. This is a runtime verification, not a frontend redesign, so no visual layout change is expected.

- [ ] **Step 7: Deliver the product understanding checkpoint before full tests**

Explain to the user:

- Product capability: login auto-start and crash recovery.
- User experience: the same localhost link opens without a Terminal command.
- Technical structure: launchd → LaunchAgent → Streamlit → server.py.
- Data flow: project working directory loads `.env`; browser stays local.
- Design reason: macOS-native service is free and reversible.
- Alternative: login shortcut lacks recovery; cloud is available when Mac-off access is needed.
- Security/cost: loopback only, no keys in plist/logs/Git, no subscription.
- Test evidence: focused tests, launchctl, health check, PID replacement, browser.
- Remaining limits: login/awake required; blank `.env` means AI functions still need local key entry.

- [ ] **Step 8: Run the full test suite once**

Run: `.venv/bin/pytest -q`

Expected: no failures; contract tests that require external credentials remain deselected by default.

- [ ] **Step 9: Update HANDOFF.md**

Add the current round at the top with root cause, installed label and paths, exact verification output, automatic-recovery evidence, test count, security boundary, user action for `.env`, and the Mac-on/logged-in/awake limitation. Preserve older records below it.

- [ ] **Step 10: Final verification and commit**

Run:

```bash
.venv/bin/python -m daibu.local_service status
curl --fail --silent --show-error http://127.0.0.1:8501/_stcore/health
git diff --check
git status --short
```

Expected: status loaded and healthy, health `ok`, no whitespace errors, and only intended files staged for this round.

Commit:

```bash
git add HANDOFF.md
git commit -m "docs: record local service verification"
```

- [ ] **Step 11: Push and verify the remote**

Run:

```bash
git push origin main
git rev-parse HEAD
git ls-remote origin refs/heads/main
```

Expected: local HEAD equals the remote `main` hash. There is no production web deployment in this scope; the installed local LaunchAgent is the runtime delivery.
