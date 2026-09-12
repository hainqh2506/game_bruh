"""Run HTTP+WS (uvicorn) and optional Cloudflare Quick Tunnel."""

from __future__ import annotations

import os
import re
import subprocess
import threading
import time
import webbrowser

import uvicorn

from paths import DEFAULT_PORT, LINK_PATH
from server.app import create_app
from server.build import build_play, debug_watch_files
from server.env import debug_enabled
from server.runctl import write_run_status


class ReloadState:
    def __init__(self) -> None:
        self.generation = 0
        self.cond = threading.Condition()

    def bump(self) -> int:
        with self.cond:
            self.generation += 1
            self.cond.notify_all()
            return self.generation

    def wait_after(self, seen: int, timeout: float = 25.0) -> int:
        with self.cond:
            if self.generation > seen:
                return self.generation
            self.cond.wait(timeout=timeout)
            return self.generation


def _mtime(path) -> float:
    try:
        return path.stat().st_mtime
    except FileNotFoundError:
        return 0.0


def watch_play_files(state: ReloadState) -> None:
    files = list(debug_watch_files())
    mtimes = {path: _mtime(path) for path in files}
    print(
        "Reload: ON — sửa play/*.js / *.css; trang tự F5, tunnel giữ nguyên.",
        flush=True,
    )
    while True:
        time.sleep(0.35)
        changed = [path.name for path in files if _mtime(path) != mtimes[path]]
        if not changed:
            continue
        time.sleep(0.15)
        mtimes = {path: _mtime(path) for path in files}
        try:
            build_play(reload=True, refresh_phrases=False)
            gen = state.bump()
            print(f"Reloaded #{gen}: {', '.join(changed)}", flush=True)
        except Exception as exc:
            print(f"Reload failed: {exc}", flush=True)


def serve_play(
    port: int = DEFAULT_PORT,
    tunnel: bool = False,
    reload: bool = True,
    host: str = "0.0.0.0",
) -> None:
    build_play(reload=reload)
    on = debug_enabled()
    state = ReloadState()
    tunnel_url_re = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
    app = create_app(reload=reload, debug=on, reload_state=state)
    tunnel_proc: subprocess.Popen | None = None

    def run_quick_tunnel() -> None:
        nonlocal tunnel_proc
        cmd = [
            "cloudflared",
            "tunnel",
            "--no-autoupdate",
            "--url",
            f"http://127.0.0.1:{port}",
        ]
        print("Starting Cloudflare Quick Tunnel (no login)…", flush=True)
        tunnel_proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert tunnel_proc.stdout is not None
        public = None
        for line in tunnel_proc.stdout:
            print(line.rstrip(), flush=True)
            match = tunnel_url_re.search(line)
            if match and public is None:
                public = match.group(0)
                write_run_status(public_url=public, tunnel_pid=tunnel_proc.pid)
                print("\n========================================", flush=True)
                print(f"  Gửi link này: {public}", flush=True)
                print(f"  Đã ghi: {LINK_PATH}", flush=True)
                print("========================================\n", flush=True)

    display_host = "127.0.0.1" if host in ("0.0.0.0", "::") else host
    url = f"http://{display_host}:{port}/"
    write_run_status(
        local_url=url,
        public_url="",
        port=port,
        debug=on,
        reload=reload,
        python_pid=os.getpid(),
        tunnel_pid="",
        stopped=False,
    )
    print(f"Local: {url}", flush=True)
    print(f"Debug tab: {'ON' if on else 'OFF'}  (DOANCHU_DEBUG=1 to enable)", flush=True)
    print(f"Reload: {'ON' if reload else 'OFF'}  (--no-reload to disable)", flush=True)
    from game.room import HUB

    lim = HUB.limits
    print(f"Rooms:  ON  (WebSocket /ws trên cùng cổng {port})", flush=True)
    print(
        f"Limits: {lim.max_solo} solo · {lim.max_rooms} phòng · "
        f"{lim.max_players}/phòng · {lim.max_party} người phòng "
        f"(DOANCHU_MAX_SOLO / _ROOMS / _PLAYERS / _PARTY)",
        flush=True,
    )
    print(f"Status file: {LINK_PATH}", flush=True)
    if reload:
        threading.Thread(target=watch_play_files, args=(state,), daemon=True).start()
    if tunnel:
        threading.Thread(target=run_quick_tunnel, daemon=True).start()
    else:
        print("Friends: uv run python main.py --tunnel", flush=True)
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        uvicorn.run(app, host=host, port=port, log_level="info")
    except OSError as exc:
        if getattr(exc, "errno", None) == 98:
            raise SystemExit(
                f"Cổng {port} đang bị chiếm (server lần trước chưa tắt).\n"
                f"Tắt bằng:  fuser -k {port}/tcp\n"
                f"Hoặc cổng khác:  uv run python main.py --tunnel --port {port + 1}"
            ) from exc
        raise
    finally:
        if tunnel_proc and tunnel_proc.poll() is None:
            tunnel_proc.terminate()
