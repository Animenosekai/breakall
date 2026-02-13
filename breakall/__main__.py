"""The CLI for the `breakall` module."""

from __future__ import annotations

import argparse
import ast
import contextlib
import importlib.abc
import importlib.machinery
import pathlib
import sys
import typing
from pathlib import Path

import breakall

GLOBAL_ENV: dict[str, typing.Any] = {"breakall": breakall, "__name__": "__main__"}


class BreakallMetaPathFinder(importlib.abc.MetaPathFinder):
    """Meta path finder that hooks into module imports to add breakall support."""

    def __init__(self) -> None:
        """Initialize the finder."""
        super().__init__()
        self.original_find_spec = importlib.machinery.PathFinder.find_spec

    def find_spec(  # pyright: ignore[reportImplicitOverride]
        self,
        fullname: str,
        path: typing.Sequence[str] | None = None,
        target: typing.Any = None,  # noqa: ANN401
    ) -> importlib.machinery.ModuleSpec | None:
        """
        Find module spec and wrap loader if needed.

        Parameters
        ----------
        fullname : str
            Full name of the module
        path : list[str] | None, optional
            Module search path, by default None
        target : typing.Any, optional
            Target object, by default None

        Returns
        -------
        importlib.machinery.ModuleSpec | None
            Module spec with wrapped loader
        """
        # Use the original finder to get the spec
        spec = self.original_find_spec(fullname, path, target)
        if spec is None or spec.loader is None:
            return spec

        # Skip standard library and breakall module itself
        if fullname.startswith(("_", "breakall")):
            return spec

        # Wrap the loader with our breakall loader
        spec.loader = BreakallLoader(spec.loader)
        return spec


class BreakallLoader(importlib.abc.Loader):
    """Loader that transforms modules to add breakall support."""

    def __init__(self, original_loader: importlib.abc.Loader) -> None:
        """
        Initialize with original loader.

        Parameters
        ----------
        original_loader : importlib.abc.Loader
            The original module loader
        """
        super().__init__()
        self.original_loader = original_loader

    def create_module(self, spec: importlib.machinery.ModuleSpec) -> typing.Any:  # pyright: ignore[reportImplicitOverride]  # noqa: ANN401
        """
        Create module using original loader.

        Parameters
        ----------
        spec : importlib.machinery.ModuleSpec
            Module spec

        Returns
        -------
        typing.Any
            The created module
        """
        return self.original_loader.create_module(spec)  # type: ignore[no-any-return]

    def exec_module(self, module: typing.Any) -> None:  # pyright: ignore[reportImplicitOverride]  # noqa: ANN401
        """
        Execute module after transforming with breakall.

        Parameters
        ----------
        module : typing.Any
            The module to execute
        """
        # Get the source code
        source = None
        if hasattr(self.original_loader, "get_source"):
            with contextlib.suppress(AttributeError, TypeError):
                source = self.original_loader.get_source(module.__name__)  # type: ignore[arg-type]

        # If we got source code, transform it
        if source:
            tree = ast.parse(source)
            # Add the enable_breakall decorator to functions
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

            # Compile and execute the transformed code
            code = compile(tree, module.__file__ or "<traced>", "exec")
            module.__dict__["breakall"] = breakall
            exec(code, module.__dict__)  # noqa: S102
        else:
            # Fall back to original execution
            self.original_loader.exec_module(module)  # type: ignore[union-attr]


def main(
    file: pathlib.Path,
    output: str | None = None,
    *,
    trace: bool = False,
) -> None:
    """
    Execute the breakall statement on the given file.

    Parameters
    ----------
    file : pathlib.Path
        The file to execute
    output : str | None, optional
        The output file path (or '-' for stdout), by default None
    trace : bool, optional
        Enable import hooking for all modules, by default False
    """
    # Install import hook if tracing is enabled
    if trace:
        finder = BreakallMetaPathFinder()
        sys.meta_path.insert(0, finder)

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
    parser.add_argument(
        "--trace",
        help=(
            "Enable tracing. This will hook and modify "
            "every imported module to support breakall."
        ),
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--output",
        help="If provided, will write the modified source code to the provided file.",
    )
    args = parser.parse_args()
    main(file=args.file, output=args.output, trace=args.trace)
