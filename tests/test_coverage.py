from breakall import enable_breakall, supports_breakall


@enable_breakall
def test_breakall_basic():
    """"""
    count = 0
    for i in range(10):
        for j in range(10):
            count += 1
            breakall
    assert count == 1  # Should break all loops after 1 iteration


@enable_breakall
def test_breakall_n_loops():
    """"""
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
def test_breakall_at_n():
    """"""
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


import pytest
from breakall.exceptions import BreakAllRuntimeError, BreakAllSyntaxError


def test_invalid_negative_loop_count():
    """"""
    with pytest.raises(BreakAllSyntaxError):

        @enable_breakall
        def func():
            """"""
            for i in range(10):
                breakall: "-1"  # Invalid negative break count


def test_invalid_loop_number():
    """"""
    with pytest.raises(BreakAllSyntaxError):

        @enable_breakall
        def func():
            """"""
            for i in range(10):  # Loop 1
                breakall @ 5  # No such loop (only 1 loop)


@enable_breakall
def decorated_function():
    """"""
    count = 0
    for i in range(10):
        for j in range(10):
            count += 1
            breakall
    return count


def test_decorated_function():
    """"""
    assert decorated_function() == 1  # Function should break all loops


def test_function_transformation():
    """"""

    @enable_breakall
    def dummy_function():
        """"""
        for i in range(10):
            for j in range(10):
                breakall

    assert supports_breakall(dummy_function)  # Ensure transformation happened


import sys

import pytest
from breakall.exceptions import BreakAllEnvironmentError


def test_no_source_code():
    """"""
    with pytest.raises(BreakAllEnvironmentError):
        enable_breakall(
            sys.setrecursionlimit
        )  # Can't retrieve the Python source code of a built-in function


@enable_breakall
def test_single_loop():
    """"""
    count = 0
    for i in range(10):
        count += 1
        breakall
    assert count == 1  # Single loop should break on first iteration


@enable_breakall
def test_no_iterations():
    """"""
    count = 0
    for i in range(0):  # No iterations
        for j in range(10):
            count += 1
            breakall
    assert count == 0  # No loops should run



def test_invalid_breakall_syntax():
    """"""
    with pytest.raises(BreakAllSyntaxError):
        @enable_breakall
        def func():
            for i in range(10):
                breakall // 2 # Should raise error

