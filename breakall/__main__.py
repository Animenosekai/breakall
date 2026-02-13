"""The CLI for the `breakall` module."""

from __future__ import annotations

import argparse
import ast
import pathlib
from pathlib import Path
from typing import Any

import breakall

GLOBAL_ENV: dict[str, Any] = {"breakall": breakall, "__name__": "__main__"}


def main(file: pathlib.Path, output: str | None = None) -> None:
    """
    Execute the breakall statement on the given file.

    Parameters
    ----------
    file : pathlib.Path
        The file to execute
    output : str | None, optional
        The output file path (or '-' for stdout), by default None
    """
    # Reading the source code
    source = file.read_text()
    # Parsing it
    tree = ast.parse(source)
    # Adding the enable_breakall decorator to the functions
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            node.decorator_list.append(
                ast.Attribute(
                    value=ast.Name(id="breakall", ctx=ast.Load()),
                    attr="enable_breakall",
                    ctx=ast.Load(),
                ),
            )
    tree = ast.fix_missing_locations(tree)
    # Compiling and executing the code
    code = compile(tree, str(file), "exec")
    exec(code, GLOBAL_ENV, None)  # noqa: S102
    # Writing the modified code
    if output:
        result = ast.unparse(tree)
        if output == "-":
            print(result)  # noqa: T201
        else:
            Path(output).write_text(result)


def entry() -> None:
    """Start the CLI application."""
    parser = argparse.ArgumentParser(
        prog="breakall",
        description="Break from multiple loops at once in Python",
    )
    parser.add_argument("file", help="The file to run", type=pathlib.Path)
    # parser.add_argument(
    #     "--trace",
    #     help=(
    #         "Enable tracing. This WILL slow down execution but will hook "
    #         "and modify every function call."
    #     ),
    #     action="store_true",
    #     default=False,
    # )
    parser.add_argument(
        "--output",
        help="If provided, will write the modified source code to the provided file.",
    )
    args = parser.parse_args()
    main(file=args.file, output=args.output)
