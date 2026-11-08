import base64
from http.client import HTTPConnection
import json
import threading

import pytest
from sqlmodel import Session

from investiq.data.database import create_db, make_engine, seed_instruments
from investiq.settings import Settings
from investiq.web.server import LocalWebServer, MAX_BODY_BYTES
from investiq.web.service import WebService


@pytest.fixture
def web(tmp_path):
    settings = Settings(_env_file=None, database_url=f"sqlite:///{tmp_path / 'api.db'}",
                        nvidia_api_key=None, twelve_data_api_key=None, marketaux_api_key=None)
    engine = create_db(make_engine(settings.database_url))
    with Session(engine) as db:
        seed_instruments(db)
    server = LocalWebServer(("127.0.0.1", 0), WebService(engine, settings))
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    thread.join(timeout=2)
    server.server_close()
    engine.dispose()


def request(web, method="GET", path="/api/bootstrap", payload=None, *, headers=None, raw=None):
    connection = HTTPConnection("127.0.0.1", web.server_port, timeout=5)
    request_headers = {"Origin": f"http://127.0.0.1:{web.server_port}"}
    if payload is not None:
        raw = json.dumps(payload).encode()
        request_headers["Content-Type"] = "application/json"
    if headers:
        request_headers.update(headers)
    connection.request(method, path, body=raw, headers=request_headers)
    response = connection.getresponse()
    body = response.read()
    result = response.status, dict(response.getheaders()), body
    connection.close()
    return result


def test_api_roundtrip_cookie_reload_and_new_browser(web):
    status, headers, body = request(web)
    assert status == 200
    bootstrap = json.loads(body)
    assert len(bootstrap["instruments"]) == 20
    cookie = headers["Set-Cookie"]
    assert "HttpOnly" in cookie and "SameSite=Strict" in cookie
    cookie = cookie.split(";")[0]
    status, _, body = request(web, "POST", "/api/chat", {"message": "volatilidad"},
                              headers={"Cookie": cookie})
    assert status == 200
    assert "No es asesoría financiera" in json.loads(body)["response"]["answer"]
    _, _, body = request(web, headers={"Cookie": cookie})
    assert len(json.loads(body)["messages"]) == 2
    _, new_headers, body = request(web)
    assert json.loads(body)["messages"] == []
    assert new_headers["Set-Cookie"].split(";")[0] != cookie
    status, _, body = request(web, "POST", "/api/session/reset", {}, headers={"Cookie": cookie})
    assert status == 200 and json.loads(body)["messages"] == []


@pytest.mark.parametrize("headers", [
    {"Origin": "https://evil.example"}, {"Origin": "null"}, {"Origin": ""},
    {"Origin": "http://localhost:9999"}, {"Sec-Fetch-Site": "cross-site"},
    {"Host": "attacker.example"},
])
def test_api_rejects_untrusted_origins_and_hosts(web, headers):
    status, _, body = request(web, "POST", "/api/chat", {"message": "hola"}, headers=headers)
    assert status == 403
    assert "error" in json.loads(body)


@pytest.mark.parametrize("path", ["/.env", "/../.env", "/%2e%2e/.env", "/server.py", "/api/nope"])
def test_static_routes_never_expose_arbitrary_files(web, path):
    status, _, body = request(web, path=path)
    assert status == 404
    assert "error" in json.loads(body)


def test_payload_size_format_and_type_checks(web):
    status, _, _ = request(web, "POST", "/api/chat", raw=b"x" * (MAX_BODY_BYTES + 1),
                           headers={"Content-Type": "application/json"})
    assert status == 413
    status, _, _ = request(web, "POST", "/api/chat", raw=b"hola",
                           headers={"Content-Type": "text/plain"})
    assert status == 415
    for invalid in (b"not-json", b"[]", b"\xff"):
        status, _, _ = request(web, "POST", "/api/chat", raw=invalid,
                               headers={"Content-Type": "application/json"})
        assert status == 400
    status, _, _ = request(web, "POST", "/api/chat", {"message": "x" * 2001})
    assert status == 400


def test_provider_error_is_safe_and_bootstrap_has_no_secret_config(web, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("fictional-private-token-do-not-expose")

    monkeypatch.setattr(web.service, "chat", fail)
    status, headers, body = request(web, "POST", "/api/chat", {"message": "hola"})
    assert status == 500
    assert b"fictional-private-token" not in body
    assert b"Traceback" not in body
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
    status, _, body = request(web)
    assert status == 200
    assert "nvidia_api_key" not in json.loads(body)


def test_protected_routes_require_valid_basic_auth(web):
    web.public = True
    web.access_password = "correct-horse-battery"
    web.public_hostname = "investiq-test.onrender.com"
    base_headers = {"Host": "investiq-test.onrender.com", "Origin": "https://investiq-test.onrender.com",
                    "X-Forwarded-Proto": "https"}
    status, headers, body = request(web, headers=base_headers)
    assert status == 401
    assert 'Basic realm="InvestiQ POC"' in headers["WWW-Authenticate"]
    assert b"correct-horse" not in body

    good = base64.b64encode(b"investiq:correct-horse-battery").decode("ascii")
    status, headers, body = request(web, headers={**base_headers, "Authorization": f"Basic {good}"})
    assert status == 200
    assert "Secure" in headers["Set-Cookie"]
    assert len(json.loads(body)["instruments"]) == 20

    bad = base64.b64encode(b"investiq:incorrect").decode("ascii")
    status, _, _ = request(web, headers={**base_headers, "Authorization": f"Basic {bad}"})
    assert status == 401
    status, _, body = request(web, path="/api/health", headers={"Host": "investiq-test.onrender.com"})
    assert status == 200


def test_pilot_server_refuses_network_binding():
    with pytest.raises(ValueError, match="loopback"):
        LocalWebServer(("0.0.0.0", 8000), None)


def test_render_public_server_requires_access_password():
    with pytest.raises(ValueError, match="INVESTIQ_ACCESS_PASSWORD"):
        LocalWebServer(("0.0.0.0", 8000), None, public=True)
