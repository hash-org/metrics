from dataclasses import dataclass
from pathlib import Path
from enum import Enum

TEMP_DIR = Path(__file__).parent.parent / "tmp"
REPO_DIR = Path("/Users/afedotov/projects/hash-org/hashc")


class OutputKind(str, Enum):
    table = "table"
    json = "json"


class OptimisationLevel(str, Enum):
    debug = "debug"
    release = "release"

    def __repr__(self) -> str:
        return self.value

    def __str__(self) -> str:
        return self.value


@dataclass
class Settings:
    optimisation_level: OptimisationLevel
    output_kind: OutputKind
    repository: Path
