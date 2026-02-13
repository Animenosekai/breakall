"""Tests for the coverage of breakall."""

# ruff: noqa: B018, F842, B007, PLR2004
# pyright: reportUnusedExpression=false, reportUnusedVariable=false, reportGeneralTypeIssues=false

import sys

import pytest

from breakall import breakall, enable_breakall, supports_breakall
from breakall.exceptions import BreakAllEnvironmentError, BreakAllSyntaxError


@enable_breakall
def test_breakall_basic() -> None:
    """Test that `breakall` breaks out of all loops."""
    count = 0
    for i in range(10):
        for j in range(10):
            count += 1
            breakall
    assert count == 1  # Should break all loops after 1 iteration


@enable_breakall
def test_breakall_n_loops() -> None:
    """Test that `breakall: n` breaks out of n loops."""
    count = 0
    for i in range(10):  # Outer loop
        for j in range(10):  # Inner loop 1
            for k in range(10):  # Inner loop 2
                count += 1
                breakall: 2  # Break out of 2 loops (k and j)
            count += 100  # Should not be reached
        count += 10  # Should be reached
    assert count == 110  # Only outer loop increments


@enable_breakall
def test_breakall_at_n() -> None:
    """Test that `breakall @ n` breaks out of n loops."""
    count = 0
    for i in range(10):  # Loop 1
        for j in range(10):  # Loop 2
            for k in range(10):  # Loop 3
                for l in range(10):  # Loop 4
                    count += 1
                    breakall @ 2  # Should break out of Loop 2
                count += 1000  # Should not be reached
            count += 100  # Should not be reached
        count += 10  # Should be reached
    assert count == 110  # Only outermost loop increments


def test_invalid_negative_loop_count() -> None:
    """Test that `breakall: n` with a negative n raises an error."""
    with pytest.raises(BreakAllSyntaxError):

        @enable_breakall
        def func() -> None:
            """Test function with invalid negative break count."""
            for i in range(10):
                breakall: -1  # Invalid negative break count


def test_invalid_loop_number() -> None:
    """Test that `breakall @ n` with an invalid n raises an error."""
    with pytest.raises(BreakAllSyntaxError):

        @enable_breakall
        def func() -> None:
            """Test function with invalid loop number."""
            for i in range(10):  # Loop 1
                breakall @ 5  # No such loop (only 1 loop)


@enable_breakall
def decorated_function() -> int:
    """Test that a decorated function with `breakall` works correctly."""
    count = 0
    for i in range(10):
        for j in range(10):
            count += 1
            breakall
    return count


def test_decorated_function() -> None:
    """Test that a decorated function with `breakall` works correctly."""
    assert decorated_function() == 1  # Function should break all loops


def test_function_transformation() -> None:
    """Test that the function is transformed to support `breakall`."""

    @enable_breakall
    def dummy_function() -> None:
        """Test transformation."""
        for i in range(10):
            for j in range(10):
                breakall

    assert supports_breakall(dummy_function)  # Ensure transformation happened


def test_no_source_code() -> None:
    """Test enabling `breakall` on a function without source code."""
    with pytest.raises(BreakAllEnvironmentError):
        enable_breakall(
            sys.setrecursionlimit,
        )  # Can't retrieve the Python source code of a built-in function


@enable_breakall
def test_single_loop() -> None:
    """Test that `breakall` works in a single loop."""
    count = 0
    for i in range(10):
        count += 1
        breakall
    assert count == 1  # Single loop should break on first iteration


@enable_breakall
def test_no_iterations() -> None:
    """Test that `breakall` works when there are no iterations."""
    count = 0
    for i in range(0):  # No iterations
        for j in range(10):
            count += 1
            breakall
    assert count == 0  # No loops should run


def test_invalid_breakall_syntax() -> None:
    """Test that invalid `breakall` syntax raises an error."""
    with pytest.raises(BreakAllSyntaxError):

        @enable_breakall
        def func() -> None:
            for i in range(10):
                breakall // 2  # Should raise error
