"""
Comprehensive tests for the breakall statement.

This module tests:

- The basic `breakall` statement
- The basic `breakall: n` statement
- The basic `breakall @ n` statement
- That there is no way of using `breakall` incorrectly
- That `breakall: 1` is converted to `break`
- That `breakall @ n` where we are in the n-th loop is converted to `break`
- Normal functions, async functions, lambdas
- Nested functions
- `for` loops, `while` loops, `async for` loops
- Exceptions
- The CLI
- enable_breakall decorator aliases
"""

# ruff: noqa: B018, F842, B007, PLR2004
# pyright: reportUnusedExpression=false, reportUnusedVariable=false, reportGeneralTypeIssues=false, reportInvalidTypeForm=false

import asyncio
from collections.abc import AsyncGenerator

import pytest

from breakall import breakall, enable_breakall
from breakall import enable_breakall as eb
from breakall.exceptions import BreakAllRuntimeError


# Test the basic `breakall` statement
def test_basic_breakall() -> None:
    """Test that the basic `breakall` statement breaks out of all loops."""

    @enable_breakall
    def func() -> list[int]:
        result: list[int] = []
        for i in range(10):
            for j in range(10):
                breakall
            result.append(i)
        return result

    assert func() == []


# Test the basic `breakall: n` statement
def test_basic_breakall_n() -> None:
    """Test that the basic `breakall: n` statement breaks out of n loops."""

    @enable_breakall
    def func() -> list[int]:
        result: list[int] = []
        for i in range(10):
            for j in range(10):
                for k in range(10):
                    breakall: 2
                result.append(i)
        return result

    assert func() == []


# Test the basic `breakall @ n` statement
def test_basic_breakall_at_n() -> None:
    """Test that the basic `breakall @ n` statement breaks out of n loops."""

    @enable_breakall
    def func() -> list[int]:
        result: list[int] = []
        for i in range(10):
            for j in range(10):
                for k in range(10):
                    breakall @ 2
                result.append(i)
        return result

    assert func() == []


# Test that there is no way of using `breakall` incorrectly
def test_invalid_breakall_syntax() -> None:
    """Test that using `breakall` with invalid syntax raises a SyntaxError."""

    def func() -> int:
        for i in range(10):
            breakall + 1  # pyright: ignore[reportOperatorIssue] # Invalid usage
        return 0

    with pytest.raises(SyntaxError):
        enable_breakall(func)


# Test that `breakall: 1` is converted to `break`
def test_breakall_one_is_break() -> None:
    """Test that `breakall: 1` is converted to `break`."""

    @enable_breakall
    def func() -> list[int]:
        result: list[int] = []
        for i in range(10):
            for j in range(10):
                breakall: 1
            result.append(i)
        return result

    assert func() == list(range(10))


# Test that `breakall @ n` where we are in the n-th loop is converted to `break`
def test_breakall_at_n_is_break() -> None:
    """Test `breakall @ n` conversion when we are in the n-th loop."""

    @enable_breakall
    def func() -> list[int]:
        result: list[int] = []
        for i in range(10):
            for j in range(10):
                breakall @ 1
            result.append(i)
        return result

    assert func() == []


async def async_range(count: int) -> AsyncGenerator[int, None]:
    """Async generator that yields numbers from 0 to count - 1."""
    for i in range(count):
        yield (i)
        await asyncio.sleep(0.0)


# Test with normal functions, async functions, lambdas
@pytest.mark.asyncio
async def test_async_breakall() -> None:
    """Test that `breakall` works in async functions."""

    @enable_breakall
    async def func() -> list[int]:
        result: list[int] = []
        for i in range(10):
            for j in range(10):
                async for k in async_range(10):
                    breakall: 2
                result.append(i)
        return result

    assert await func() == []


# Test with nested functions
def test_nested_functions_breakall() -> None:
    """Test that `breakall` works in nested functions."""

    @enable_breakall
    def outer() -> str:
        def inner() -> None:
            for i in range(5):
                for j in range(5):
                    breakall: 2

        inner()
        return "ok"

    assert outer() == "ok"


# Test with `for` loops, `while` loops, `async for` loops
def test_for_loop_breakall() -> None:
    """Test that `breakall` works in `for` loops."""

    @enable_breakall
    def func() -> list[int]:
        result: list[int] = []
        for i in range(10):
            for j in range(10):
                breakall @ 2
            result.append(i)
        return result

    assert func() == list(range(10))


def test_while_loop_breakall() -> None:
    """Test that `breakall` works in `while` loops."""

    @enable_breakall
    def func() -> list[int]:
        result: list[int] = []
        i = 0
        while i < 10:
            j = 0
            while j < 10:
                breakall: 2
            result.append(i)
            i += 1
        return result

    assert func() == []


@pytest.mark.asyncio
async def test_async_for_loop_breakall() -> None:
    """Test that `breakall` works in `async for` loops."""

    @enable_breakall
    async def func() -> list[int]:
        result: list[int] = []
        for i in range(10):
            async for j in async_range(10):
                breakall: 2
            result.append(i)
        return result

    assert await func() == []


# Test exceptions
def test_breakall_exception() -> None:
    """Test that using `breakall` with invalid syntax raises an Exception."""

    @enable_breakall
    def func() -> None:
        for i in range(5):
            for j in range(5):
                if i == 2:
                    msg = "Test Exception"
                    raise NotImplementedError(msg)
                breakall: j

    with pytest.raises(BreakAllRuntimeError):
        func()


# Test `breakall: var` and `breakall: func()`
def test_breakall_dynamic() -> None:
    """Test that `breakall: var` and `breakall: func()` work correctly."""

    @enable_breakall
    def func() -> list[int]:
        result: list[int] = []
        n = 2

        def get_n() -> int:
            return n

        for i in range(10):
            for j in range(10):
                breakall: get_n()  # Should break 2 loops dynamically
            result.append(i)
        return result

    assert func() == []


# Test `breakall @ var` and `breakall @ func()`
def test_breakall_at_dynamic() -> None:
    """Test that `breakall @ var` and `breakall @ func()` work correctly."""

    @enable_breakall
    def func() -> list[int]:
        result: list[int] = []
        loop_num = 2

        def get_loop_num() -> int:
            return loop_num

        for i in range(10):
            for j in range(10):
                for k in range(10):
                    breakall @ get_loop_num()  # Should break to loop 2 dynamically
                result.append(i)
        return result

    assert func() == []


# Test decorator aliases
# Note: You can't import the enable_breakall decorator locally (inside a test function)
def test_decorator_alias_short() -> None:
    """Test that `breakall` works with a short alias decorator name."""

    @eb
    def func() -> list[int]:
        result: list[int] = []
        for i in range(10):
            for j in range(10):
                breakall
            result.append(i)
        return result

    assert func() == []
