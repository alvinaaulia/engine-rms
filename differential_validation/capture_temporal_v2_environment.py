#!/usr/bin/env python3
from __future__ import annotations

import json
import ctypes
import locale
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

def command(*args: str) -> str:
    return subprocess.check_output(args, text=True, errors="replace").strip()


def powershell(expression: str) -> str:
    try:
        return command("powershell.exe", "-NoProfile", "-Command", expression)
    except Exception:
        return "NOT_OBSERVABLE"


def memory_status() -> tuple[int | None, int | None]:
    if os.name == "nt":
        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("length", ctypes.c_ulong), ("memory_load", ctypes.c_ulong),
                ("total_physical", ctypes.c_ulonglong), ("available_physical", ctypes.c_ulonglong),
                ("total_page_file", ctypes.c_ulonglong), ("available_page_file", ctypes.c_ulonglong),
                ("total_virtual", ctypes.c_ulonglong), ("available_virtual", ctypes.c_ulonglong),
                ("available_extended_virtual", ctypes.c_ulonglong),
            ]
        status = MemoryStatus()
        status.length = ctypes.sizeof(MemoryStatus)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return status.total_physical, status.available_physical
    return None, None


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: capture_temporal_v2_environment.py RUN_DIR DATABASE_JSON")
    run = Path(sys.argv[1])
    database = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8-sig"))
    total_memory, available_memory = memory_status()
    cpu = powershell("(Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty Name)")
    storage = powershell("(Get-PhysicalDisk | Select-Object -First 1 -ExpandProperty MediaType)")
    data = {
        "observation_type": "controlled local performance observation",
        "os": platform.platform(),
        "cpu_model": cpu,
        "logical_cpu": os.cpu_count(),
        "physical_memory_bytes": total_memory,
        "available_memory_bytes": available_memory,
        "php_version": command("php", "-r", "echo PHP_VERSION;"),
        "go_version": command("go", "version"),
        "python_version": platform.python_version(),
        "mysql_server_version": database.get("version"),
        "database_name": database.get("database_name"),
        "database_collation": database.get("collation_name"),
        "database_timezone": database.get("server_timezone"),
        "storage_type": storage,
        "canonical_timezone": "UTC",
        "local_timezone": time.tzname[0],
        "locale": locale.getlocale(),
    }
    (run / "environment.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(data, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
