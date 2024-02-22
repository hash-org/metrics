import subprocess
from pathlib import Path


def checkout_git_revision(repo: Path, revision: str):
    result = subprocess.Popen(["git", "checkout", revision], cwd=repo).wait()

    if result != 0:
        raise RuntimeError(f"Could not checkout {revision=}")
