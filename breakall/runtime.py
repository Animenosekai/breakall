"""Runtime helpers for the `breakall` statement"""

import typing

from breakall.exceptions import BreakAllRuntimeError


def destination_from_break_count(
    count: typing.Any,
    current_loop: int,
    filename: str,
    line: int,
    function: str,
    col_offset: int,
    spacing: int,
    unparsed_node: str,
    error_length: int,
    indicator: str = "^",
):
    """
    Parameters
    ----------
    count: Any
    current_loop: int
    filename: str
    line: int
    function: str
    col_offset: int
    spacing: int
    unparsed_node: str
    error_length: int
    indicator: str, default = ^

    Raises
    ------
    BreakAllRuntimeError
    ValueError
    """
    try:
        parsed = int(count)
    except Exception:
        raise BreakAllRuntimeError(
            title="Invalid break count",
            message=f"Cannot parse the break count `{count}`",
            filename=filename,
            line=line,
            function=function,
            col_offset=col_offset,
            spacing=spacing,
            unparsed_node=unparsed_node,
            error_length=error_length,
            indicator=indicator,
        )
    if parsed < 1:
        raise BreakAllRuntimeError(
            title="Invalid break count",
            message="The break count must be greater than 0",
            filename=filename,
            line=line,
            function=function,
            col_offset=col_offset,
            spacing=spacing,
            unparsed_node=unparsed_node,
            error_length=error_length,
            indicator=indicator,
        )
    destination = current_loop - parsed + 1
    if destination < 1:
        raise BreakAllRuntimeError(
            title="Invalid break count",
            message=f"There {('are' if current_loop > 1 else 'is')} only {current_loop} loop{('s' if current_loop > 1 else '')} to break.",
            filename=filename,
            line=line,
            function=function,
            col_offset=col_offset,
            spacing=spacing,
            unparsed_node=unparsed_node,
            error_length=error_length,
            indicator=indicator,
        )
    return destination


def destination_from_loop_number(
    loop: typing.Any,
    current_loop: int,
    filename: str,
    line: int,
    function: str,
    col_offset: int,
    spacing: int,
    unparsed_node: str,
    error_length: int,
    indicator: str = "^",
):
    """
    Parameters
    ----------
    loop: Any
    current_loop: int
    filename: str
    line: int
    function: str
    col_offset: int
    spacing: int
    unparsed_node: str
    error_length: int
    indicator: str, default = ^

    Raises
    ------
    BreakAllRuntimeError
    ValueError
    """
    try:
        parsed = int(loop)
    except Exception:
        raise BreakAllRuntimeError(
            title="Invalid loop number",
            message=f"Cannot parse the loop number `{loop}`",
            filename=filename,
            line=line,
            function=function,
            col_offset=col_offset,
            spacing=spacing,
            unparsed_node=unparsed_node,
            error_length=error_length,
            indicator=indicator,
        )
    if parsed < 1:
        raise BreakAllRuntimeError(
            title="Invalid loop number",
            message="The loop number must be greater than 0",
            filename=filename,
            line=line,
            function=function,
            col_offset=col_offset,
            spacing=spacing,
            unparsed_node=unparsed_node,
            error_length=error_length,
            indicator=indicator,
        )
    if parsed > current_loop:
        raise BreakAllRuntimeError(
            title="Invalid loop number",
            message=f"There {('are' if current_loop > 1 else 'is')} only {current_loop} loop{('s' if current_loop > 1 else '')} to break up until this point. Note that it is impossible to break to a loop defined later.",
            filename=filename,
            line=line,
            function=function,
            col_offset=col_offset,
            spacing=spacing,
            unparsed_node=unparsed_node,
            error_length=error_length,
            indicator=indicator,
        )
    return parsed

