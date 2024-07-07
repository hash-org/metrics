#!/usr/bin/env python

from typing import List
import typer
from pathlib import Path
from shutil import rmtree

from runner.logger import LOG
from runner.cases import parse_cases_file, run_test_case
from runner.results import ResultEntry, TestResults
from runner.utils import (
    CompilationProvider,
    OptimisationLevel,
    compile_and_copy,
    to_entry,
)
from runner.options import TEMP_DIR, OutputKind, REPO_DIR, Settings

app = typer.Typer(add_completion=False)


@app.command()
def clear():
    """
    Remove any artifacts that were generated by previous runs.
    """

    if TEMP_DIR.exists():
        LOG.info("clearing entries")
        rmtree(TEMP_DIR)

    TEMP_DIR.mkdir()


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
        REPO_DIR, help="The path to the repository of the compiler."
    ),
    cases: str = typer.Option(
        ...,
        help="The path to the file containing the test cases to run the comparison on.",
    ),
    output: OutputKind = typer.Option(
        OutputKind.table, help="The kind of format to use when outputting results"
    ),
    optimisation_level: OptimisationLevel = typer.Option(
        OptimisationLevel.release,
        help="The optimisation level the compiler should be compiled to",
    ),
):
    """
    Perform a run between two or more versions of the compiler.

    This will collect the following metrics:
     - compilation timings, including per stage and total.
     - memory usage, including per stage and total.
     - instruction count.
     - produced artifact size
     - produced artifact speed

    Metrics are collected on the provided cases, and a indicative comparison of the two runs. The output
    format of the metrics can be configured through the commandline arguments.
    """

    # Check whether the repository path exists or not.
    repo = Path(repository)
    if not repo.exists() or not repo.is_dir():
        raise typer.BadParameter("The repository does not exist or is not a directory")

    settings = Settings(
        repository=repo, optimisation_level=optimisation_level, output_kind=output
    )

    # TODO: make this be able to run with N versions

    # determine whether the left and right is an executable.
    left, right = left.strip(), right.strip()
    left_entry = to_entry(settings, name="left", path_or_revision=left)
    if left_entry is None:
        raise typer.BadParameter(
            "The left comparison object is not a valid path to an executable or "
            "a revision number"
        )

    right_entry = to_entry(settings, name="right", path_or_revision=right)
    if right_entry is None:
        raise typer.BadParameter(
            "The left comparison object is not a valid path to an executable or "
            "a revision number"
        )
    
    # now we have the executables, we want to run them on the provided test cases. We take the path
    # from the `--cases` argument and turn into a list of cases to run.

    cases_path = Path(cases)
    if not cases_path.exists() or not cases_path.is_file():
        raise typer.BadParameter("The cases file does not exist or is not a file")

    compilation_providers: List[CompilationProvider] = []

    for entry in [left_entry, right_entry]:
        # now we need to either copy over the executable into the "testbed", or checkout
        # the revision, compile it and then copy over the executable.
        compilation_result = compile_and_copy(settings, entry)
        if compilation_result is None:
            raise typer.BadParameter(
                f"Failed to compile and copy the `{entry.name}` comparison object"
            )
        else:
            compilation_providers.append(compilation_result)

    test_config = parse_cases_file(cases_path)
    results = []

    for case_id, case in enumerate(test_config.cases):
        # get the left and right results
        left_result = run_test_case(
            repo=repo, compiler=compilation_providers[0], case=case, case_id=case_id
        )
        right_result = run_test_case(
            repo=repo, compiler=compilation_providers[1], case=case, case_id=case_id
        )

        if left_result.exit_code != 0:
            LOG.error(f"failed to run the left comparison object on case `{case.file}`")
            continue

        if right_result.exit_code != 0:
            LOG.error(
                f"failed to run the right comparison object on case `{case.file}`"
            )
            continue

        # construct the results from both runs
        results.append(
            ResultEntry(name=case.name, original=left_result, result=right_result)
        )

    results_obj = TestResults(results=results)

    # now we want to output the results in the desired format.
    match settings.output_kind:
        case OutputKind.table:
            # TODO: Use tabulation and create a view which shows the differences
            #
            # - We want to have a `total` view between all of the test cases and a
            #   a detailed view (invoked by `--detailed-results`) which will display
            #   the difference for every single test case that was present instead of
            #   just showing the total value.
            for result in results_obj:
                print(result)
        case OutputKind.json:
            print(results.model_dump_json())


def main():
    app()


if __name__ == "__main__":
    main()
