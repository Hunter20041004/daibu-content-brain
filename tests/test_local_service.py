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
