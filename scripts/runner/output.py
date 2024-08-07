import math
from typing import List, Tuple


from .utils import CompilationProvider
from .results import TestResults, percentage_diff
from .options import OutputSettings

from rich.console import Console
from rich.table import Table


def sizeof_fmt(num: int, suffix="B") -> str:
    """
    Convert the given number of bytes into a human-readable format.
    """

    for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"


def get_trend_icon(value: float) -> str:
    """
    Function to compute the trend icon based on the given value.

    If the value is 0, then we return an up-down arrow. If the value is
    positive, we return an up arrow, otherwise we return a down arrow.
    """

    if value == 0:
        return ":up-down_arrow:"
    elif value > 0:
        return "[red] :up_arrow: [/red]"
    else:
        return "[green] :down_arrow: [/green]"


def get_trend_colour(value: float) -> str:
    """
    Function to compute the colour of the trend based on the given value.

    If the value is 0, then we return an empty string. If the value is
    positive, we return "red", otherwise we return "green".
    """
    if value == 0:
        return ""
    elif value > 0:
        return "red "
    else:
        return "green "


def compute_domain_text(domain: Tuple[float, float]) -> str:
    """
    Function to compute the textual representation of a given domain.
    """

    if math.isclose(domain[0], domain[1]):
        colour = get_trend_colour(domain[0])
        return f"[{colour}bold]{domain[0]:.2f}% [/]"
    else:
        min_colour = get_trend_colour(domain[0])
        max_colour = get_trend_colour(domain[1])
        return f"[{min_colour}bold]{domain[0]:.2f}%[/], [{max_colour}bold]{domain[1]:.2f}%[/]"


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
    compilation_providers: List[CompilationProvider]

    console: Console

    def __init__(
        self,
        settings: OutputSettings,
        results: TestResults,
        compilation_providers: List[CompilationProvider],
    ):
        self.settings = settings
        self.results = results
        self.compilation_providers = compilation_providers
        self.console = Console(
            soft_wrap=True,
        )

    def _construct_compiler_provider_comparison_string(
        self, background: str = "#F47983"
    ) -> str:
        """
        Create a string that represents the comparison between the two
        compiler providers.
        """
        assert len(self.compilation_providers) >= 2
        left_instance = self.compilation_providers[0]
        right_instance = self.compilation_providers[1]

        return f"[bold on {background}]{left_instance}[/] vs [bold on {background}]{right_instance}[/]"

    def print_info(self) -> None:
        """
        Construct the RSS/Duration and Exe size comparison tables, and print them to
        the console.
        """

        compiler_providers = self._construct_compiler_provider_comparison_string()

        rss_time_comparison_table = Table(
            title=f"RSS/Time Comparison of {compiler_providers}",
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
            rss_avg, rss_min, rss_max = self.results.get_rss_stats(stage)
            d_avg, d_min, d_max = self.results.get_duration_stats(stage)

            rss_time_comparison_table.add_row(
                stage,
                compute_avg_text(rss_avg),
                compute_domain_text((rss_min, rss_max)),
                compute_avg_text(d_avg),
                compute_domain_text((d_min, d_max)),
            )

        # We also want to add the total row.

        # Next we want to construct a table that outputs information about
        # the executable size difference. We will show the difference per
        # case and then the "total" difference at the end. The total difference
        # should show the `avg` difference and the `range` difference.
        exe_size_comparison_table = Table(
            title=f"Executable Size Comparison of\n{compiler_providers}",
        )

        exe_size_comparison_table.add_column("Case")
        exe_size_comparison_table.add_column("Difference")
        exe_size_comparison_table.add_column("Value")

        for case in self.results.case_results:
            left_size = case.original.exe_size
            right_size = case.result.exe_size

            # if both are none, we just skip it entirely.
            if not left_size and not right_size:
                continue

            # if one is ok and not the other (perhaps a compilation error), then
            # we write `N/A` for both
            if not left_size or not right_size:
                exe_size_comparison_table.add_row(
                    f"[bold]{case.name}[/bold]",
                    "N/A",
                    "N/A",
                )
                continue

            diff = right_size - left_size
            trend = get_trend_icon(diff)
            diff_percentage = percentage_diff(left_size, right_size)

            exe_size_comparison_table.add_row(
                f"[bold]{case.name}[/bold]",
                f"{trend} {sizeof_fmt(abs(diff))}",
                f"{trend} {abs(diff_percentage):.2f}% ({sizeof_fmt(right_size)})",
            )

        self.console.print(rss_time_comparison_table, new_line_start=True)
        self.console.print(exe_size_comparison_table, new_line_start=True)
