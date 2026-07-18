"""
Custom configuration for pytest.
"""

import pytest


def pytest_report_teststatus(report: pytest.TestReport) -> tuple[str, str, str] | None:
    """
    Custom report for pytest.
    """

    if report.when == "call":
        return (report.outcome, report.outcome[0].upper(), f"{report.outcome.upper()} ({report.duration:.2f}s)")

    return None
