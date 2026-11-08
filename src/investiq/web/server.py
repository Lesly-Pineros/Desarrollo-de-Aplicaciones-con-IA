"""Single-process, loopback-only web server for the local InvestiQ pilot."""

from __future__ import annotations

import argparse
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
import json
import logging
from time import perf_counter
from urllib.parse import urlsplit

from sqlmodel import Session

from investiq.data.database import create_db, ensure_sqlite_parent, make_engine, seed_instruments
from investiq.logging_config import configure_logging, log_stage, log_unexpected, request_context
from investiq.settings import get_settings
from investiq.web.service import InvalidRequest, WebService
from investiq.web.sessions import SessionCapacityError, SessionStore

COOKIE_NAME = "investiq_session"
MAX_BODY_BYTES = 16 * 1024
logger = logging.getLogger(__name__)
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.css": ("app.css", "text/css; charset=utf-8"),
    "/robot-theme.css": ("robot-theme.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/media/profesor-investiq.mp4": ("media/profesor-investiq.mp4", "video/mp4"),
    "/media/profesor-investiq.png": ("media/profesor-investiq.png", "image/png"),
    "/fonts/fraunces.ttf": ("fonts/fraunces.ttf", "font/ttf"),
    "/fonts/manrope.ttf": ("fonts/manrope.ttf", "font/ttf"),
    "/fonts/fraunces-OFL.txt": ("fonts/fraunces-OFL.txt", "text/plain; charset=utf-8"),
    "/fonts/manrope-OFL.txt": ("fonts/manrope-OFL.txt", "text/plain; charset=utf-8"),
}


class LocalWebServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, service: WebService, store: SessionStore | None = None):
        if address[0] not in {"127.0.0.1", "localhost"}:
            raise ValueError("The local pilot only binds to loopback")
        self.service = service
        self.sessions = store or SessionStore()
        super().__init__(address, WebHandler)


class WebHandler(BaseHTTPRequestHandler):
    server: LocalWebServer
    server_version = "InvestiQ"
    sys_version = ""

    def log_message(self, format, *args) -> None:
        # URLs, prompts, provider errors and configuration never enter access logs.
        pass

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(15)

    def _headers(self, status: int, mime: str, length: int, cookie: str | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; "
                         "style-src 'self'; font-src 'self'; img-src 'self' data:; media-src 'self'; "
                         "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()

    def _json(self, status: int, value: dict, cookie: str | None = None) -> None:
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self._headers(status, "application/json; charset=utf-8", len(body), cookie)
        self.wfile.write(body)

    def _authority(self, value: str):
        try:
            parsed = urlsplit("//" + value)
            if (parsed.hostname not in {"localhost", "127.0.0.1"}
                    or parsed.port != self.server.server_port
                    or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment):
                return None
            return parsed.hostname, parsed.port
        except ValueError:
            return None

    def _local_request(self, *, post: bool = False) -> bool:
        hosts = self.headers.get_all("Host", [])
        authority = self._authority(hosts[0]) if len(hosts) == 1 else None
        if authority is None:
            self._json(403, {"error": "Abre la aplicación desde su dirección local."})
            return False
        if post:
            try:
                origin = urlsplit(self.headers.get("Origin", ""))
                valid = origin.scheme == "http" and self._authority(origin.netloc) == authority
                valid = valid and not (origin.path or origin.query or origin.fragment)
            except ValueError:
                valid = False
            if not valid or self.headers.get("Sec-Fetch-Site") == "cross-site":
                self._json(403, {"error": "Envía la consulta desde la página local de InvestiQ."})
                return False
        return True

    def _session_token(self) -> str | None:
        try:
            cookie = SimpleCookie()
            cookie.load(self.headers.get("Cookie", ""))
            entry = cookie.get(COOKIE_NAME)
            return entry.value if entry else None
        except CookieError:
            return None

    def _run_api(self, path: str, payload: dict | None = None) -> None:
        route = {"/api/bootstrap": "bootstrap", "/api/chat": "chat",
                 "/api/session/reset": "reset", "/api/memory": "memory"}.get(path, "other")
        with request_context():
            started = perf_counter()
            status = 200
            logger.info("http.request.start method=%s route=%s",
                        "GET" if route == "bootstrap" else "POST", route)
            try:
                with self.server.sessions.acquire(self._session_token()) as (browser, created):
                    with log_stage(logger, f"http.{route}"):
                        if path == "/api/bootstrap":
                            result = self.server.service.bootstrap(browser)
                        elif path == "/api/chat":
                            result = self.server.service.chat(browser, payload)
                        elif path == "/api/session/reset":
                            result = self.server.service.reset(browser, payload)
                        else:
                            result = self.server.service.memory(browser, payload)
                    cookie = (f"{COOKIE_NAME}={browser.token}; Path=/; HttpOnly; SameSite=Strict"
                              if created else None)
                    self._json(200, result, cookie)
            except InvalidRequest as error:
                status = 400
                logger.warning("http.request.rejected route=%s reason=invalid_request", route)
                self._json(400, {"error": str(error)})
            except SessionCapacityError:
                status = 503
                logger.warning("http.request.rejected route=%s reason=session_capacity", route)
                self._json(503, {"error": "Hay varias conversaciones en curso. Inténtalo de nuevo en un momento."})
            except Exception as error:
                status = 500
                log_unexpected(logger, f"http.{route}", error)
                self._json(500, {"error": "No pude completar la consulta. Inténtalo de nuevo; si sigue pasando, reinicia la aplicación."})
            finally:
                elapsed_ms = round((perf_counter() - started) * 1000)
                logger.info("http.request.done route=%s status=%d duration_ms=%d", route, status, elapsed_ms)

    def do_GET(self) -> None:
        if not self._local_request():
            return
        path = urlsplit(self.path).path
        if path == "/api/health":
            self._json(200, {"status": "ok"})
        elif path == "/api/bootstrap":
            self._run_api(path)
        elif path in STATIC_FILES:
            name, mime = STATIC_FILES[path]
            try:
                body = files("investiq.web").joinpath("static", name).read_bytes()
            except (FileNotFoundError, OSError):
                self._json(404, {"error": "No encontré ese recurso."})
                return
            self._headers(200, mime, len(body))
            self.wfile.write(body)
        else:
            self._json(404, {"error": "No encontré esa página."})

    def do_POST(self) -> None:
        if not self._local_request(post=True):
            return
        path = urlsplit(self.path).path
        if path not in {"/api/chat", "/api/session/reset", "/api/memory"}:
            self._json(404, {"error": "No encontré esa acción."})
            return
        if self.headers.get("Transfer-Encoding"):
            self._json(400, {"error": "No pude leer el mensaje. Vuelve a intentarlo."})
            return
        lengths = self.headers.get_all("Content-Length", [])
        if len(lengths) != 1 or not lengths[0].isascii() or not lengths[0].isdigit():
            self._json(411, {"error": "No pude leer el tamaño del mensaje."})
            return
        length = int(lengths[0])
        if length > MAX_BODY_BYTES:
            self._json(413, {"error": "El mensaje es demasiado grande. Divídelo e inténtalo de nuevo."})
            return
        if self.headers.get_content_type() != "application/json":
            self._json(415, {"error": "Envía el mensaje desde el chat de InvestiQ."})
            return
        try:
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError
        except (ValueError, UnicodeDecodeError, RecursionError):
            self._json(400, {"error": "No pude leer el mensaje. Vuelve a intentarlo."})
            return
        self._run_api(path, payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="InvestiQ: web educativa local")
    parser.add_argument("--host", choices=("127.0.0.1", "localhost"), default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    if not 0 <= args.port <= 65535:
        parser.error("--port debe estar entre 0 y 65535")
    engine = None
    configure_logging()
    logger.info("startup.begin component=web")
    try:
        settings = get_settings()
        configure_logging(settings.log_level)
        logger.info("startup.configuration mode=%s log_level=%s",
                    "configured" if settings.has_nvidia_key else "local", settings.log_level)
        with log_stage(logger, "startup.database"):
            ensure_sqlite_parent(settings.database_url)
            engine = create_db(make_engine(settings.database_url))
            with Session(engine) as db:
                seed_instruments(db)
    except Exception as error:
        log_unexpected(logger, "startup", error)
        print("No pude iniciar InvestiQ. Revisa la configuración local y el acceso a la base de datos.")
        if engine is not None:
            engine.dispose()
        return 1
    try:
        server = LocalWebServer((args.host, args.port), WebService(engine, settings))
    except OSError as error:
        log_unexpected(logger, "startup.bind", error)
        print("No pude abrir el puerto local. Prueba otro con --port 8001.")
        engine.dispose()
        return 1
    logger.info("startup.ready host=%s port=%d", args.host, server.server_port)
    print(f"InvestiQ listo en http://{args.host}:{server.server_port} (Ctrl+C para salir).", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("shutdown.begin component=web")
        server.server_close()
        engine.dispose()
        logger.info("shutdown.done component=web")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
