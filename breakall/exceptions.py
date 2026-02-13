"""The module for the custom exceptions of the `breakall` statement"""

from __future__ import annotations

import ast
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import types


class BreakAllError(Exception):
    """A custom error for the `breakall` statement."""

    def __init__(
        self,
        title: str,
        message: str,
        filename: str = "<unknown filename>",
        line: int = 0,
        function: str = "",
        col_offset: int = 0,
        spacing: int = 0,
        unparsed_node: str = "",
        error_length: int = 0,
        indicator: str = "^",
    ) -> None:
        """
        Initialize a BreakAllError.

        Parameters
        ----------
        title : str
            The error title
        message : str
            The error message
        filename : str, optional
            The filename, by default "<unknown filename>"
        line : int, optional
            The line number, by default 0
        function : str, optional
            The function name, by default ""
        col_offset : int, optional
            The column offset, by default 0
        spacing : int, optional
            The spacing, by default 0
        unparsed_node : str, optional
            The unparsed node, by default ""
        error_length : int, optional
            The error length, by default 0
        indicator : str, optional
            The indicator character, by default "^"
        """
        self.title = str(title)
        self.message = str(message)
        self.filename = str(filename)
        self.line = int(line)
        self.function = str(function)
        self.col_offset = int(col_offset)
        self.spacing = int(spacing)
        self.unparsed_node = str(unparsed_node)
        self.error_length = int(error_length)
        self.indicator = str(indicator)
        super().__init__(self.build_error_body())

    @classmethod
    def from_node(
        cls,
        title: str,
        message: str,
        node: ast.stmt | ast.expr,
        spacing: int,
        error_length: int,
        filename: str = "<unknown filename>",
        function: str = "<anonymous function>",
        indicator: str = "^",
    ) -> BreakAllError:
        """
        Create a BreakAllError from an AST node.

        Parameters
        ----------
        title : str
            The error title
        message : str
            The error message
        node : ast.stmt | ast.expr
            The AST node
        spacing : int
            The spacing
        error_length : int
            The error length
        filename : str, optional
            The filename, by default "<unknown filename>"
        function : str, optional
            The function name, by default "<anonymous function>"
        indicator : str, optional
            The indicator character, by default "^"

        Returns
        -------
        BreakAllError
            The created error
        """
        return cls(
            title,
            message,
            filename=filename,
            line=getattr(node, "lineno", 0),
            function=function,
            col_offset=getattr(node, "col_offset", 0),
            spacing=spacing,
            unparsed_node=ast.unparse(node),
            error_length=error_length,
            indicator=indicator,
        )

    def build_error_body(self) -> str:
        """
        Build the error body to show to the user.

        Returns
        -------
        str
            The error body
        """
        return "\n".join(
            (
                self.title,
                f'File "{self.filename}", line {self.line}, in {self.function}',
                f"{' ' * self.col_offset}{self.unparsed_node}",
                (
                    f"{' ' * self.col_offset}{' ' * self.spacing}"
                    f"{self.indicator * self.error_length}"
                ),
                self.message,
            ),
        )

    __repr__ = build_error_body


class BreakAllEnvironmentError(BreakAllError):
    """A custom environment error for the `breakall` statement"""


class BreakAllSyntaxError(BreakAllError, SyntaxError):
    """A custom syntax error for the `breakall` statement"""


class BreakAllRuntimeError(BreakAllError, RuntimeError):
    """A custom runtime error for the `breakall` statement"""


def exception_hook(
    exctype: type[BaseException],
    value: BaseException,
    traceback: types.TracebackType | None,
    /,
) -> None:
    """
    Handle exceptions for the `breakall` module.

    This exception hook is used to avoid having big stack traces for
    BreakAllError exceptions on the user's side.

    Parameters
    ----------
    exctype : type[BaseException]
        The exception type
    value : BaseException
        The exception value
    traceback : types.TracebackType | None
        The traceback
    """
    try:
        if issubclass(exctype, BreakAllError):
            print(f"{exctype.__name__}: {value}")  # noqa: T201
            return
    except Exception:  # noqa: BLE001, S110
        # Raised for example if for some reason `exctype` is not a type
        pass
    sys.__excepthook__(exctype, value, traceback)
