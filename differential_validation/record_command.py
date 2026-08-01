"""Run a command and persist stdout/stderr plus strict execution metadata."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from evidence import PARSER_VERSION


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--cwd", type=Path, required=True)
    parser.add_argument("--evidence-file", help="Existing command-produced evidence file, relative to output-dir")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("command is required after --")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = args.output_dir / f"{args.name}.stdout.log"
    stderr_path = args.output_dir / f"{args.name}.stderr.log"
    meta_path = args.output_dir / f"{args.name}.meta.json"
    started = datetime.now(timezone.utc)
    monotonic = time.perf_counter()
    with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open("w", encoding="utf-8") as stderr:
        completed = subprocess.run(command, cwd=args.cwd, stdout=stdout, stderr=stderr, text=True)
    finished = datetime.now(timezone.utc)
    meta = {
        "evidence_file": args.evidence_file or stdout_path.name,
        "stdout_file": stdout_path.name,
        "stderr_file": stderr_path.name,
        "parser_version": PARSER_VERSION,
        "command": command,
        "exit_code": completed.returncode,
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "duration_seconds": round(time.perf_counter() - monotonic, 6),
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    sys.exit(completed.returncode)


if __name__ == "__main__":
    main()
