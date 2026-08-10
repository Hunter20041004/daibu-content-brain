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
