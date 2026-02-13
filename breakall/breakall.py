"""The core implementation of the `breakall` statement in Python"""

import ast
import inspect
import sys
import typing
import warnings

from breakall.exceptions import (
    BreakAllEnvironmentError,
    BreakAllSyntaxError,
    exception_hook,
)
from breakall.nodes import same_location

# This is here only to make type checkers happy
breakall = "breakall"
"The `breakall` statement. You can import this to make the type checkers happy."
# Type definitions
DefinedFunctionType = typing.TypeVar(
    "DefinedFunctionType",
    ast.FunctionDef,
    ast.AsyncFunctionDef,
)
"The type of the defined function in the AST"
LoopType = typing.Union[ast.For, ast.While, ast.AsyncFor]
"The type of the loop in the AST"


class BreakAllTransformer(ast.NodeTransformer):
    """
    A node transformer which fixes the source code by replacing all "breakall" with a way to break multiple loops at once.

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

    def __init__(self, filename: str = "<string>", start_line: int = 0) -> None:
        """
        The constructor of the BreakAllTransformer class

        Parameters
        ----------
        filename: str, default = <string>
            The filename of the source code
        start_line: int, default = 0
            The starting line of the function in the source code
        """
        self.filename = str(filename)
        "Filename of the source code (mainly for error messages)"
        self.start_line = int(start_line)
        "The starting line of the function in the source code"
        self._loop_counter = 0
        "(internal) The loop counter to keep track of the loops"
        self._usage: typing.Set[int] = set()
        "(internal) What loops have been breaked to in the scope"
        self._functions: typing.List[str] = []
        "(internal) The functions in the scope in definition order (mainly for error messages)"
        self._lambdas_names: typing.Dict[ast.Lambda, str] = {}
        "(internal) The last lambda assignments in the scope (mainly for error messages)"

    @same_location
    def visit_Def(self, node: DefinedFunctionType) -> ast.AST:
        """
        Parameters
        ----------
        node: DefinedFunctionType

        Returns
        -------
        AST
        """
        decorators = []
        for decorator in node.decorator_list:
            if (
                isinstance(decorator, ast.Name)
                and decorator.id == enable_breakall.__name__
            ):
                break
            decorators.append(decorator)
        node.decorator_list = decorators
        self._functions.append(node.name)
        node = self.generic_visit(node)
        self._functions.pop()
        return node

    visit_FunctionDef = visit_Def
    visit_AsyncFunctionDef = visit_Def
    visit_Loop_ReturnType = typing.Union[
        typing.List[typing.Union[ast.Assign, ast.Try]],
        LoopType,
        ast.stmt,
        typing.List[ast.stmt],
    ]

    @same_location
    def visit_Lambda(self, node: ast.Lambda) -> ast.AST:
        """
        Parameters
        ----------
        node: Lambda

        Returns
        -------
        AST
        """
        try:
            self._functions.append(f"<lambda@{self._lambdas_names[node]}>")
        except KeyError:
            # This is might be an unassigned lambda function
            self._functions.append("<lambda>")
        node = self.generic_visit(node)
        self._functions.pop()
        return node

    @same_location  # type: ignore
    def visit_Loop(self, node: LoopType) -> visit_Loop_ReturnType:
        """
        Parameters
        ----------
        node: LoopType

        Returns
        -------
        visit_Loop_ReturnType
        list
        """
        self._loop_counter += 1
        loop_body: typing.Union[ast.stmt, typing.List[ast.stmt]] = self.generic_visit(
            node,
        )
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

    visit_For = visit_Loop
    visit_While = visit_Loop
    visit_AsyncFor = visit_Loop

    @same_location
    def visit_Assign(self, node: ast.Assign) -> ast.AST:
        """
        Parameters
        ----------
        node: Assign

        Returns
        -------
        AST
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
        return self.generic_visit(node)

    @same_location
    def visit_AnnAssign(
        self,
        node: ast.AnnAssign,
    ) -> typing.Union[ast.AST | typing.List[ast.AST]]:
        """
        Support for the `breakall` statement with a break count.

        Example
        -------
        >>> for i in range(10):
        ...     for j in range(10):
        ...         breakall: 2 # break 2 loops

        Parameters
        ----------
        node: AnnAssign
            The node to check and fix

        Returns
        -------
        AST

        Raises
        ------
        BreakAllSyntaxError.from_node
        BreakAllSyntaxError
        """
        # If the `breakall` statement also has a break count
        if isinstance(node.target, ast.Name) and node.target.id == "breakall":
            if not isinstance(node.annotation, ast.Constant):
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
                parsed_break_count = int(node.annotation.value)
            except Exception:
                raise BreakAllSyntaxError.from_node(
                    title="Invalid break count",
                    message=f"Cannot parse the break count `{node.annotation.value}`",
                    node=node,
                    spacing=len(node.target.id) + 2,
                    error_length=len(repr(node.annotation.value)),
                    filename=self.filename,
                    function=".".join(self._functions),
                )
            if parsed_break_count == 1:
                # Little optimization
                return ast.Break()
            if parsed_break_count < 1:
                raise BreakAllSyntaxError.from_node(
                    title="Invalid break count",
                    message="The break count must be greater than 0",
                    node=node,
                    spacing=len(node.target.id) + 2,
                    error_length=len(repr(node.annotation.value)),
                    filename=self.filename,
                    function=".".join(self._functions),
                )
            destination = self._loop_counter - parsed_break_count + 1
            if destination < 1:
                raise BreakAllSyntaxError.from_node(
                    title="Invalid break count",
                    message=f"There {('are' if self._loop_counter > 1 else 'is')} only {self._loop_counter} loop{('s' if self._loop_counter > 1 else '')} to break.",
                    node=node,
                    spacing=len(node.target.id) + 2,
                    error_length=len(repr(node.annotation.value)),
                    filename=self.filename,
                    function=".".join(self._functions),
                )
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

    @same_location
    def visit_Expr(
        self,
        node: ast.Expr,
    ) -> typing.Union[ast.AST | typing.List[ast.AST]]:
        """
        Parameters
        ----------
        node: Expr

        Returns
        -------
        AST

        Raises
        ------
        BreakAllSyntaxError.from_node
        BreakAllSyntaxError
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
        if isinstance(node.value, ast.UnaryOp):
            if (
                isinstance(node.value.operand, ast.Name)
                and node.value.operand.id == "breakall"
            ):
                OPERATOR_REPR: typing.Dict[
                    typing.Type[typing.Union[ast.operator, ast.unaryop]],
                    str,
                ] = {ast.UAdd: "+", ast.USub: "-", ast.Not: "not", ast.Invert: "~"}
                operator_repr = OPERATOR_REPR.get(
                    type(node.value.op),
                    ast.unparse(node.value.op),
                )
                raise BreakAllSyntaxError.from_node(
                    title="Invalid break operation",
                    message=f"The `breakall` statement must be alone, followed by `:` and a break count or `@` and a loop number, not preceeded by `{operator_repr}`",
                    node=node,
                    spacing=0,
                    error_length=len(operator_repr),
                    filename=self.filename,
                    function=".".join(self._functions),
                )
        if not isinstance(node.value, ast.BinOp):
            return self.generic_visit(node)
        value = node.value
        if isinstance(value.left, ast.Name) and value.left.id == "breakall":
            if not isinstance(value.op, ast.MatMult):
                OPERATOR_REPR = {
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
                operator_repr = OPERATOR_REPR.get(type(value.op), ast.unparse(value.op))
                operator_length = len(operator_repr)
                # + 1 for the space before the operator
                raise BreakAllSyntaxError.from_node(
                    title="Invalid break operation",
                    message=f"The `breakall` statement must be alone, followed by `:` and a break count or `@` and a loop number, not `{operator_repr}`",
                    node=node,
                    spacing=len(value.left.id) + 1,
                    error_length=operator_length,
                    filename=self.filename,
                    function=".".join(self._functions),
                )
            # + 3 for the space before the operator, the `@` operator and the space after the operator
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
                parsed_loop_number = int(value.right.value)
            except Exception:
                raise BreakAllSyntaxError.from_node(
                    title="Invalid loop number",
                    message=f"Cannot parse the loop number `{value.right.value}`",
                    node=node,
                    spacing=len(value.left.id) + 3,
                    error_length=len(repr(value.right.value)),
                    filename=self.filename,
                    function=".".join(self._functions),
                )
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
                )
            if parsed_loop_number > self._loop_counter:
                raise BreakAllSyntaxError.from_node(
                    title="Invalid loop number",
                    message=f"There {('are' if self._loop_counter > 1 else 'is')} only {self._loop_counter} loop{('s' if self._loop_counter > 1 else '')} to break up until this point. Note that it is impossible to break to a loop defined later.",
                    node=node,
                    spacing=len(value.left.id) + 3,
                    error_length=len(repr(value.right.value)),
                    filename=self.filename,
                    function=".".join(self._functions),
                )
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
) -> ast.Module:
    """
    Fixes the source code by replacing all "breakall" with a way to break all loops.

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
    source: str
        The source code to fix
    filename: str, default = <string>
        The filename of the source code
    start_line: int, default = 0
        The starting line of the function in the source code

    Returns
    -------
    Module
        The fixed source code
    """
    tree = ast.parse(source)
    # Avoid having big stack traces for a SyntaxError on the user's side
    sys.excepthook = exception_hook
    tree = BreakAllTransformer(filename=filename, start_line=start_line).visit(tree)
    # Restore the previous behavior for performance reasons
    sys.excepthook = sys.__excepthook__
    tree = ast.fix_missing_locations(tree)
    return tree


def enable_breakall(func: typing.Optional[typing.Callable] = None):
    """
    Enables the `breakall` statement on the given function

    Example
    -------
    >>> @enable_breakall
    ... def test():
    ...     for i in range(10):
    ...         for j in range(10):
    ...             breakall

    Parameters
    ----------
    func: () -> Any | NoneType, default = None
        The function to enable the `breakall` statement on

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
                    try:
                        prev_frame.f_globals[name] = enable_breakall(obj)
                    except Exception:
                        warnings.warn(
                            f"Could not enable the `breakall` statement on the function `{name}`",
                            RuntimeWarning,
                        )
        finally:
            del frame
        return None
    # Gets the source code of the function
    try:
        source_lines, start_line = inspect.getsourcelines(func)
    except Exception:
        source_lines, start_line = [], 0
    if not source_lines:
        try:
            raise BreakAllEnvironmentError(
                title="No source code found",
                message="The function source code could not be retrieved",
                line=start_line,
                filename=inspect.getsourcefile(func) or "<string>",
            )
        except Exception:
            raise BreakAllEnvironmentError(
                title="No source code found",
                message="The function source code could not be retrieved",
                line=start_line,
                filename="<string>",
            )
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
    tree = fix_source(source, filename=filename, start_line=start_line)
    # Compile the fixed source code
    compiled = compile(tree, filename, "exec")
    # Executes the compiled source code (module)
    output: typing.Dict = {}
    exec(compiled, func.__globals__, output)
    # Gets the function from the module
    for name, obj in output.items():
        if name == func.__name__:
            func = obj
            # Indicates that the function has been modified
            func.supports_breakall = True  # type: ignore
            break
    else:
        func.supports_breakall = False  # type: ignore
    # Returns the function
    return func


def supports_breakall(func: typing.Callable):
    """
    Returns whether the function supports the `breakall` statement

    Parameters
    ----------
    func: () -> Any
        The function to check if it supports the `breakall` statement

    Returns
    -------
    bool
        Whether the function supports the `breakall` statement
    """
    # Maybe also check the AST
    return hasattr(func, "supports_breakall") and func.supports_breakall
