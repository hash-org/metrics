#!/usr/bin/env python

import typer
from pathlib import Path

from utils import compile_and_copy, to_entry
from options import OutputKind, REPO_DIR

app = typer.Typer(add_completion=False)


@app.command()
def compare(
    left: str = typer.Argument(
        ...,
        help="The right comparison object, either a file path or a revision number.",
    ),
    right: str = typer.Argument(
        help="The right comparison object, either a file path or a revision number."
    ),
    repository: str = typer.Option(
        REPO_DIR,
        help="The path to the repository of the compiler."
    ),
    output: OutputKind = typer.Option(
        OutputKind.table, help="The kind of format to use when outputting results"
    ),
):
    # Check whether the repository path exists or not.
    repository = Path(repository)
    if not repository.exists() or not repository.is_dir():
        raise typer.BadParameter("The repository does not exist or is not a directory")
    
    # TODO: make this be able to run with N versions

    # determine whether the left and right is an executable.
    left, right = left.strip(), right.strip()
    left = to_entry(repository, name="left", path_or_revision=left)
    if left is None:
        raise typer.BadParameter(
            "The left comparison object is not a valid path to an executable or "
            "a revision number"
        )

    right = to_entry(repository, name="right", path_or_revision=right)
    if right is None:
        raise typer.BadParameter(
            "The left comparison object is not a valid path to an executable or "
            "a revision number"
        )

    # now we need to either copy over the executable into the "testbed", or checkout
    # the revision, compile it and then copy over the executable.
    left_result = compile_and_copy(repository, left)
    if left_result is None:
        raise typer.BadParameter(
            "Failed to compile and copy the left comparison object"
        )

    right_result = compile_and_copy(repository, right)
    if right_result is None:
        raise typer.BadParameter(
            "Failed to compile and copy the left comparison object"
        )



def main():
    app()


if __name__ == "__main__":
    main()
