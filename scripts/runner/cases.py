import os
import json

from pathlib import Path
from subprocess import PIPE, Popen, TimeoutExpired
from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional


from .messages import Metrics, find_message_in_stream
from .logger import LOG
from .options import TEMP_DIR
from .utils import CompilationProvider


class TestCase(BaseModel):
    """
    A test case describing it and information about how to run the case.
    """

    """
    The name of the case, used for display and identification
    purposes.
    """
    name: str

    """
    The path of the case, this must be a hash program.
    """
    file: Path

    description: Optional[str] = Field(
        None,
        description="An optional description of the case, this is used for debugging purposes.",
    )

    tags: List[str] = Field([], description="Any associated tags with the case.")

    additional_args: Optional[str] = Field(
        None,
        description="Additional arguments to pass to the compiler, specifically a `DeepPartial<CompilerSettings>.",
    )

    run: bool = Field(
        False, description="Whether to run the generated executable or not."
    )

    iterations: int = Field(1, description="The number of times to run the case.", ge=1)

    warmup_iterations: int = Field(
        default=2, description="The number of warmup iterations to run the case."
    )

    timeout: int = Field(
        60, description="The maximum number of seconds to run the case for.", ge=1
    )


class TestCaseFile(BaseModel):
    cases: List[TestCase]


def parse_cases_file(file: Path) -> TestCaseFile:
    """
    Load the test cases from the provided file which is JSON.
    """
    with open(file, "r") as f:
        try:
            return TestCaseFile.model_validate_json(f.read())
        except ValidationError as e:
            raise ValueError(
                f"Failed to load the test cases from `{
                    file}`: {e}"
            ) from e


class TestCaseResult(BaseModel):
    """
    An identifier to the original case.
    """

    case: int

    """
    The exit code of the program, this is 0 if the program successfully ran, otherwise it is the
    exit code of the program.
    """
    exit_code: int

    """
    Resultant metrics that were collected from the test case. 

    None if the program did not successfully compile. 
    """
    compile_metrics: Optional[Metrics]

    """
    The total size of the produced in bytes.
    """
    exe_size: Optional[int]


def run_test_case(
    *, repo: Path, compiler: CompilationProvider, case_id: int, case: TestCase
) -> TestCaseResult:
    """
    Handle the running of a single test case. This will do the following:

    - Run the warmup iterations first, the number of iterations are specified
      by the `warmup_iterations` field in the case.

    - Run the actual iterations, the number of iterations are specified by the
      `iterations` field in the case.

    - Check for any outliers in the `total` metrics and warn the user if any are found.

    - Return the average of the results.
    """

    # Run the warmup iterations first.
    LOG.info(
        f"compiling case `{case.file} with {case.warmup_iterations} warmup iterations`"
    )

    for _ in range(case.warmup_iterations):
        _single_run(
            repo=repo, compiler=compiler, case_id=case_id, case=case, silent=True
        )

    # Now run the actual iterations.

    results = []

    for i in range(case.iterations):
        LOG.info(f"running iteration {i} for case `{case.file}`")
        results.append(
            _single_run(repo=repo, compiler=compiler, case_id=case_id, case=case)
        )

    # We want to check for any statistical outliers per `total` entry in each of the
    # metrics stages. If so, we want to warn the user about this.

    LOG.info("successfully compiled and collected metrics")
    return results[0]  # TODO: must be changed to return the average of the results.


def _single_run(
    *,
    repo: Path,
    compiler: CompilationProvider,
    case_id: int,
    case: TestCase,
    silent=False,
) -> TestCaseResult:
    """
    Run the provided test case with the compiler executable.
    """

    # TODO: use the JSON schema from the compiler to actually validate the input args.
    file_name = case.file.stem.split(".")[0]
    output_path = TEMP_DIR / "cases" / compiler.entry.name / file_name
    output_path.mkdir(parents=True, exist_ok=True)

    args = {
        "entry_point": str(case.file),
        "output_directory": str(output_path),
        "messaging_format": "json",
        "timings": True,
        "stage": "build",  # TODO: make this configurable.
        # "optimisation_level": "Debug" # TODO: add a way to specify this per case or per run?
    }

    # Ensure that the compiler itself is executable.
    os.chmod(compiler.path, 0o755)

    # Args must be double encoded
    encoded_args = json.dumps(json.dumps(args))

    try:
        handle = Popen(
            f"{compiler.path} --configure {encoded_args}",
            cwd=repo,
            stderr=PIPE,
            stdout=PIPE,
            shell=True,
        )

        result = handle.wait(timeout=case.timeout)
        stdout, stderr = handle.communicate()
    except TimeoutExpired:
        LOG.warn(f"command `{handle.args}` timed out after {case.timeout} seconds")
        return TestCaseResult(
            case=case_id, exit_code=-1, compile_metrics=None, exe_size=None
        )

    # For the non-zero exit case, we simply return the result and do no further
    # processing.
    if result != 0:
        LOG.error(
            f"command `{handle.args}` exited with non-zero exit code, {result=}\n{stderr.decode()}"
        )

        return TestCaseResult(
            case=case_id, exit_code=result, compile_metrics=None, exe_size=None
        )

    # we want to parse the output of the compilation as a stream of `CompilerMessage`s, where
    # one of them will be a `TimingMetrics` message.
    #
    # TODO: for now, we just ignore all of the other messages and try find the `TimingMetrics` message.
    metrics = find_message_in_stream(stdout.decode(), "metrics")

    if metrics is None:
        LOG.error("failed to find the `TimingMetrics` message in the output")
        return TestCaseResult(
            case=case_id, exit_code=-1, compile_metrics=None, exe_size=None
        )

    # now we want to get the size of the produced executable. We locate the executable
    # and get the size of it.
    exe_name = output_path / args.get("optimisation_level", "debug") / file_name

    if not exe_name.exists() or not exe_name.is_file():
        LOG.error(f"failed to locate the produced executable at `{exe_name}`")

    size = exe_name.stat().st_size

    return TestCaseResult(
        case=case_id, exit_code=result, compile_metrics=metrics, exe_size=size
    )
