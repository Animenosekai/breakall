"""Tests for the basic functionality of breakall."""

from breakall import breakall, enable_breakall

# ruff: noqa: B018, F842
# pyright: reportUnusedExpression=false, reportUnusedVariable=false


@enable_breakall
def test_breakall_all_loops() -> None:
    """Test that breakall breaks out of all loops."""
    count = 0
    for i in range(10):
        for j in range(10):
            count += 1
            breakall
    assert count == 1  # Only one iteration should occur


@enable_breakall
def test_breakall_n_loops() -> None:
    """Test that breakall breaks out of n loops."""
    count = 0
    for i in range(10):  # Outer loop
        for j in range(10):  # Inner loop 1
            for k in range(10):  # Inner loop 2
                count += 1
                breakall: 2
            count += 100  # Should not be incremented
        count += 10  # Should be incremented
    assert count == 110  # Only 1 iteration of each outer loop


@enable_breakall
def test_breakall_at_n() -> None:
    """Test that breakall breaks out of n loops with @ syntax."""
    count = 0
    for i in range(10):  # Loop 1
        for j in range(10):  # Loop 2
            for k in range(10):  # Loop 3
                for l in range(10):  # Loop 4
                    count += 1
                    breakall @ 2  # Should break out of Loop 2
                count += 1000  # Should not be incremented
            count += 100  # Should not be incremented
        count += 10  # Should be incremented
    assert count == 110


def test_no_breakall() -> None:
    """Test that code without breakall works as normal."""
    count = 0
    for i in range(3):
        for j in range(3):
            count += 1
    assert count == 9  # All iterations should complete
