"""Runtime helpers for the `breakall` statement"""

from __future__ import annotations

import typing

from breakall.exceptions import BreakAllRuntimeError


def destination_from_break_count(
    count: typing.Any,  # noqa: ANN401
    current_loop: int,
    filename: str,
    line: int,
    function: str,
    col_offset: int,
    spacing: int,
    unparsed_node: str,
    error_length: int,
    indicator: str = "^",
) -> int:
    """
    Find destination loop based on break count.

    Parameters
    ----------
    count : typing.Any
        The break count
    current_loop : int
        The current loop level
    filename : str
        The filename
    line : int
        The line number
    function : str
        The function name
    col_offset : int
        The column offset
    spacing : int
        The spacing
    unparsed_node : str
        The unparsed node
    error_length : int
        The error length
    indicator : str, optional
        The indicator character, by default "^"

    Returns
    -------
    int
        The destination loop number

    Raises
    ------
    BreakAllRuntimeError
        If the break count is invalid
    """
    try:
        parsed = int(count)
    except Exception as exc:
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
        ) from exc
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
            message=(
                f"There {('are' if current_loop > 1 else 'is')} only "
                f"{current_loop} loop{('s' if current_loop > 1 else '')} to break."
            ),
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
    loop: typing.Any,  # noqa: ANN401
    current_loop: int,
    filename: str,
    line: int,
    function: str,
    col_offset: int,
    spacing: int,
    unparsed_node: str,
    error_length: int,
    indicator: str = "^",
) -> int:
    """
    Find destination loop based on loop number.

    Parameters
    ----------
    loop : typing.Any
        The loop number
    current_loop : int
        The current loop level
    filename : str
        The filename
    line : int
        The line number
    function : str
        The function name
    col_offset : int
        The column offset
    spacing : int
        The spacing
    unparsed_node : str
        The unparsed node
    error_length : int
        The error length
    indicator : str, optional
        The indicator character, by default "^"

    Returns
    -------
    int
        The destination loop number

    Raises
    ------
    BreakAllRuntimeError
        If the loop number is invalid
    """
    try:
        parsed = int(loop)
    except Exception as exc:
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
        ) from exc
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
            message=(
                f"There {('are' if current_loop > 1 else 'is')} only "
                f"{current_loop} loop{('s' if current_loop > 1 else '')} to break "
                "up until this point. Note that it is impossible to break to a "
                "loop defined later."
            ),
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
