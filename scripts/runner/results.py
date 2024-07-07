from dataclasses import dataclass
from typing import Generator, List, Optional

from pydantic import BaseModel, Field

from .cases import TestCaseResult
from .messages import Metrics


@dataclass
class ResultEntryComparison:
    """
    The difference in timings between the two runs. The `Metrics` structure is re-used to
    represent the difference in timings and memory usage.
    """

    compile_metrics: Metrics

    """
    The difference in executable size that was produced.
    """
    exe_size: Optional[int]


class ResultEntry(BaseModel):
    """
    A class that holds collected metrics about a test case being run under
    `original` and `result` test case configurations.

    The actual results of the test case are stored in the `comparison` field.
    """

    name: str
    original: TestCaseResult
    result: TestCaseResult
    comparison: Optional[ResultEntryComparison] = Field(default=None)

    def model_post_init(self, __context):
        """
        Construct the `comparison` after the initial structure has been initialised.
        """
        self.comparison = ResultEntry.construct_comparison(self.original, self.result)

    @staticmethod
    def construct_comparison(
        original: TestCaseResult, result: TestCaseResult
    ) -> Optional[ResultEntryComparison]:
        """
        Construct a comparison between the two test case results.
        """
        if original.compile_metrics is None or result.compile_metrics is None:
            return None

        compile_metrics = Metrics(
            message="metrics",
            metrics={
                stage: original.compile_metrics.metrics[stage].diff(
                    result.compile_metrics.metrics[stage]
                )
                for stage in original.compile_metrics.metrics
            },
        )

        # just ignore the `exe_size` if we weren't able to collect it for
        # some reason from either of the test cases.
        if result.exe_size is None or original.exe_size is None:
            exe_size = None
        else:
            exe_size = result.exe_size - original.exe_size

        return ResultEntryComparison(compile_metrics, exe_size)


class TestResults(BaseModel):
    """
    The resultant collection of test results that were collected from the test cases.

    This is a simple wrapper around a list of `ResultEntry` objects.
    """

    results: List[ResultEntry]

    def __iter__(self) -> Generator[ResultEntry, None, None]:
        for result in self.results:
            yield result

    def append(self, item: ResultEntry) -> None:
        self.results.append(item)
