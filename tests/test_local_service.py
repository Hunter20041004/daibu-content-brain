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
    assert plist["StandardOutPath"].endswith(
        "/DaibuContentBrain/stdout.log"
    )
    assert plist["StandardErrorPath"].endswith(
        "/DaibuContentBrain/stderr.log"
    )
