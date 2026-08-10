"""Install and inspect Daibu's per-user macOS LaunchAgent."""

from __future__ import annotations

import os
import plistlib
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


LABEL = "io.daibu.content-brain"
PORT = 8501


class InvalidLocalService(ValueError):
    pass


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


def validate_project(paths: ServicePaths) -> None:
    required = (paths.streamlit, paths.server, paths.env_example)
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise InvalidLocalService(
            "無法安裝呆一布背景服務，缺少：" + "、".join(missing)
        )


def ensure_env_file(paths: ServicePaths) -> bool:
    if paths.env_file.exists():
        return False
    shutil.copyfile(paths.env_example, paths.env_file)
    os.chmod(paths.env_file, 0o600)
    return True


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


def install(
    paths: ServicePaths,
    command: Command = default_command,
) -> bool:
    validate_project(paths)
    created_env = ensure_env_file(paths)
    _write_plist(paths)
    command(["launchctl", "bootout", service_target()])
    if command(
        ["launchctl", "bootstrap", service_domain(), str(paths.plist)]
    ):
        raise InvalidLocalService("macOS 無法載入呆一布背景服務")
    if command(["launchctl", "kickstart", "-k", service_target()]):
        raise InvalidLocalService("macOS 無法啟動呆一布背景服務")
    return created_env


@dataclass(frozen=True)
class ServiceStatus:
    loaded: bool
    healthy: bool
    occupied_by_other_process: bool
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
    healthy = health(url)
    return ServiceStatus(
        loaded,
        healthy,
        healthy and not loaded,
        paths.plist,
        paths.stderr_log,
    )


def uninstall(
    paths: ServicePaths,
    command: Command = default_command,
) -> None:
    command(["launchctl", "bootout", service_target()])
    paths.plist.unlink(missing_ok=True)
