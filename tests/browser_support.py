from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import socket
import subprocess
import time
from urllib.error import URLError
from urllib.request import urlopen


PROJECT_ROOT = Path(__file__).parents[1]


def _free_port() -> int:
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        return int(server.getsockname()[1])


@contextmanager
def running_streamlit(tmp_path: Path, seed_fn):
    database_path = tmp_path / "browser.db"
    logo_path = tmp_path / "logos"
    seed_fn(database_path, logo_path)
    port = _free_port()
    environment = os.environ.copy()
    environment.update(
        {
            "DAIBU_DB_PATH": str(database_path),
            "DAIBU_LOGO_DIR": str(logo_path),
            "PYTHON_DOTENV_DISABLED": "1",
        }
    )
    process = subprocess.Popen(
        [
            str(PROJECT_ROOT / ".venv/bin/streamlit"),
            "run",
            str(PROJECT_ROOT / "app.py"),
            "--server.headless=true",
            f"--server.port={port}",
            "--server.address=127.0.0.1",
            "--browser.gatherUsageStats=false",
        ],
        cwd=PROJECT_ROOT,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    health = f"http://127.0.0.1:{port}/_stcore/health"
    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if process.poll() is not None:
                detail = process.stderr.read() if process.stderr else ""
                raise RuntimeError(f"Streamlit 提前結束：{detail[-1000:]}")
            try:
                with urlopen(health, timeout=1) as response:
                    if response.status == 200:
                        break
            except (URLError, TimeoutError):
                time.sleep(0.1)
        else:
            raise RuntimeError("Streamlit 在 20 秒內沒有啟動")
        yield f"http://127.0.0.1:{port}"
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
