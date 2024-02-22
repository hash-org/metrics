from pathlib import Path
from enum import Enum


class OutputKind(str, Enum):
    graph = "graph"
    table =  "table"
    json = "json"


TEMP_DIR = Path(__file__).parent.parent / "tmp"
REPO_DIR = Path("/Users/afedotov/projects/hash-org/hashc")
