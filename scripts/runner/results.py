from dataclasses import dataclass
from typing import Generator, List, Optional, Tuple, Literal

from pydantic import BaseModel

from .cases import TestCaseResult
from .messages import Metrics


def percentage_diff(left: float, right: float) -> float:
    """
    Return the percentage difference between the `left` and the `right`
    values. Assuming that we are always comparing `right` to `left`, as
    in `left` is the "original" value.
    """

    if left == 0:
        return float("inf")

    return ((right - left) / left) * 100


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

    def compare(
        self,
    ) -> Optional[ResultEntryComparison]:
        """
        Construct a comparison between the two test case results.
        """
        original = self.original
        result = self.result

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


type MetricKind = Literal["time", "rss"]
type ResultKind = Literal["left", "right"]


class TestResults(BaseModel):
    """
    The resultant collection of test results that were collected from the test cases.

    This is a simple wrapper around a list of `ResultEntry` objects.
    """

    case_results: List[ResultEntry]

    def __iter__(self) -> Generator[ResultEntry, None, None]:
        for result in self.case_results:
            yield result

    def append(self, item: ResultEntry) -> None:
        self.case_results.append(item)

    @property
    def stages(self) -> List[str]:
        """
        Return the list of stages that are present in the test results.

        TODO: make this cached, since its only going to change if the `self.case_results`
        changes.

        TODO: make this include sub-stages too?
        """
        return (
            self.case_results[0].original.compile_metrics.metrics.keys()
            if self.case_results
            else []
        )

    def get_metric(
        self, result: ResultKind, stage: str, metric: MetricKind
    ) -> List[float]:
        """
        Return a collection of all the associated metrics with a particular stage.
        This will return a list of results for the specified stage.

        If the metric is `time`, `Duration`s are implicitly converted to milliseconds.
        """
        if stage not in self.stages:
            raise ValueError(f"Provided {stage=} is not a valid stage")

        metrics = []

        for item in self.case_results:
            entry = item.original if result == "left" else item.result
            assert entry.compile_metrics

            entry = entry.compile_metrics.metrics[stage]

            match metric:
                case "rss":
                    metrics.append(entry.total.end_rss)
                case "time":
                    metrics.append(entry.total.duration.to_ms())

        return metrics

    def get_metric_domain(self, stage: str, metric: MetricKind) -> Tuple[float, float]:
        """
        Get the domain of the specified metric for the specified stage.
        """

        left_results = self.get_metric("left", stage, metric)
        right_results = self.get_metric("right", stage, metric)

        diffs = [
            percentage_diff(item[0], item[1])
            for item in zip(left_results, right_results)
        ]
        return (min(diffs), max(diffs))

    def get_metric_avg(
        self, result: ResultKind, stage: str, metric: MetricKind
    ) -> float:
        """
        Get the average of the specified metric for the specified stage.
        """
        results = self.get_metric(result, stage, metric)
        return sum(results) / len(results)

    def get_rss_stats(self, stage: str) -> Tuple[float, float, float]:
        """
        Get the percentage average, and the percentage range of the RSS
        metric for the specified stage.
        """

        left_avg = self.get_metric_avg("left", stage, "rss")
        right_avg = self.get_metric_avg("right", stage, "rss")
        right_domain = self.get_metric_domain(stage, "rss")

        return (percentage_diff(left_avg, right_avg), *right_domain)

    def get_duration_stats(self, stage: str) -> Tuple[float, float]:
        """
        Get the percentage average, and the percentage range of the duration
        metric for the specified stage.
        """
        left_avg = self.get_metric_avg("left", stage, "time")
        right_avg = self.get_metric_avg("right", stage, "time")
        right_domain = self.get_metric_domain(stage, "time")

        return (percentage_diff(left_avg, right_avg), *right_domain)
