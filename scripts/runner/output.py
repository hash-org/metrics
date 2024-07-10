import math
from typing import Tuple

from .results import TestResults
from .options import OutputSettings

from rich.console import Console
from rich.table import Table


def get_trend_icon(value: float) -> str:
    if value == 0:
        return ":up-down_arrow:"
    elif value > 0:
        return "[red] :up_arrow: [/red]"
    else:
        return "[green] :down_arrow: [/green]"


def compute_domain_text(domain: Tuple[float, float]) -> str:
    if math.isclose(domain[0], domain[1]):
        trend = get_trend_icon(domain[0])
        return f"[bold]{trend} {abs(domain[0]):.2f}% [/bold]"
    else:
        return (
            f"[bold]{abs(domain[0]):.2f}%[/bold] - [bold]{abs(domain[1]):.2f}%[/bold]"
        )


def compute_avg_text(avg: float) -> str:
    trend = get_trend_icon(avg)
    return f"[bold]{trend} {abs(avg):.2f}%[/bold]"


class TabulatedOutput:
    """
    Simple class to house all of the logic to format and display
    details of the test results in a tabulated format.
    """

    settings: OutputSettings
    results: TestResults

    console: Console

    def __init__(self, settings: OutputSettings, results: TestResults):
        self.settings = settings
        self.results = results
        self.console = Console(
            soft_wrap=True,
        )

    def print_info(self) -> None:
        rss_time_comparison_table = Table(
            title="RSS/Time Comparison",
        )

        # We want to show the difference in the RSS/time per stage
        # for the `average`, `range`.
        rss_time_comparison_table.add_column("Stage")
        rss_time_comparison_table.add_column("RSS (average)")
        rss_time_comparison_table.add_column("RSS (range)")
        rss_time_comparison_table.add_column("Duration (average)")
        rss_time_comparison_table.add_column("Duration (range)")

        # We're comparing from the left (as the original) and the
        # right as the result.

        for stage in self.results.stages:
            rss_avg = self.results.get_rss_avg(stage)
            rss_domain = self.results.get_rss_domain(stage)
            duration_avg = self.results.get_duration_avg(stage)
            duration_domain = self.results.get_duration_domain(stage)

            rss_time_comparison_table.add_row(
                stage,
                compute_avg_text(rss_avg),
                compute_domain_text(rss_domain),
                compute_avg_text(duration_avg),
                compute_domain_text(duration_domain),
            )

        # We also want to add the total row.

        # Next we want to construct a table that outputs information about
        # the executable size difference. We will show the difference per
        # case and then the "total" difference at the end. The total difference
        # should show the `avg` difference and the `range` difference.

        # exe_size_comparison_table = Table()

        self.console.print(rss_time_comparison_table, new_line_start=True)
        # self.console.print(exe_size_comparison_table)
