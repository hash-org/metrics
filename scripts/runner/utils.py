import os
import shutil
import platform
from subprocess import Popen, PIPE
from pathlib import Path
from typing import Literal, Union, Optional

from options import TEMP_DIR


def checkout_git_revision(repo: Path, revision: str):
    """
    Checkout the given repository revision, assuming that the repository and
    revision both exist.

    :param repo: Path to the repository to checkout.
    :param revision: The revision number.
    :return: Nothing.
    """
    result = Popen(["git", "checkout", revision], cwd=repo).wait()

    if result != 0:
        raise RuntimeError(f"Could not checkout {revision=}")


def revision_exists(repo: Path, revision: str) -> bool:
    """
    Check if the given revision number exists for the given repository.

    :param repo: The path to the repository.
    :param revision: The revision identifier.
    :return: True if exists, False otherwise.
    """
    result = Popen(["git", "cat-file", "-e", revision], cwd=repo).wait()

    return result == 0


type EntryKind = Literal["file", "revision"]


class Entry:
    kind: EntryKind
    data: str
    name: str

    def __init__(self, kind: EntryKind, data: str, name: str):
        self.kind = kind
        self.data = data
        self.name = name


def to_entry(
    repo: Path, name: str, path_or_revision: Union[Path, str]
) -> Optional[Entry]:
    """
    Computer whether the given item is a path to an executable or a revision
    of a repository. The method to work out which item it is follows the following:

    - Assume that this is a path, test that it exists and whether the path points
    to an executable.

    - If the path does not point to an executable, attempt to check whether this
    is a revision.

    :param repo: The path to the repository.
    :param path_or_revision: The item to check.
    :return: An entry object if either the item is a file or a revision, else nothing.
    """

    path = Path(path_or_revision)

    if path.is_file() and os.access(path, os.X_OK):
        return Entry(kind="file", data=str(path), name=name)

    if revision_exists(repo, str(path)):
        return Entry(kind="revision", data=str(path), name=name)

    return None


def compile_and_copy(repo: Path, entry: Entry) -> Optional[str]:
    """
    Attempts to extract an executable from the given repository and
    with the given entry configuration. The configuration can either be
    a revision number or a file path.

    * If it is a revision number, the function will set the repository to,
    checkout the revision, compile, and copy the produced executable.

    * If it is a path, the function will simply copy over the file into
    the directory.
    """
    if not TEMP_DIR.exists():
        TEMP_DIR.mkdir()

    extension = ".exe" if platform.system() == "Windows" else ""
    dst = TEMP_DIR / f"{entry.name}{extension}"

    match entry.kind:
        case "file":
            shutil.copyfile(entry.data, dst)
        case "revision":
            # we need to checkout the revision of the repository, compile it, and
            # then copy the file over.
            checkout_git_revision(repo, entry.data)

            handle = Popen(
                ["cargo", "build", "--release"], cwd=repo, stderr=PIPE,
            )
            
            result = handle.wait()
            if result != 0:
                _, stderr = handle.communicate()
                raise RuntimeError(f"Compilation returned a non-zero exit code, output:\n{stderr}")

            exe_name = "hashc.exe" if platform.system() == "Windows" else "hashc"
            exe_path = repo / "target" / "release" / exe_name

            if not exe_path.exists() and os.access(exe_path, os.X_OK):
                raise FileNotFoundError(
                    f"No executable was produced for `{entry.name}`"
                )

            shutil.copyfile(exe_path, dst)

    return dst
