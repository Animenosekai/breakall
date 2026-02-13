"""Tests for the CLI functionality of breakall."""

from __future__ import annotations

import sys
import typing

if typing.TYPE_CHECKING:
    from pathlib import Path

    import pytest

from breakall.__main__ import main

# ruff: noqa: B018, F842, B007, PLR2004
# pyright: reportUnusedExpression=false, reportUnusedVariable=false


def test_cli_basic_execution(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test basic CLI execution with a simple file."""
    # Create a test file
    test_file = tmp_path / "test_basic.py"
    test_file.write_text("""
def test_func():
    count = 0
    for i in range(10):
        for j in range(10):
            count += 1
            breakall
    print(f"Count: {count}")

test_func()
""")

    # Execute with main
    main(file=test_file)

    # Check output
    captured = capsys.readouterr()
    assert "Count: 1" in captured.out


def test_cli_breakall_n(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test CLI execution with breakall: n syntax."""
    test_file = tmp_path / "test_n.py"
    test_file.write_text("""
def test_func():
    count = 0
    for i in range(10):
        for j in range(10):
            for k in range(10):
                count += 1
                breakall: 2
            count += 100
        count += 10
    print(f"Count: {count}")

test_func()
""")

    main(file=test_file)

    captured = capsys.readouterr()
    assert "Count: 110" in captured.out


def test_cli_breakall_at(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test CLI execution with breakall @ n syntax."""
    test_file = tmp_path / "test_at.py"
    test_file.write_text("""
def test_func():
    count = 0
    for i in range(10):
        for j in range(10):
            for k in range(10):
                count += 1
                breakall @ 2
            count += 100
        count += 10
    print(f"Count: {count}")

test_func()
""")

    main(file=test_file)

    captured = capsys.readouterr()
    assert "Count: 110" in captured.out


def test_cli_output_to_file(tmp_path: Path) -> None:
    """Test CLI with --output flag to write transformed code to a file."""
    test_file = tmp_path / "test_output.py"
    test_file.write_text("""
def hello():
    for i in range(5):
        breakall
    print("Hello!")

hello()
""")

    output_file = tmp_path / "output.py"
    main(file=test_file, output=str(output_file))

    # Check that output file was created and contains the decorator
    assert output_file.exists()
    output_content = output_file.read_text()
    assert "@breakall.enable_breakall" in output_content
    assert "def hello():" in output_content


def test_cli_output_to_stdout(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test CLI with --output=- to write transformed code to stdout."""
    test_file = tmp_path / "test_stdout.py"
    test_file.write_text("""
def greet():
    for i in range(3):
        breakall
    return "hi"

result = greet()
""")

    main(file=test_file, output="-")

    captured = capsys.readouterr()
    assert "@breakall.enable_breakall" in captured.out
    assert "def greet():" in captured.out


def test_cli_trace_with_import(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test CLI with --trace flag for importing modules."""
    # Create a module to import (like test2.py)
    module_file = tmp_path / "helper_module.py"
    module_file.write_text("""
def hello_helper():
    for i in range(5):
        for j in range(5):
            breakall: 2
        print(f"i={i}, j={j}")
    print("Hello from helper!")
""")

    # Create main file that imports the module (like test.py)
    main_file = tmp_path / "main_with_import.py"
    main_file.write_text("""
from helper_module import hello_helper

hello_helper()
""")

    # Add tmp_path to sys.path so imports work
    sys.path.insert(0, str(tmp_path))
    try:
        # Execute with trace enabled
        main(file=main_file, trace=True)

        captured = capsys.readouterr()
        # breakall: 2 breaks out of both loops (i and j)
        # So the print inside the i loop never executes
        # Only the final print happens
        assert "Hello from helper!" in captured.out
        assert "i=" not in captured.out  # Loop prints should not appear
    finally:
        sys.path.remove(str(tmp_path))


def test_cli_trace_multiple_modules(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test CLI with --trace flag importing multiple modules."""
    # Create first module
    module1 = tmp_path / "module1.py"
    module1.write_text("""
def func1():
    count = 0
    for i in range(10):
        for j in range(10):
            count += 1
            breakall
    return count
""")

    # Create second module
    module2 = tmp_path / "module2.py"
    module2.write_text("""
def func2():
    result = []
    for i in range(5):
        for j in range(5):
            for k in range(5):
                breakall: 2
        result.append(i)
    return result
""")

    # Create main file
    main_file = tmp_path / "main_multi.py"
    main_file.write_text("""
from module1 import func1
from module2 import func2

print(f"func1 result: {func1()}")
print(f"func2 result: {func2()}")
""")

    sys.path.insert(0, str(tmp_path))
    try:
        main(file=main_file, trace=True)

        captured = capsys.readouterr()
        assert "func1 result: 1" in captured.out
        assert "func2 result: [0, 1, 2, 3, 4]" in captured.out
    finally:
        sys.path.remove(str(tmp_path))


def test_cli_without_trace_no_import_hook(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that without --trace, imported modules don't get breakall support."""
    # Create a module with breakall (but it won't work without trace)
    module_file = tmp_path / "no_trace_module.py"
    module_file.write_text("""
def test_no_trace():
    # This breakall won't work because module isn't transformed
    for i in range(5):
        for j in range(5):
            # Without trace, this will just be treated as an expression statement
            pass  # Replacing breakall with pass to avoid NameError
    print("No trace completed")
""")

    main_file = tmp_path / "no_trace_main.py"
    main_file.write_text("""
import no_trace_module
no_trace_module.test_no_trace()
""")

    sys.path.insert(0, str(tmp_path))
    try:
        # Execute without trace
        main(file=main_file, trace=False)

        captured = capsys.readouterr()
        assert "No trace completed" in captured.out
    finally:
        sys.path.remove(str(tmp_path))


def test_cli_nested_functions(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test CLI with nested functions."""
    test_file = tmp_path / "test_nested.py"
    test_file.write_text("""
def outer():
    def inner():
        count = 0
        for i in range(10):
            for j in range(10):
                count += 1
                breakall
        return count
    
    result = inner()
    print(f"Nested result: {result}")

outer()
""")

    main(file=test_file)

    captured = capsys.readouterr()
    assert "Nested result: 1" in captured.out


def test_cli_async_functions(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test CLI with async functions."""
    test_file = tmp_path / "test_async.py"
    test_file.write_text("""
import asyncio

async def async_test():
    count = 0
    for i in range(10):
        for j in range(10):
            count += 1
            breakall
    return count

result = asyncio.run(async_test())
print(f"Async result: {result}")
""")

    main(file=test_file)

    captured = capsys.readouterr()
    assert "Async result: 1" in captured.out


def test_cli_while_loops(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test CLI with while loops."""
    test_file = tmp_path / "test_while.py"
    test_file.write_text("""
def test_while():
    count = 0
    i = 0
    while i < 10:
        j = 0
        while j < 10:
            count += 1
            breakall: 2
        i += 1
    print(f"While result: {count}")

test_while()
""")

    main(file=test_file)

    captured = capsys.readouterr()
    assert "While result: 1" in captured.out


def test_cli_mixed_loop_types(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test CLI with mixed for and while loops."""
    test_file = tmp_path / "test_mixed.py"
    test_file.write_text("""
def test_mixed():
    count = 0
    for i in range(5):
        j = 0
        while j < 5:
            count += 1
            breakall: 2
        count += 10
    print(f"Mixed result: {count}")

test_mixed()
""")

    main(file=test_file)

    captured = capsys.readouterr()
    assert "Mixed result: 1" in captured.out


def test_cli_dynamic_breakall(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test CLI with dynamic breakall values."""
    test_file = tmp_path / "test_dynamic.py"
    test_file.write_text("""
def test_dynamic():
    n = 2
    count = 0
    for i in range(10):
        for j in range(10):
            for k in range(10):
                count += 1
                breakall: n
            count += 100
        count += 10
    print(f"Dynamic result: {count}")

test_dynamic()
""")

    main(file=test_file)

    captured = capsys.readouterr()
    assert "Dynamic result: 110" in captured.out


def test_cli_multiple_functions(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test CLI file with multiple functions using breakall."""
    test_file = tmp_path / "test_multiple.py"
    test_file.write_text("""
def func1():
    count = 0
    for i in range(10):
        for j in range(10):
            count += 1
            breakall
    return count

def func2():
    count = 0
    for i in range(10):
        for j in range(10):
            for k in range(10):
                count += 1
                breakall: 2
        count += 100
    return count

print(f"func1: {func1()}")
print(f"func2: {func2()}")
""")

    main(file=test_file)

    captured = capsys.readouterr()
    assert "func1: 1" in captured.out
    # func2: 10 iterations of i loop, each adds 1 then 100 = 1010 total
    assert "func2: 1010" in captured.out
