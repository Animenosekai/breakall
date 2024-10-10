"""The core implementation of the `breakall` statement in Python"""

import ast
import collections
import inspect
import typing

# This is here only to make type checkers happy
breakall = "breakall"
# Type definitions
DefinedFunctionType = typing.TypeVar(
    "DefinedFunctionType", ast.FunctionDef, ast.AsyncFunctionDef
)
LoopType = typing.Union[ast.For, ast.While, ast.AsyncFor]


class BreakAllTransformer(ast.NodeTransformer):
    """
    A node transformer which fixes the source code by replacing all "breakall" with a way to break multiple loops at once.

    Note
    ----
    ... breakall # break all loops
    ... breakall: 2 # break 2 loops
    ... breakall: 1 # same as `break`

    Example
    -------
    >>> source = '''
    ... for i in range(10):
    ...     for j in range(10):
    ...        breakall
    ... '''
    >>> tree = ast.parse(source)
    >>> BreakAllTransformer().visit(tree)
    # Produces an AST tree which is equivalent to:
    @BreakAll1 = type("breakall", (Exception,), {})
    try:
        for i in range(10):
            @BreakAll2 = type("breakall", (Exception,), {})
            try:
                for j in range(10):
                    raise @BreakAll1
            except @BreakAll2:
                pass
    except @BreakAll1:
        pass

    Raises
    ------
    SyntaxError
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
        except IndexError:
            # This is might be an unassigned lambda function
            self._functions.append("<lambda>")
        node = self.generic_visit(node)
        self._functions.pop()
        return node

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
        self._loop_counter += 1  # type: ignore
        loop_body: typing.Union[ast.stmt, typing.List[ast.stmt]] = self.generic_visit(
            node
        )
        result: BreakAllTransformer.visit_Loop_ReturnType
        if self._loop_counter in self._usage:
            assignment = ast.Assign(
                targets=[ast.Name(f"@BreakAll{self._loop_counter}", ast.Store())],
                value=ast.Call(
                    func=ast.Name("type", ast.Load()),
                    args=[
                        ast.Constant("breakall"),
                        ast.Tuple(
                            elts=[ast.Name("Exception", ast.Load())], ctx=ast.Load()
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
                        type=ast.Name(f"@BreakAll{self._loop_counter}", ast.Load()),
                        name=None,
                        body=[ast.Pass()],
                    )
                ],
                orelse=[],
                finalbody=[],
            )
            result = [assignment, try_block]
            self._usage.remove(self._loop_counter)
        else:
            result = loop_body
        self._loop_counter -= 1
        return result

    visit_For = visit_Loop
    visit_While = visit_Loop
    visit_AsyncFor = visit_Loop

    def build_syntax_error(
        self,
        title: str,
        message: str,
        node: typing.Union[ast.stmt, ast.expr],
        spacing: int,
        error_length: int,
        indicator: str = "~",
    ) -> str:
        """
        Builds the error message for syntax errors

        Parameters
        ----------
        title: str
            The title of the error
        message: str
            The message of the error
        node: expr | stmt
            The node which caused the error
        spacing: int
            The spacing before the error happened in the line
        error_length: int
            The length of the error
        indicator: str, default = ~

        Returns
        -------
        str
            The error message
        """
        function_name = ".".join(self._functions)
        msgs = [
            title,
            f'File "{self.filename}", line {node.lineno + self.start_line - 1}, in {function_name}',
            f"{' ' * node.col_offset}{ast.unparse(node)}",
            f"{' ' * node.col_offset}{' ' * spacing}{indicator * error_length}",
            message,
        ]
        return "\n".join(msgs)

    def visit_Assign(self, node: ast.Assign) -> ast.AST:
        """
        Parameters
        ----------
        node: Assign

        Returns
        -------
        AST
        """
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and isinstance(node.value, ast.Lambda):
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

    def visit_AnnAssign(self, node: ast.AnnAssign) -> ast.AST:
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
        SyntaxError
        """
        # If the `breakall` statement also has a break count
        if isinstance(node.target, ast.Name) and node.target.id == "breakall":
            if not isinstance(node.annotation, ast.Constant):
                raise SyntaxError(
                    self.build_syntax_error(
                        "Invalid break count",
                        "The break count must be a literal",
                        node,
                        len(node.target.id) + 2,
                        len(ast.unparse(node.annotation)),
                    )
                )
            try:
                parsed_break_count = int(node.annotation.value)
            except Exception:
                raise SyntaxError(
                    self.build_syntax_error(
                        "Invalid break count",
                        f"Cannot parse the break count `{node.annotation.value}`",
                        node,
                        len(node.target.id) + 2,
                        len(repr(node.annotation.value)),
                    )
                )
            if parsed_break_count == 1:
                # Little optimization
                return ast.Break()
            if parsed_break_count < 1:
                raise SyntaxError(
                    self.build_syntax_error(
                        "Invalid break count",
                        "The break count must be greater than 0",
                        node,
                        len(node.target.id) + 2,
                        len(repr(node.annotation.value)),
                    )
                )
            destination = self._loop_counter - parsed_break_count + 1
            if destination < 1:
                raise SyntaxError(
                    self.build_syntax_error(
                        "Invalid break count",
                        f"There {('are' if self._loop_counter > 1 else 'is')} only {self._loop_counter} loop{('s' if self._loop_counter > 1 else '')} to break.",
                        node,
                        len(node.target.id) + 2,
                        len(repr(node.annotation.value)),
                    )
                )
            self._usage.add(destination)
            return ast.Raise(
                exc=ast.Call(
                    func=ast.Name(f"@BreakAll{destination}", ast.Load()),
                    args=[],
                    keywords=[],
                ),
                cause=None,
            )
        elif isinstance(node.value, ast.Lambda) and isinstance(node.target, ast.Name):
            self._lambdas_names[node.value] = node.target.id
        return self.generic_visit(node)

    def visit_Expr(self, node: ast.Expr) -> ast.AST:
        """
        Parameters
        ----------
        node: Expr

        Returns
        -------
        AST

        Raises
        ------
        SyntaxError
        """
        # If the expression is a `breakall` statement
        if (
            isinstance(node.value, ast.Name) and node.value.id == "breakall"
        ):  # `@BreakAll1` is always the first loop
            self._usage.add(1)
            return ast.Raise(
                exc=ast.Call(
                    func=ast.Name(f"@BreakAll1", ast.Load()), args=[], keywords=[]
                ),
                cause=None,
            )
        if isinstance(node.value, ast.UnaryOp):
            if (
                isinstance(node.value.operand, ast.Name)
                and node.value.operand.id == "breakall"
            ):
                OPERATOR_REPR: typing.Dict[
                    typing.Type[typing.Union[ast.operator, ast.unaryop]], str
                ] = {ast.UAdd: "+", ast.USub: "-", ast.Not: "not", ast.Invert: "~"}
                operator_repr = OPERATOR_REPR.get(
                    type(node.value.op), ast.unparse(node.value.op)
                )
                raise SyntaxError(
                    self.build_syntax_error(
                        "Invalid break operation",
                        "The `breakall` statement must be alone, followed by `:` and a break count or `@` and a loop number",
                        node,
                        0,
                        len(operator_repr),
                    )
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
                raise SyntaxError(
                    self.build_syntax_error(
                        "Invalid break operation",
                        f"The `breakall` statement must be alone, followed by `:` and a break count or `@` and a loop number, not `{operator_repr}`",
                        node,
                        len(value.left.id) + 1,
                        operator_length,
                    )
                )
            # + 3 for the space before the operator, the `@` operator and the space after the operator
            if not isinstance(value.right, ast.Constant):
                raise SyntaxError(
                    self.build_syntax_error(
                        "Invalid loop number",
                        "The loop number must be a literal",
                        node,
                        len(value.left.id) + 3,
                        len(ast.unparse(value.right)),
                    )
                )
            try:
                parsed_loop_number = int(value.right.value)
            except Exception:
                raise SyntaxError(
                    self.build_syntax_error(
                        "Invalid loop number",
                        f"Cannot parse the loop number `{value.right.value}`",
                        node,
                        len(value.left.id) + 3,
                        len(repr(value.right.value)),
                    )
                )
            if parsed_loop_number == self._loop_counter:
                # for i in range(n): # Loop 1
                #     for j in range(m): # Loop 2
                #         breakall @ 2
                # `breakall @ 2` breaks the second loop which is equivalent to `break`
                return ast.Break()
            if parsed_loop_number < 1:
                raise SyntaxError(
                    self.build_syntax_error(
                        "Invalid loop number",
                        "The loop number must be greater than 0",
                        node,
                        len(value.left.id) + 3,
                        len(repr(value.right.value)),
                    )
                )
            if parsed_loop_number > self._loop_counter:
                raise SyntaxError(
                    self.build_syntax_error(
                        "Invalid loop number",
                        f"There {('are' if self._loop_counter > 1 else 'is')} only {self._loop_counter} loop{('s' if self._loop_counter > 1 else '')} to break up until this point. Note that it is impossible to break to a loop defined later.",
                        node,
                        len(value.left.id) + 3,
                        len(repr(value.right.value)),
                    )
                )
            self._usage.add(parsed_loop_number)
            return ast.Raise(
                exc=ast.Call(
                    func=ast.Name(f"@BreakAll{parsed_loop_number}", ast.Load()),
                    args=[],
                    keywords=[],
                ),
                cause=None,
            )
        return self.generic_visit(node)


def fix_source(
    source: str, filename: str = "<string>", start_line: int = 0
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
    @BreakAll1 = type("breakall", (Exception,), {})
    try:
        for i in range(10):
            @BreakAll2 = type("breakall", (Exception,), {})
            try:
                for j in range(10):
                    raise @BreakAll1
            except @BreakAll2:
                pass
    except @BreakAll1:
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
    tree = BreakAllTransformer(filename=filename, start_line=start_line).visit(tree)
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
    ValueError
        If the function source code could not be retrieved
    """
    if func is None:
        # Enable the `breakall` function for all functions in the current global scope
        frame = inspect.currentframe()
        if frame is None:
            raise ValueError("The current frame could not be retrieved")
        try:
            for name, obj in globals().items():
                if callable(obj):
                    globals()[name] = enable_breakall(obj)
        finally:
            del frame
        return
    # Gets the source code of the function
    source_lines, start_line = inspect.getsourcelines(func)
    if not source_lines:
        raise ValueError("The function source code could not be retrieved")
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
    return hasattr(func, "supports_breakall") and func.supports_breakall  # type: ignore

