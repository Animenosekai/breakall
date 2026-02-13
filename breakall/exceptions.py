"""The module for the custom exceptions of the `breakall` statement"""
import ast
import sys
import types
import typing


class BreakAllError(Exception):

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
    ):
        """
        Parameters
        ----------
        title: str
        message: str
        filename: str
        line: int
        function: str
        col_offset: int
        spacing: int
        unparsed_node: str
        error_length: int
        indicator: str, default = ^
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
        node: typing.Union[ast.stmt, ast.expr],
        spacing: int,
        error_length: int,
        filename: str = "<unknown filename>",
        function: str = "<anonymous function>",
        indicator: str = "^",
    ) -> "BreakAllError":
        """
        Parameters
        ----------
        title: str
        message: str
        node: expr | stmt
        spacing: int
        error_length: int
        filename: str, default = <unknown filename>
        function: str, default = <anonymous function>
        indicator: str, default = ^

        Returns
        -------
        BreakAllError
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
        Builds the error body to show to the user

        Returns
        -------
        str
        """
        return "\n".join(
            (
                self.title,
                f'File "{self.filename}", line {self.line}, in {self.function}',
                f"{' ' * self.col_offset}{self.unparsed_node}",
                f"{' ' * self.col_offset}{' ' * self.spacing}{self.indicator * self.error_length}",
                self.message,
            )
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
):
    """
    The exception hook for the `BreakAllSyntaxError` exception,
    which is used to avoid having big stack traces for a SyntaxError
    on the user's side.

    Parameters
    ----------
    exctype: type
        The exception type
    value: Any | BaseException
        The exception value
    traceback: traceback
        The traceback
    """
    try:
        if issubclass(exctype, BreakAllError):
            print(f"{exctype.__name__}: {value}")
            return
    except Exception:
        # Raised for example if for some reason `exctype` is not a type
        pass
    sys.__excepthook__(exctype, value, traceback)

