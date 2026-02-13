"""The CLI for the `breakall` module"""

import argparse
import ast
import pathlib
import typing

import breakall

GLOBAL_ENV = {"breakall": breakall, "__name__": "__main__"}


def main(file: pathlib.Path, output: typing.Optional[str] = None) -> None:
    """
    Parameters
    ----------
    file: Path
    output: NoneType | str, default = None
    """
    # Reading the source code
    with open(file) as f:
        source = f.read()
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
    code = compile(tree, file, "exec")
    exec(code, GLOBAL_ENV, None)
    # Writing the modified code
    if output:
        result = ast.unparse(tree)
        if output == "-":
            print(result)
        else:
            with open(output, "w") as f:
                f.write(result)


def entry() -> None:
    """The main entry point of the module"""
    parser = argparse.ArgumentParser(
        prog="breakall",
        description="Break from multiple loops at once in Python",
    )
    parser.add_argument("file", help="The file to run", type=pathlib.Path)
    # parser.add_argument(
    #     "--trace",
    #     help="Enable tracing. This WILL slow down the execution of the program but will hook and modify every function call.",
    #     action="store_true",
    #     default=False,
    # )
    parser.add_argument(
        "--output",
        help="If provided, will write the modified source code to the provided file.",
    )
    args = parser.parse_args()
    main(file=pathlib.Path(args.file), output=args.output)
