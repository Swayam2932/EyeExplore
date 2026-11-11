"""Run the EyeExplore landing site and Dash dashboard behind one HTTP port.

Production prerequisites: install Python requirements, install Node.js, and run
``npm ci`` in ``eyeexplore/`` once. Start the complete application with
``python main.py``. The public port is selected with the ``PORT`` environment
variable (defaults to 8000).
"""

from __future__ import annotations

import atexit
import os
import signal
import secrets
import subprocess
import sys
import time
from pathlib import Path

import requests
from flask import Flask, Response, abort, request
from waitress import serve


ROOT = Path(__file__).resolve().parent
LANDING_DIR = ROOT / "eyeexplore"
DASHBOARD_PREFIX = "/dashboard-app"
LANDING_PORT = int(os.environ.get("LANDING_INTERNAL_PORT", "3000"))
DASHBOARD_PORT = int(os.environ.get("DASHBOARD_INTERNAL_PORT", "8050"))
PUBLIC_PORT = int(os.environ.get("PORT", "8000"))
STARTUP_TIMEOUT = float(os.environ.get("STARTUP_TIMEOUT", "180"))

processes: list[subprocess.Popen] = []


def _stop_processes() -> None:
    for process in reversed(processes):
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                process.terminate()
    for process in reversed(processes):
        if process.poll() is None:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


atexit.register(_stop_processes)


def _run(command: list[str], *, cwd: Path, env: dict[str, str]) -> None:
    subprocess.run(command, cwd=cwd, env=env, check=True)


def _start(command: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.Popen:
    process = subprocess.Popen(command, cwd=cwd, env=env, start_new_session=True)
    processes.append(process)
    return process


def _wait_for_service(url: str, process: subprocess.Popen, name: str) -> None:
    deadline = time.monotonic() + STARTUP_TIMEOUT
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"{name} exited during startup (status {process.returncode}).")
        try:
            response = requests.get(url, timeout=2)
            if response.status_code < 500:
                return
        except requests.RequestException:
            time.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for {name} at {url}.")


def _proxy(target: str, *, strip_dashboard_prefix: bool = False) -> Response:
    path = request.full_path
    if path.endswith("?"):
        path = path[:-1]
    if strip_dashboard_prefix:
        path = path[len(DASHBOARD_PREFIX):] or "/"
        if not path.startswith("/"):
            path = "/" + path
    url = target.rstrip("/") + path
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in {"host", "content-length", "connection"}
    }
    try:
        upstream = requests.request(
            method=request.method,
            url=url,
            headers=headers,
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False,
            stream=True,
            timeout=(10, 300),
        )
    except requests.RequestException as exc:
        abort(502, description=f"Upstream application unavailable: {exc}")

    excluded = {
        "connection",
        "keep-alive",
        "proxy-connection",
        "transfer-encoding",
        "te",
        "trailer",
        "upgrade",
        "content-encoding",
        "content-length",
    }
    # Connection may nominate additional hop-by-hop headers.
    excluded.update(
        header.strip().lower()
        for header in upstream.headers.get("Connection", "").split(",")
        if header.strip()
    )
    response_headers = [
        (key, value) for key, value in upstream.headers.items()
        if key.lower() not in excluded
    ]
    def body():
        try:
            yield from upstream.iter_content(chunk_size=64 * 1024)
        finally:
            upstream.close()

    return Response(
        body(),
        status=upstream.status_code,
        headers=response_headers,
    )


server = Flask(__name__)
server.secret_key = os.environ.get("STUDY_SECRET_KEY") or secrets.token_hex(32)
server.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("STUDY_COOKIE_SECURE", "0") == "1",
    MAX_CONTENT_LENGTH=64 * 1024,
)

from UserStudy import blueprint as user_study_blueprint

server.register_blueprint(user_study_blueprint)


@server.route(f"{DASHBOARD_PREFIX}", defaults={"path": ""}, methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
@server.route(f"{DASHBOARD_PREFIX}/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
def dashboard_proxy(path: str) -> Response:
    return _proxy(f"http://127.0.0.1:{DASHBOARD_PORT}", strip_dashboard_prefix=True)


@server.route("/", defaults={"path": ""}, methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
@server.route("/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
def landing_proxy(path: str) -> Response:
    return _proxy(f"http://127.0.0.1:{LANDING_PORT}")


def main() -> None:
    if not LANDING_DIR.is_dir():
        raise SystemExit(f"Landing site directory not found: {LANDING_DIR}")
    if not (LANDING_DIR / "node_modules").is_dir():
        raise SystemExit("Node dependencies are missing. Run `npm ci` in eyeexplore/ first.")

    env = os.environ.copy()
    env["DASHBOARD_PREFIX"] = DASHBOARD_PREFIX
    dash_process = _start(
        [sys.executable, str(ROOT / "app.py")], cwd=ROOT,
        env={**env, "DASH_HOST": "127.0.0.1", "DASH_PORT": str(DASHBOARD_PORT), "DASH_DEBUG": "0"},
    )
    _wait_for_service(
        f"http://127.0.0.1:{DASHBOARD_PORT}/",
        dash_process,
        "Dash dashboard",
    )

    _run(["npm", "run", "build"], cwd=LANDING_DIR, env=env)
    landing_process = _start(
        ["npm", "run", "start", "--", "--hostname", "127.0.0.1", "--port", str(LANDING_PORT)],
        cwd=LANDING_DIR,
        env={**env, "HOSTNAME": "127.0.0.1", "PORT": str(LANDING_PORT)},
    )
    _wait_for_service(f"http://127.0.0.1:{LANDING_PORT}/", landing_process, "Next.js landing site")

    print(f"EyeExplore is available at http://localhost:{PUBLIC_PORT}", flush=True)
    print(f"Dashboard route: {DASHBOARD_PREFIX}/", flush=True)
    print("Participant study: /user-study/", flush=True)
    try:
        serve(server, host="0.0.0.0", port=PUBLIC_PORT, threads=int(os.environ.get("WEB_THREADS", "8")))
    finally:
        _stop_processes()


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda _signum, _frame: (_stop_processes(), sys.exit(0)))
    try:
        main()
    except KeyboardInterrupt:
        pass
