import json

from typing import Dict, Literal, Optional, Self
from pydantic import BaseModel, ValidationError

from .logger import LOG


class Duration(BaseModel):
    secs: int
    nanos: int

    def __sub__(self, other: Self) -> Self:
        return Duration(
            secs=self.secs - other.secs,
            nanos=self.nanos - other.nanos,
        )

    def __add__(self, other: Self) -> Self:
        return Duration(
            secs=self.secs + other.secs,
            nanos=self.nanos + other.nanos,
        )

    def to_ms(self) -> float:
        """
        Convert the `Duration` into milliseconds.
        """
        return self.secs * 1e3 + self.nanos * 1e-6

    def from_ms(ms: float) -> Self:
        """
        Create a `Duration` instance from milliseconds.
        """
        return Duration(
            secs=int(ms / 1e3),
            nanos=int((ms % 1e3) * 1e6),
        )


class MetricEntry(BaseModel):
    start_rss: Optional[int]
    end_rss: Optional[int]
    duration: Duration

    def diff(self, other: Self) -> Self:
        return MetricEntry(
            start_rss=self.start_rss - other.start_rss,
            end_rss=self.end_rss - other.end_rss,
            duration=self.duration - other.duration,
        )

    def __add__(self, other: Self) -> Self:
        """
        Add two MetricEntry instances together.
        """

        return MetricEntry(
            start_rss=self.start_rss + other.start_rss,
            end_rss=self.end_rss + other.end_rss,
            duration=self.duration + other.duration,
        )


class StageMetrics(BaseModel):
    metrics: Dict[str, MetricEntry]

    def diff(self, other: Self) -> Self:
        # TODO: account for stages that exist in one but not the other!
        return StageMetrics(
            metrics={
                stage: self.metrics[stage].diff(other.metrics[stage])
                for stage in self.metrics
            }
        )


class StageMetricEntry(BaseModel):
    total: MetricEntry
    children: StageMetrics

    def diff(self, other: Self) -> Self:
        return StageMetricEntry(
            total=self.total.diff(other.total),
            children=self.children.diff(other.children),
        )


# TODO: find a way to generate this from the compiler schema.
class Metrics(BaseModel):
    metrics: Dict[str, StageMetricEntry]

    def add(self, other: Self) -> Self:
        return Metrics(
            metrics={
                stage: self.metrics[stage].diff(other.metrics[stage])
                for stage in self.metrics
            }
        )


type MessageName = Literal["metrics"]


# TODO: figure out how to a type map here, as in we want to take a `message_name` and knowingly get the
# appropriate output type
def find_message_in_stream(stream: str, message_name: MessageName) -> Optional[Metrics]:
    """
    Scan the messages stream and find the message with the appropriate tag name.
    """

    # each line is a single message, so we can just iterate over them.
    for line in stream.rstrip().split("\n"):
        # Load the message as JSON, and extract the `message` item.
        message = json.loads(line).get("message")

        # now we want to see if the line is a `TimingMetrics` message.
        # if it is, we can parse it and return it.
        try:
            if message_name == "metrics":
                return Metrics.model_validate(message)
        except ValidationError as exc:
            LOG.error(f"failed to parse the message: {"\n".join(exc.errors())}")
            continue

    return None
