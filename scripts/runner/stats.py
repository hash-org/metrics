from typing import List
import numpy as np

OUTLIER_THRESHOLD = 1.4826 * 10.0
EPSILON = np.finfo(float).eps


def modified_zscores(data: List[float]) -> List[float]:
    """
    Compute the modified z-scores for the given data.

    Compute modified Z-scores for a given sample. A (unmodified) Z-score is defined by
    `(x_i - x_mean)/x_stddev` whereas the modified Z-score is defined by `(x_i - x_median)/MAD`
    where MAD is the median absolute deviation.

    References:
    - <https://en.wikipedia.org/wiki/Median_absolute_deviation>
    """
    assert len(data) > 0

    median = np.median(data)
    median_absolute_deviation = np.median([np.abs(x - median) for x in data])
    median_absolute_deviation = (
        median_absolute_deviation if median_absolute_deviation != 0 else EPSILON
    )

    modified_z_scores = [
        0.6745 * (x - median) / median_absolute_deviation for x in data
    ]
    return modified_z_scores


def check_outliers(
    values: List[float],
) -> bool:
    """
    Check whether any of the values are outliers.
    """

    modified_z_scores = modified_zscores(values)
    return any(np.abs(modified_z_scores) > OUTLIER_THRESHOLD)
