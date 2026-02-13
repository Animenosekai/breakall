"""The core implementation of the `breakall` statement in Python"""

from __future__ import annotations

import ast
import inspect
import sys
import typing
import warnings
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

from breakall.exceptions import (
    BreakAllEnvironmentError,
    BreakAllSyntaxError,
    exception_hook,
)
from breakall.nodes import same_location


class SupportsAt(str):
    """
    A type for AST nodes that support the `@` operator.

    This is mainly for type checkers to recognize that a node supports the `@`
    operator when it is used in the context of the `breakall` statement.
    """

    __slots__ = ()

    def __matmul__(self, other: int) -> str:
        """
        Support for the `@` operator with the `breakall` statement.

        Example
        -------
        >>> node = SupportsAt("breakall")
        >>> node @ 2
        'breakall @ 2'

        Parameters
        ----------
        other : int
            The right-hand side of the `@` operator

        Returns
        -------
        str
            The result of the `@` operation
        """
        return f"breakall @ {other}"


# This is here only to make type checkers happy
breakall = SupportsAt("breakall")
"The `breakall` statement. You can import this to make the type checkers happy."
# Type definitions
DefinedFunctionType = typing.TypeVar(
    "DefinedFunctionType",
    ast.FunctionDef,
    ast.AsyncFunctionDef,
)
"The type of the defined function in the AST"
LoopType = ast.For | ast.While | ast.AsyncFor
"The type of the loop in the AST"


class BreakAllTransformer(ast.NodeTransformer):
    """
    Fix the source code by replacing all "breakall" with proper loop breaks.

    This node transformer fixes the source code by replacing all "breakall"
    with a way to break multiple loops at once.

    Note:
    ----
    ... breakall # break all loops
    ... breakall: 2 # break 2 loops
    ... breakall: 1 # same as `break`

    Example:
    -------
    >>> source = '''
    ... for i in range(10):
    ...     for j in range(10):
    ...        breakall
    ... '''
    >>> tree = ast.parse(source)
    >>> BreakAllTransformer().visit(tree)
    # Produces an AST tree which is equivalent to:
    1@breakall = type("breakall", (Exception,), {})
    try:
        for i in range(10):
            for j in range(10):
                raise 1@breakall
    except 1@breakall:
        pass

    Raises:
    ------
    BreakAllSyntaxError.from_node
    BreakAllSyntaxError
    """

    def __init__(
        self,
        filename: str = "<string>",
        start_line: int = 0,
        globals: dict[str, typing.Any] | None = None,  # noqa: A002
    ) -> None:
        """
        Initialize the BreakAllTransformer.

        Parameters
        ----------
        filename : str, optional
            The filename of the source code, by default "<string>"
        start_line : int, optional
            The starting line of the function in the source code, by default 0
        globals : dict[str, typing.Any] | None, optional
            The globals of the function, by default None
        """
        super().__init__()
        self.filename = str(filename)
        "Filename of the source code (mainly for error messages)"
        self.start_line = int(start_line)
        "The starting line of the function in the source code"
        self._loop_counter = 0
        "(internal) The loop counter to keep track of the loops"
        self._usage: set[int] = set()
        "(internal) What loops have been breaked to in the scope"
        self._functions: list[str] = []
        "(internal) The functions in the scope in definition order"
        self._lambdas_names: dict[ast.Lambda, str] = {}
        "(internal) The last lambda assignments in the scope"

        self.aliases: set[str] = {
            name for name, value in (globals or {}).items() if value is enable_breakall
        }
        """(internal) The aliases for the `enable_breakall` decorator in the scope"""

        # The default name also needs to be added to the aliases
        # for locally imported `enable_breakall` to work
        # The only caveat is that locally defined aliases won't work
        self.aliases.add(enable_breakall.__name__)

    @same_location
    def visit_def(self, node: DefinedFunctionType) -> ast.AST:  # pyright: ignore[reportIncompatibleMethodOverride]
        """
        Visit a function definition node.

        Parameters
        ----------
        node : DefinedFunctionType
            The node to visit

        Returns
        -------
        ast.AST
            The modified node
        """
        decorators: list[ast.expr] = []
        for decorator in node.decorator_list:
            if (
                isinstance(decorator, ast.Name)
                # and decorator.id == enable_breakall.__name__
                and decorator.id in self.aliases
            ):
                break
            decorators.append(decorator)
        node.decorator_list = decorators
        self._functions.append(node.name)
        node = self.generic_visit(node)  # pyright: ignore[reportAssignmentType]
        self._functions.pop()
        return node

    visit_FunctionDef = visit_def  # pyright: ignore[reportAssignmentType] # noqa: N815
    visit_AsyncFunctionDef = visit_def  # pyright: ignore[reportAssignmentType] # noqa: N815
    visit_Loop_ReturnType: typing.TypeAlias = (  # noqa: PYI042, N815
        list[ast.Assign | ast.Try] | LoopType | ast.stmt | list[ast.stmt]
    )

    @same_location
    def visit_lambda(self, node: ast.Lambda) -> ast.AST:  # pyright: ignore[reportIncompatibleMethodOverride]
        """
        Visit a lambda node.

        Parameters
        ----------
        node : ast.Lambda
            The node to visit

        Returns
        -------
        ast.AST
            The modified node
        """
        try:
            self._functions.append(f"<lambda@{self._lambdas_names[node]}>")
        except KeyError:
            # This might be an unassigned lambda function
            self._functions.append("<lambda>")
        node = self.generic_visit(node)  # pyright: ignore[reportAssignmentType]
        self._functions.pop()
        return node

    visit_Lambda = visit_lambda  # pyright: ignore[reportAssignmentType] # noqa: N815

    @same_location  # pyright: ignore[reportArgumentType]
    def visit_loop(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        node: LoopType,
    ) -> visit_Loop_ReturnType:
        """
        Visit a loop node.

        Parameters
        ----------
        node : LoopType
            The node to visit

        Returns
        -------
        visit_Loop_ReturnType
            The modified node(s)
        """
        self._loop_counter += 1
        loop_body: ast.stmt | list[ast.stmt] = self.generic_visit(node)  # pyright: ignore[reportAssignmentType]
        result: BreakAllTransformer.visit_Loop_ReturnType
        if self._loop_counter in self._usage:
            assignment = ast.Assign(
                targets=[ast.Name(f"{self._loop_counter}@breakall", ast.Store())],
                value=ast.Call(
                    func=ast.Name("type", ast.Load()),
                    args=[
                        ast.Constant("breakall"),
                        ast.Tuple(
                            elts=[ast.Name("Exception", ast.Load())],
                            ctx=ast.Load(),
                        ),
                        ast.Dict(keys=[], values=[]),
                    ],
                    keywords=[],
                ),
            )
            try_block = ast.Try(
                body=loop_body if isinstance(loop_body, list) else [loop_body],
                handlers=[
                    ast.ExceptHandler(
                        type=ast.Name(f"{self._loop_counter}@breakall", ast.Load()),
                        name=None,
                        body=[ast.Pass()],
                    ),
                ],
                orelse=[],
                finalbody=[],
            )
            result = [assignment, try_block]
            self._usage.remove(self._loop_counter)
        else:
            # Don't apply modifications if not needed
            result = loop_body
        self._loop_counter -= 1
        return result

    visit_For = visit_loop  # pyright: ignore[reportAssignmentType] # noqa: N815
    visit_While = visit_loop  # pyright: ignore[reportAssignmentType] # noqa: N815
    visit_AsyncFor = visit_loop  # pyright: ignore[reportAssignmentType] # noqa: N815

    @same_location
    def visit_assign(self, node: ast.Assign) -> ast.AST:  # pyright: ignore[reportIncompatibleMethodOverride]
        """
        Visit an assignment node.

        Parameters
        ----------
        node : ast.Assign
            The node to visit

        Returns
        -------
        ast.AST
            The modified node
        """
        if (
            len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Lambda)
        ):
            self._lambdas_names[node.value] = node.targets[0].id
        elif isinstance(node.value, ast.Tuple):
            for index, target in enumerate(node.targets):
                if not isinstance(target, ast.Name) or "*" in target.id:
                    # Don't really know what to do with this one so abort
                    # For now, we don't support unpacking for lambda names
                    break
                try:
                    lambda_func = node.value.elts[index]
                    if isinstance(lambda_func, ast.Lambda):
                        self._lambdas_names[lambda_func] = target.id
                except IndexError:
                    # `index` might be out of bound, which shouldn't happen?
                    break
        return self.generic_visit(node)  # pyright: ignore[reportReturnType]

    visit_Assign = visit_assign  # pyright: ignore[reportAssignmentType] # noqa: N815

    @same_location
    def visit_annotated_assign(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        node: ast.AnnAssign,
    ) -> ast.AST | list[ast.AST]:
        """
        Visit an annotated assignment node with `breakall` support.

        Support for the `breakall` statement with a break count.

        Example
        -------
        >>> for i in range(10):
        ...     for j in range(10):
        ...         breakall: 2 # break 2 loops

        Parameters
        ----------
        node : ast.AnnAssign
            The node to check and fix

        Returns
        -------
        ast.AST | list[ast.AST]
            The modified node(s)

        Raises
        ------
        BreakAllSyntaxError
            If the expression contains invalid breakall syntax
        """
        # If the `breakall` statement also has a break count
        if isinstance(node.target, ast.Name) and node.target.id == "breakall":
            # Check if the annotation is a constant or
            # a simple unary operation on a constant
            is_static_value = isinstance(node.annotation, ast.Constant) or (
                isinstance(node.annotation, ast.UnaryOp)
                and isinstance(node.annotation.op, (ast.UAdd, ast.USub))
                and isinstance(node.annotation.operand, ast.Constant)
            )

            if not is_static_value:
                # Any loop up until this point can be broken
                self._usage.update(range(1, self._loop_counter + 1))
                return [
                    ast.ImportFrom(
                        module="breakall.runtime",
                        names=[ast.alias(name="destination_from_break_count")],
                        level=0,
                    ),
                    ast.Raise(
                        exc=ast.Subscript(
                            value=ast.Call(
                                func=ast.Name(id="locals", ctx=ast.Load()),
                                args=[],
                                keywords=[],
                            ),
                            slice=ast.Call(
                                func=ast.Attribute(
                                    value=ast.Constant(value="{dest}@breakall"),
                                    attr="format",
                                    ctx=ast.Load(),
                                ),
                                args=[],
                                keywords=[
                                    ast.keyword(
                                        arg="dest",
                                        value=ast.Call(
                                            func=ast.Name(
                                                id="destination_from_break_count",
                                                ctx=ast.Load(),
                                            ),
                                            args=[],
                                            keywords=[
                                                ast.keyword(
                                                    arg="count",
                                                    value=node.annotation,
                                                ),
                                                ast.keyword(
                                                    arg="current_loop",
                                                    value=ast.Constant(
                                                        value=self._loop_counter,
                                                    ),
                                                ),
                                                ast.keyword(
                                                    arg="filename",
                                                    value=ast.Constant(
                                                        value=self.filename,
                                                    ),
                                                ),
                                                ast.keyword(
                                                    arg="line",
                                                    value=ast.Constant(
                                                        value=node.lineno
                                                        + self.start_line,
                                                    ),
                                                ),
                                                ast.keyword(
                                                    arg="function",
                                                    value=ast.Constant(
                                                        value=".".join(self._functions),
                                                    ),
                                                ),
                                                ast.keyword(
                                                    arg="col_offset",
                                                    value=ast.Constant(
                                                        value=node.col_offset,
                                                    ),
                                                ),
                                                ast.keyword(
                                                    arg="spacing",
                                                    value=ast.Constant(
                                                        value=len(node.target.id) + 2,
                                                    ),
                                                ),
                                                ast.keyword(
                                                    arg="unparsed_node",
                                                    value=ast.Constant(
                                                        value=ast.unparse(node),
                                                    ),
                                                ),
                                                ast.keyword(
                                                    arg="error_length",
                                                    value=ast.Constant(
                                                        value=len(
                                                            ast.unparse(
                                                                node.annotation,
                                                            ),
                                                        ),
                                                    ),
                                                ),
                                            ],
                                        ),
                                    ),
                                ],
                            ),
                            ctx=ast.Load(),
                        ),
                    ),
                ]
            try:
                # Extract the integer value from the annotation
                if isinstance(node.annotation, ast.Constant):
                    parsed_break_count = int(node.annotation.value)  # pyright: ignore[reportArgumentType]
                elif isinstance(node.annotation, ast.UnaryOp):
                    # Handle negative/positive numbers like -1, +2, etc.
                    operand_value = int(node.annotation.operand.value)  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue, reportArgumentType]
                    if isinstance(node.annotation.op, ast.USub):
                        parsed_break_count = -operand_value
                    else:  # UAdd
                        parsed_break_count = operand_value
                else:
                    msg = "Unexpected annotation type"
                    raise TypeError(msg)  # noqa: TRY301
            except Exception as exc:
                annotation_str = ast.unparse(node.annotation)
                raise BreakAllSyntaxError.from_node(
                    title="Invalid break count",
                    message=(f"Cannot parse the break count `{annotation_str}`"),
                    node=node,
                    spacing=len(node.target.id) + 2,
                    error_length=len(annotation_str),
                    filename=self.filename,
                    function=".".join(self._functions),
                ) from exc
            if parsed_break_count == 1:
                # Little optimization
                return ast.Break()
            if parsed_break_count < 1:
                annotation_str = ast.unparse(node.annotation)
                raise BreakAllSyntaxError.from_node(
                    title="Invalid break count",
                    message="The break count must be greater than 0",
                    node=node,
                    spacing=len(node.target.id) + 2,
                    error_length=len(annotation_str),
                    filename=self.filename,
                    function=".".join(self._functions),
                ) from None
            destination = self._loop_counter - parsed_break_count + 1
            if destination < 1:
                plural = "" if self._loop_counter == 1 else "s"
                is_or_are = "is" if self._loop_counter == 1 else "are"
                annotation_str = ast.unparse(node.annotation)
                raise BreakAllSyntaxError.from_node(
                    title="Invalid break count",
                    message=(
                        f"There {is_or_are} only {self._loop_counter} "
                        f"loop{plural} to break."
                    ),
                    node=node,
                    spacing=len(node.target.id) + 2,
                    error_length=len(annotation_str),
                    filename=self.filename,
                    function=".".join(self._functions),
                ) from None
            self._usage.add(destination)
            return ast.Raise(
                exc=ast.Call(
                    func=ast.Name(f"{destination}@breakall", ast.Load()),
                    args=[],
                    keywords=[],
                ),
                cause=None,
            )
        if isinstance(node.value, ast.Lambda) and isinstance(node.target, ast.Name):
            self._lambdas_names[node.value] = node.target.id
        return self.generic_visit(node)

    visit_AnnAssign = visit_annotated_assign  # pyright: ignore[reportAssignmentType] # noqa: N815

    @same_location
    def visit_Expr(  # noqa: N802, pyright: ignore[reportIncompatibleMethodOverride]
        self,
        node: ast.Expr,
    ) -> ast.AST | list[ast.AST]:
        """
        Visit an expression node.

        Parameters
        ----------
        node : ast.Expr
            The expression node to visit

        Returns
        -------
        ast.AST | list[ast.AST]
            The modified AST node or list of nodes

        Raises
        ------
        BreakAllSyntaxError
            If the expression contains invalid breakall syntax
        """
        # If the expression is a `breakall` statement
        if (
            isinstance(node.value, ast.Name) and node.value.id == "breakall"
        ):  # `1@breakall` is always the first loop
            self._usage.add(1)
            return ast.Raise(
                exc=ast.Call(
                    func=ast.Name("1@breakall", ast.Load()),
                    args=[],
                    keywords=[],
                ),
                cause=None,
            )
        if isinstance(node.value, ast.UnaryOp) and (
            isinstance(node.value.operand, ast.Name)
            and node.value.operand.id == "breakall"
        ):
            operator_repr_map: dict[
                type[ast.operator | ast.unaryop],
                str,
            ] = {ast.UAdd: "+", ast.USub: "-", ast.Not: "not", ast.Invert: "~"}
            operator_repr = operator_repr_map.get(  # pyright: ignore[reportArgumentType]
                type(node.value.op),
                ast.unparse(node.value.op),
            )
            raise BreakAllSyntaxError.from_node(
                title="Invalid break operation",
                message=(
                    "The `breakall` statement must be alone, followed by "
                    "`:` and a break count or `@` and a loop number, not "
                    f"preceeded by `{operator_repr}`"
                ),
                node=node,
                spacing=0,
                error_length=len(operator_repr),
                filename=self.filename,
                function=".".join(self._functions),
            ) from None
        if not isinstance(node.value, ast.BinOp):
            return self.generic_visit(node)
        value = node.value
        if isinstance(value.left, ast.Name) and value.left.id == "breakall":
            if not isinstance(value.op, ast.MatMult):
                binop_repr_map: dict[type[ast.operator], str] = {  # pyright: ignore[reportInvalidTypeForm]
                    ast.Add: "+",
                    ast.Sub: "-",
                    ast.Mult: "*",
                    ast.Div: "/",
                    ast.Mod: "%",
                    ast.Pow: "**",
                    ast.LShift: "<<",
                    ast.RShift: ">>",
                    ast.BitOr: "|",
                    ast.BitXor: "^",
                    ast.BitAnd: "&",
                    ast.FloorDiv: "//",
                }
                operator_repr = binop_repr_map.get(  # pyright: ignore[reportArgumentType]
                    type(value.op),
                    ast.unparse(value.op),
                )
                operator_length: int = len(operator_repr)  # pyright: ignore[reportArgumentType]
                # + 1 for the space before the operator
                raise BreakAllSyntaxError.from_node(
                    title="Invalid break operation",
                    message=(
                        "The `breakall` statement must be alone, followed by "
                        "`:` and a break count or `@` and a loop number, not "
                        f"`{operator_repr}`"
                    ),
                    node=node,
                    spacing=len(value.left.id) + 1,
                    error_length=operator_length,
                    filename=self.filename,
                    function=".".join(self._functions),
                ) from None
            # Check if the break loop number is dynamic
            if not isinstance(value.right, ast.Constant):
                # Any loop up until this point can be broken
                self._usage.update(range(1, self._loop_counter + 1))
                return [
                    ast.ImportFrom(
                        module="breakall.runtime",
                        names=[ast.alias(name="destination_from_loop_number")],
                        level=0,
                    ),
                    ast.Raise(
                        exc=ast.Subscript(
                            value=ast.Call(
                                func=ast.Name(id="locals", ctx=ast.Load()),
                                args=[],
                                keywords=[],
                            ),
                            slice=ast.Call(
                                func=ast.Attribute(
                                    value=ast.Constant(value="{dest}@breakall"),
                                    attr="format",
                                    ctx=ast.Load(),
                                ),
                                args=[],
                                keywords=[
                                    ast.keyword(
                                        arg="dest",
                                        value=ast.Call(
                                            func=ast.Name(
                                                id="destination_from_loop_number",
                                                ctx=ast.Load(),
                                            ),
                                            args=[],
                                            keywords=[
                                                ast.keyword(
                                                    arg="loop",
                                                    value=value.right,
                                                ),
                                                ast.keyword(
                                                    arg="current_loop",
                                                    value=ast.Constant(
                                                        value=self._loop_counter,
                                                    ),
                                                ),
                                                ast.keyword(
                                                    arg="filename",
                                                    value=ast.Constant(
                                                        value=self.filename,
                                                    ),
                                                ),
                                                ast.keyword(
                                                    arg="line",
                                                    value=ast.Constant(
                                                        value=node.lineno
                                                        + self.start_line,
                                                    ),
                                                ),
                                                ast.keyword(
                                                    arg="function",
                                                    value=ast.Constant(
                                                        value=".".join(self._functions),
                                                    ),
                                                ),
                                                ast.keyword(
                                                    arg="col_offset",
                                                    value=ast.Constant(
                                                        value=node.col_offset,
                                                    ),
                                                ),
                                                ast.keyword(
                                                    arg="spacing",
                                                    value=ast.Constant(
                                                        value=len(value.left.id) + 3,
                                                    ),
                                                ),
                                                ast.keyword(
                                                    arg="unparsed_node",
                                                    value=ast.Constant(
                                                        value=ast.unparse(value),
                                                    ),
                                                ),
                                                ast.keyword(
                                                    arg="error_length",
                                                    value=ast.Constant(
                                                        value=len(
                                                            ast.unparse(value.right),
                                                        ),
                                                    ),
                                                ),
                                            ],
                                        ),
                                    ),
                                ],
                            ),
                            ctx=ast.Load(),
                        ),
                    ),
                ]
            try:
                parsed_loop_number = int(value.right.value)  # pyright: ignore[reportArgumentType]
            except Exception as exc:
                raise BreakAllSyntaxError.from_node(
                    title="Invalid loop number",
                    message=f"Cannot parse the loop number `{value.right.value}`",
                    node=node,
                    spacing=len(value.left.id) + 3,
                    error_length=len(repr(value.right.value)),
                    filename=self.filename,
                    function=".".join(self._functions),
                ) from exc
            if parsed_loop_number == self._loop_counter:
                # for i in range(n): # Loop 1
                #     for j in range(m): # Loop 2
                #         breakall @ 2
                # `breakall @ 2` breaks the second loop which is equivalent to `break`
                return ast.Break()
            if parsed_loop_number < 1:
                raise BreakAllSyntaxError.from_node(
                    title="Invalid loop number",
                    message="The loop number must be greater than 0",
                    node=node,
                    spacing=len(value.left.id) + 3,
                    error_length=len(repr(value.right.value)),
                    filename=self.filename,
                    function=".".join(self._functions),
                ) from None
            if parsed_loop_number > self._loop_counter:
                is_or_are = "is" if self._loop_counter == 1 else "are"
                plural = "" if self._loop_counter == 1 else "s"
                raise BreakAllSyntaxError.from_node(
                    title="Invalid loop number",
                    message=(
                        f"There {is_or_are} only {self._loop_counter} "
                        f"loop{plural} to break up until this point. "
                        "Note that it is impossible to break to a loop "
                        "defined later."
                    ),
                    node=node,
                    spacing=len(value.left.id) + 3,
                    error_length=len(repr(value.right.value)),
                    filename=self.filename,
                    function=".".join(self._functions),
                ) from None
            self._usage.add(parsed_loop_number)
            return ast.Raise(
                exc=ast.Name(f"{parsed_loop_number}@breakall", ast.Load()),
                cause=None,
            )
        return self.generic_visit(node)


def fix_source(
    source: str,
    filename: str = "<string>",
    start_line: int = 0,
    globals: dict[str, typing.Any] | None = None,  # noqa: A002
) -> ast.Module:
    """
    Fix the source code by replacing all "breakall" with a way to break all loops.

    Note
    ----
    ...         breakall # break all loops
    ...         breakall: 2 # break 2 loops
    ...         breakall: 1 # same as `break`
    ...         breakall @ 1 # break to loop 1

    Example
    -------
    >>> source = '''
    ... for i in range(10):
    ...     for j in range(10):
    ...        breakall
    ... '''
    >>> fix_source(source)
    # Produces an AST tree which is equivalent to:
    1@breakall = type("breakall", (Exception,), {})
    try:
        for i in range(10):
            2@breakall = type("breakall", (Exception,), {})
            try:
                for j in range(10):
                    raise 1@breakall
            except 2@breakall:
                pass
    except 1@breakall:
        pass

    Parameters
    ----------
    source : str
        The source code to fix
    filename : str, optional
        The filename of the source code, by default "<string>"
    start_line : int, optional
        The starting line of the function in the source code, by default 0
    globals : dict[str, typing.Any] | None, optional
        The globals of the function to check for `enable_breakall` aliases

    Returns
    -------
    Module
        The fixed source code
    """
    tree = ast.parse(source)
    # Avoid having big stack traces for a SyntaxError on the user's side
    sys.excepthook = exception_hook
    tree = BreakAllTransformer(
        filename=filename,
        start_line=start_line,
        globals=globals,
    ).visit(tree)
    # Restore the previous behavior for performance reasons
    sys.excepthook = sys.__excepthook__
    ast.fix_missing_locations(tree)
    return tree


Function = typing.TypeVar("Function", bound=typing.Callable[..., typing.Any])


class SupportsBreakall(typing.Protocol, typing.Generic[Function]):
    """
    A type for callables that can be enabled with `enable_breakall`.

    This is mainly for type checkers to recognize that a function supports the
    `breakall` statement after being enabled with `enable_breakall`.
    """

    __call__: Function
    """The call method of the function"""
    __globals__: dict[str, typing.Any]
    """The global scope of the function"""
    __name__: str
    """The name of the function"""

    supports_breakall: bool
    "Whether the function supports the `breakall` statement"


@typing.overload
def enable_breakall() -> None: ...


@typing.overload
def enable_breakall(func: Function) -> SupportsBreakall[Function]: ...


def enable_breakall(  # noqa: PLR0912
    func: Function | None = None,
) -> SupportsBreakall[Function] | None:
    """
    Enable the `breakall` statement on the given function.

    Example
    -------
    >>> @enable_breakall
    ... def test():
    ...     for i in range(10):
    ...         for j in range(10):
    ...             breakall

    Parameters
    ----------
    func : Function | None, optional
        The function to enable the `breakall` statement on, by default None

    Returns
    -------
    SupportsBreakall | None
        The enabled function or None if called as a decorator factory

    Raises
    ------
    BreakAllEnvironmentError
        If the function source code could not be retrieved
    """
    if func is None:
        # Enable the `breakall` function for all functions in the current global scope
        frame = inspect.currentframe()
        if frame is None:
            raise BreakAllEnvironmentError(
                title="No frame found",
                message="The current frame could not be retrieved",
            )
        prev_frame = frame.f_back
        if prev_frame is None:
            raise BreakAllEnvironmentError(
                title="No previous frame found",
                message="The previous frame could not be retrieved",
            )
        try:
            for name, obj in prev_frame.f_globals.items():
                if callable(obj):
                    obj = typing.cast(SupportsBreakall[typing.Any], obj)
                    obj.supports_breakall = False
                    try:
                        prev_frame.f_globals[name] = enable_breakall(obj)
                    except Exception:  # noqa: BLE001
                        warnings.warn(
                            (
                                f"Could not enable the `breakall` statement"
                                f" on the function `{name}`"
                            ),
                            RuntimeWarning,
                            stacklevel=2,
                        )
        finally:
            del frame
        return None

    # Gets the source code of the function
    try:
        source_lines, start_line = inspect.getsourcelines(func)
    except Exception:  # noqa: BLE001
        source_lines, start_line = [], 0
    if not source_lines:
        try:
            raise BreakAllEnvironmentError(  # noqa: TRY301
                title="No source code found",
                message="The function source code could not be retrieved",
                line=start_line,
                filename=inspect.getsourcefile(func) or "<string>",
            ) from None
        except Exception:  # noqa: BLE001
            raise BreakAllEnvironmentError(
                title="No source code found",
                message="The function source code could not be retrieved",
                line=start_line,
                filename="<string>",
            ) from None
    indentation = 0
    for element in source_lines[0]:
        if not element.isspace():
            break
        indentation += 1
    source = ""
    for line in source_lines:
        source += line[indentation:]

    # Fixes the source code
    filename = inspect.getsourcefile(func) or "<string>"

    try:
        func_globals = func.__globals__
    except AttributeError:
        func_globals = None

    tree = fix_source(
        source,
        filename=filename,
        start_line=start_line,
        globals=func_globals,
    )

    # Compile the fixed source code
    compiled = compile(tree, filename, "exec")

    # Executes the compiled source code (module)
    output: dict[str, typing.Any] = {}
    exec(compiled, func_globals, output)  # noqa: S102, pyright: ignore[reportUnknownArgumentType]

    # Gets the function from the module
    for name, obj in output.items():
        if name == func.__name__:
            func = obj
            # Indicates that the function has been modified
            func.supports_breakall = True  # pyright: ignore[reportFunctionMemberAccess, reportOptionalMemberAccess]
            break
    else:
        func.supports_breakall = False  # pyright: ignore[reportFunctionMemberAccess]

    # Returns the function
    return typing.cast(SupportsBreakall[Function], func)


def supports_breakall(func: Callable[..., typing.Any]) -> bool:
    """
    Check if a function supports the `breakall` statement.

    Parameters
    ----------
    func : Callable[..., Any]
        The function to check

    Returns
    -------
    bool
        Whether the function supports the `breakall` statement
    """
    # Maybe also check the AST
    return hasattr(func, "supports_breakall") and func.supports_breakall  # pyright: ignore[reportFunctionMemberAccess]
