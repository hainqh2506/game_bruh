"""PID / tunnel status files and stop."""

from __future__ import annotations

import json
import os
import signal
import subprocess
from datetime import datetime, timezone

from paths import LEGACY_PORTS, LINK_PATH, RUN_DIR, STATUS_PATH


def write_run_status(**fields: object) -> dict:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    data: dict = {}
    if STATUS_PATH.exists():
        try:
            data = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
    data.update(fields)
    data["updated_at"] = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    STATUS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    public = data.get("public_url") or "(đang tạo tunnel…)"
    debug = "ON" if data.get("debug") else "OFF"
    reload_on = "ON" if data.get("reload") else "OFF"
    LINK_PATH.write_text(
        "\n".join(
            [
                "Đoán Chữ Unlimited",
                "",
                f"Public:  {public}",
                f"Local:   {data.get('local_url', '')}",
                f"Port:    {data.get('port', '')}",
                f"Debug:   {debug}",
                f"Reload:  {reload_on}",
                f"Python:  pid {data.get('python_pid', '')}",
                f"Tunnel:  pid {data.get('tunnel_pid', '') or '-'}",
                f"Updated: {data.get('updated_at', '')}",
                "",
                "Sửa play/*.js rồi đợi trang tự F5 — không chạy lại make dev.",
                "Tắt:  uv run python main.py --stop",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return data


def _kill_pid(pid: int) -> None:
    try:
        os.kill(pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        return


def stop_run(extra_ports: tuple[int, ...] = ()) -> None:
    ports: set[int] = set(extra_ports)
    pids: set[int] = set()
    if STATUS_PATH.exists():
        try:
            data = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
        if data.get("port"):
            ports.add(int(data["port"]))
        for key in ("python_pid", "tunnel_pid"):
            if data.get(key):
                pids.add(int(data[key]))
    ports.update(LEGACY_PORTS)
    for pid in pids:
        _kill_pid(pid)
    for port in ports:
        subprocess.run(
            ["fuser", "-k", f"{port}/tcp"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    subprocess.run(
        ["pkill", "-f", "cloudflared tunnel --no-autoupdate --url http://127.0.0.1:"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if STATUS_PATH.exists() or LINK_PATH.exists():
        write_run_status(public_url="", python_pid="", tunnel_pid="", stopped=True)
    print("Đã tắt server/tunnel cũ.", flush=True)
