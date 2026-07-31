from starlette.testclient import TestClient


def test_nested_streamlit_health_routes_redirect_to_root():
    from server import app

    with TestClient(app) as client:
        response = client.get(
            "/%E9%81%B8%E9%A1%8C/_stcore/health",
            follow_redirects=False,
        )
        host_config = client.get(
            "/%E9%81%B8%E9%A1%8C/_stcore/host-config?x=1&y=2",
            follow_redirects=False,
        )

    assert response.status_code == 307
    assert response.headers["location"] == "/_stcore/health"
    assert host_config.status_code == 307
    assert host_config.headers["location"] == "/_stcore/host-config?x=1&y=2"
