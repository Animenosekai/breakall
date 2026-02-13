"""Module to handle AST nodes"""

from __future__ import annotations

import ast
import typing
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

SourceASTNode = typing.TypeVar("SourceASTNode", bound=ast.AST)
TargetASTNode = typing.TypeVar("TargetASTNode", bound=ast.AST)


def copy_location(
    source: SourceASTNode,
    target: TargetASTNode,
    *,
    overwrite: bool = True,
    recursive: bool = True,
) -> TargetASTNode:
    """
    Copy the location of a node to another if possible.

    Parameters
    ----------
    source : SourceASTNode
        The node to copy from
    target : TargetASTNode
        The node where the location is copied to
    overwrite : bool, optional
        Whether to overwrite if it already has location data, by default True
    recursive : bool, optional
        Whether to copy the location recursively to all children, by default True

    Returns
    -------
    TargetASTNode
        The target node with copied location data
    """
    if source == target:
        return target
    if (
        "lineno" in target._attributes  # noqa: SLF001
        and hasattr(source, "lineno")
        and (not hasattr(target, "lineno") or overwrite)
    ):
        target.lineno = source.lineno  # type: ignore[attr-defined]
    if (
        "end_lineno" in target._attributes  # noqa: SLF001
        and hasattr(source, "end_lineno")
        and (not hasattr(target, "end_lineno") or overwrite)
    ):
        target.end_lineno = source.end_lineno  # type: ignore[attr-defined]
    if (
        "col_offset" in target._attributes  # noqa: SLF001
        and hasattr(source, "col_offset")
        and (not hasattr(target, "col_offset") or overwrite)
    ):
        target.col_offset = source.col_offset  # type: ignore[attr-defined]
    if (
        "end_col_offset" in target._attributes  # noqa: SLF001
        and hasattr(source, "end_col_offset")
        and (not hasattr(target, "end_col_offset") or overwrite)
    ):
        target.end_col_offset = source.end_col_offset  # type: ignore[attr-defined]
    if recursive:
        for node in ast.iter_child_nodes(target):
            copy_location(source, node, overwrite=overwrite, recursive=recursive)
    return target


def same_location(
    func: Callable[
        [typing.Any, SourceASTNode],
        list[TargetASTNode] | TargetASTNode,
    ],
) -> Callable[
    [typing.Any, SourceASTNode],
    list[TargetASTNode] | TargetASTNode,
]:
    """
    Decorate a function to copy the location of the first argument to return values.

    Parameters
    ----------
    func : Callable[[typing.Any, SourceASTNode], list[TargetASTNode] | TargetASTNode]
        The function to decorate

    Returns
    -------
    Callable[[typing.Any, SourceASTNode], list[TargetASTNode] | TargetASTNode]
        The decorated function
    """

    def wrapper(
        self: typing.Any,  # noqa: ANN401
        source: SourceASTNode,
        *args: typing.Any,  # noqa: ANN401
        **kwargs: typing.Any,  # noqa: ANN401
    ) -> list[TargetASTNode] | TargetASTNode:
        """
        Wrap a function to copy location data.

        Parameters
        ----------
        self : typing.Any
            The self parameter
        source : SourceASTNode
            The source AST node
        *args : typing.Any
            Additional arguments
        **kwargs : typing.Any
            Additional keyword arguments

        Returns
        -------
        list[TargetASTNode] | TargetASTNode
            The result with copied location
        """
        result = func(self, source, *args, **kwargs)
        if isinstance(result, list):
            for node in result:
                copy_location(source, node)
        else:
            copy_location(source, result)
        return result

    return wrapper
