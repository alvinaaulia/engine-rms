"""Assemble a source-complete, dependency-light review bundle from Git-tracked files."""
from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENGINE = ROOT.parent
LARAVEL = ENGINE.parent / "papa-website-v2"


def archive(repo: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as handle:
        archive_path = Path(handle.name)
    try:
        subprocess.run(["git", "archive", "--format=zip", "-o", str(archive_path), "HEAD"], cwd=repo, check=True)
        shutil.unpack_archive(archive_path, target)
    finally:
        archive_path.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise RuntimeError(f"output must be absent or empty: {output}")
    archive(ENGINE, output / "engine-rms")
    archive(LARAVEL, output / "laravel")
    shutil.copytree(output / "engine-rms" / "differential_validation", output / "differential-validation")
    shutil.copytree(ROOT / "runs", output / "runs")
    for name in (
        "README.md", "LICENSE-or-ACCESS-NOTE.md", ".env.example", "Makefile",
        "docker-compose.yml", "Dockerfile.go", "Dockerfile.laravel",
        "Dockerfile.validation", "artifact-manifest.json",
    ):
        shutil.copy2(ROOT / "artifact" / name, output / name)
    print(output)


if __name__ == "__main__":
    main()
