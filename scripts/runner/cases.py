import os
import json

from pathlib import Path
from subprocess import PIPE, Popen
from pydantic import BaseModel, ValidationError
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

    """
    An optional description of the case, this is used for debugging purposes.
    """
    description: Optional[str] = None

    """
    Any associated tags with the case, this is used for filtering and search. 
    """
    tags: List[str] = []

    """ 
    This is stored in the JSON format that the compiler accepts, specifically a `DeepPartial<CompilerSettings>`
    """
    additional_args: Optional[str] = None

    """
    Whether to also run the generated executable or not, looking at the used memory, time, and other
    metrics. 
    """
    run: bool = False


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

    handle = Popen(
        f"{compiler.path} --configure {encoded_args}",
        cwd=repo,
        stderr=PIPE,
        stdout=PIPE,
        shell=True,
    )
    LOG.info(f"compiling case `{case.file}`")

    result = handle.wait()
    stdout, stderr = handle.communicate()

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

    LOG.info("successfully compiled and collected metrics")
    return TestCaseResult(
        case=case_id, exit_code=result, compile_metrics=metrics, exe_size=size
    )
