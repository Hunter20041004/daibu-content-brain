from daibu import local_service
import pytest


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
