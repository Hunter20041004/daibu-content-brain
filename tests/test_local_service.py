import plistlib

import pytest

from daibu import local_service


def _runnable_paths(tmp_path):
    paths = local_service.resolve_paths(
        tmp_path / "project",
        tmp_path / "home",
    )
    paths.streamlit.parent.mkdir(parents=True)
    paths.streamlit.write_text("#!/bin/sh\n", encoding="utf-8")
    paths.server.write_text("# server\n", encoding="utf-8")
    paths.env_example.write_text("GEMINI_API_KEY=\n", encoding="utf-8")
    return paths


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
    assert plist["StandardOutPath"].endswith(
        "/DaibuContentBrain/stdout.log"
    )
    assert plist["StandardErrorPath"].endswith(
        "/DaibuContentBrain/stderr.log"
    )


def test_validate_project_lists_every_missing_runtime_file(tmp_path):
    paths = local_service.resolve_paths(
        tmp_path / "project",
        tmp_path / "home",
    )

    with pytest.raises(local_service.InvalidLocalService) as error:
        local_service.validate_project(paths)

    message = str(error.value)
    assert str(paths.streamlit) in message
    assert str(paths.server) in message
    assert str(paths.env_example) in message


def test_ensure_env_file_copies_the_example_with_owner_only_permissions(
    tmp_path,
):
    paths = local_service.resolve_paths(
        tmp_path / "project",
        tmp_path / "home",
    )
    paths.project_root.mkdir(parents=True)
    paths.env_example.write_text("GEMINI_API_KEY=\n", encoding="utf-8")

    created = local_service.ensure_env_file(paths)

    assert created is True
    assert paths.env_file.read_text(encoding="utf-8") == "GEMINI_API_KEY=\n"
    assert paths.env_file.stat().st_mode & 0o777 == 0o600


def test_ensure_env_file_never_replaces_an_existing_secret_file(tmp_path):
    paths = local_service.resolve_paths(
        tmp_path / "project",
        tmp_path / "home",
    )
    paths.project_root.mkdir(parents=True)
    paths.env_example.write_text("GEMINI_API_KEY=\n", encoding="utf-8")
    paths.env_file.write_text(
        "GEMINI_API_KEY=existing-local-value\n",
        encoding="utf-8",
    )

    created = local_service.ensure_env_file(paths)

    assert created is False
    assert paths.env_file.read_text(encoding="utf-8") == (
        "GEMINI_API_KEY=existing-local-value\n"
    )


def test_install_writes_the_plist_then_reloads_and_starts_the_service(
    tmp_path,
):
    paths = _runnable_paths(tmp_path)
    calls = []

    created_env = local_service.install(
        paths,
        command=lambda args: calls.append(args) or 0,
    )

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


def test_status_requires_both_launchctl_and_the_health_endpoint(tmp_path):
    paths = _runnable_paths(tmp_path)
    paths.launch_agent_dir.mkdir(parents=True)
    paths.plist.write_bytes(plistlib.dumps(local_service.build_plist(paths)))
    calls = []

    result = local_service.status(
        paths,
        command=lambda args: calls.append(args) or 0,
        health=lambda url: (
            url == "http://127.0.0.1:8501/_stcore/health"
        ),
    )

    assert result.loaded is True
    assert result.healthy is True
    assert result.plist_path == paths.plist
    assert result.stderr_log == paths.stderr_log
    assert calls == [
        ["launchctl", "print", local_service.service_target()]
    ]


def test_status_identifies_a_healthy_listener_not_owned_by_the_launch_agent(
    tmp_path,
):
    paths = _runnable_paths(tmp_path)

    result = local_service.status(
        paths,
        command=lambda _args: 1,
        health=lambda _url: True,
    )

    assert result.loaded is False
    assert result.healthy is True
    assert result.occupied_by_other_process is True


def test_uninstall_removes_only_the_service_plist(tmp_path):
    paths = _runnable_paths(tmp_path)
    paths.launch_agent_dir.mkdir(parents=True)
    paths.plist.write_text("plist", encoding="utf-8")
    paths.env_file.write_text(
        "GEMINI_API_KEY=keep-me\n",
        encoding="utf-8",
    )
    database = paths.project_root / "daibu.db"
    database.write_bytes(b"database")
    paths.log_dir.mkdir(parents=True)
    paths.stderr_log.write_text("old log", encoding="utf-8")
    calls = []

    local_service.uninstall(
        paths,
        command=lambda args: calls.append(args) or 0,
    )

    assert calls == [
        ["launchctl", "bootout", local_service.service_target()]
    ]
    assert not paths.plist.exists()
    assert paths.env_file.read_text(encoding="utf-8") == (
        "GEMINI_API_KEY=keep-me\n"
    )
    assert database.read_bytes() == b"database"
    assert paths.stderr_log.read_text(encoding="utf-8") == "old log"
