"""Module to handle AST nodes"""

import ast
import typing

SourceASTNode = typing.TypeVar("SourceASTNode", bound=ast.AST)
TargetASTNode = typing.TypeVar("TargetASTNode", bound=ast.AST)


def copy_location(
    source: SourceASTNode,
    target: TargetASTNode,
    overwrite: bool = True,
    recursive: bool = True,
) -> TargetASTNode:
    """
    Copies the location of a node to another if possible

    Parameters
    ----------
    source: AST | SourceASTNode
        The node to copy from
    target: AST | TargetASTNode
        The node where the location is copied to
    overwrite: bool, default = True
        Whether to overwrite if it already has location data
    recursive: bool, default = True
        Whether to copy the location recursively to all children

    Returns
    -------
    TargetASTNode
    """
    if source == target:
        return target
    if "lineno" in target._attributes and hasattr(source, "lineno"):
        if not hasattr(target, "lineno") or overwrite:
            target.lineno = source.lineno
    if "end_lineno" in target._attributes and hasattr(source, "end_lineno"):
        if not hasattr(target, "end_lineno") or overwrite:
            target.end_lineno = source.end_lineno
    if "col_offset" in target._attributes and hasattr(source, "col_offset"):
        if not hasattr(target, "col_offset") or overwrite:
            target.col_offset = source.col_offset
    if "end_col_offset" in target._attributes and hasattr(source, "end_col_offset"):
        if not hasattr(target, "end_col_offset") or overwrite:
            target.end_col_offset = source.end_col_offset
    if recursive:
        for node in ast.iter_child_nodes(target):
            copy_location(source, node, overwrite, recursive)
    return target


def same_location(
    func: typing.Callable[
        [typing.Any, SourceASTNode],
        typing.Union[typing.List[TargetASTNode], TargetASTNode],
    ],
) -> typing.Callable[
    [typing.Any, SourceASTNode],
    typing.Union[typing.List[TargetASTNode], TargetASTNode],
]:
    """
    Decorator to copy the location of the first argument to the return value

    Parameters
    ----------
    func: (Any, AST) -> list | (Any, AST) -> list | AST
        The function to decorate

    Returns
    -------
    (Any, AST) -> list | AST
    """

    def wrapper(self, source: typing.Any, *args, **kwargs):
        """
        Parameters
        ----------
        source: Any
        args
        kwargs
        """
        result = func(self, source, *args, **kwargs)
        if isinstance(result, list):
            for node in result:
                copy_location(source, node)
        else:
            copy_location(source, result)
        return result

    return wrapper
