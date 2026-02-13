# breakall

<img src="./assets/logo3.png" alt="Logo" align="right" height="220px">

## Break from multiple loops at once in Python

***Why isn't this a thing in Python?***

[![PyPI version](https://badge.fury.io/py/breakall.svg)](https://pypi.org/project/breakall/)
[![Downloads](https://static.pepy.tech/personalized-badge/breakall?period=total&units=international_system&left_color=grey&right_color=blue&left_text=Total%20Downloads)](https://pepy.tech/project/breakall)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/breakall)](https://pypistats.org/packages/breakall)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/breakall)](https://pypi.org/project/breakall/)
[![PyPI - Status](https://img.shields.io/pypi/status/breakall)](https://pypi.org/project/breakall/)
[![GitHub - License](https://img.shields.io/github/license/Animenosekai/breakall)](https://github.com/Animenosekai/breakall/blob/main/LICENSE)
[![GitHub Top Language](https://img.shields.io/github/languages/top/Animenosekai/breakall)](https://github.com/Animenosekai/breakall)
[![CI](https://github.com/Animenosekai/breakall/actions/workflows/ci.yml/badge.svg)](https://github.com/Animenosekai/breakall/actions/workflows/ci.yml)
[![Code Coverage](https://codecov.io/gh/Animenosekai/breakall/branch/main/graph/badge.svg)](https://codecov.io/gh/Animenosekai/breakall)
![Code Size](https://img.shields.io/github/languages/code-size/Animenosekai/breakall)
![Repo Size](https://img.shields.io/github/repo-size/Animenosekai/breakall)
![Issues](https://img.shields.io/github/issues/Animenosekai/breakall)

## Index

- [Break from multiple loops at once in Python](#break-from-multiple-loops-at-once-in-python)
- [Index](#index)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Basic Usage](#basic-usage)
- [Keyword](#keyword)
  - [`breakall`](#breakall-1)
  - [`breakall: n`](#breakall-n)
  - [`breakall @ n`](#breakall--n)
- [Linter and Type Checker Configuration](#linter-and-type-checker-configuration)
  - [Importing breakall](#importing-breakall)
  - [Ruff](#ruff)
  - [Pyright](#pyright)
- [Command-Line Interface](#command-line-interface)
  - [Tracing Imported Modules](#tracing-imported-modules)
    - [Example: Without `--trace`](#example-without---trace)
    - [Example: With `--trace`](#example-with---trace)
  - [Saving Transformed Code](#saving-transformed-code)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [Authors](#authors)
- [Disclaimer](#disclaimer)
- [License](#license)

## Getting Started

### Prerequisites

You will need Python +3.10 to run this module

```bash
# vermin output
Minimum required versions: 3.10
Incompatible versions:     2
```

> [!NOTE]  
> The heavy use of `ast.unparse` makes this incompatible with Python version lower than 3.10

### Installation

```bash
pip install --upgrade breakall
```

### Basic Usage

You can use `breakall` by decorating your function with `@enable_breakall`:

```python
>>> from breakall import enable_breakall
>>>
>>> @enable_breakall
... def main():
...     for i in range(10):
...         for j in range(10):
...             for k in range(10):
...                 if k == 5:
...                     breakall
...                 print(i, j, k)
```

Alternatively, you can enable `breakall` for all functions in your module by calling `enable_breakall()` without arguments:

```python
from breakall import enable_breakall

def main():
    for i in range(10):
        for j in range(10):
            for k in range(10):
                if k == 5:
                    breakall
                print(i, j, k)

# This will enable breakall for all functions in the current scope
enable_breakall()

main()
```

Or you can use the command-line interface:

```bash
python -m breakall script.py
# or
breakall script.py
```

This will automatically enable `breakall` for all functions in the file.

## Keyword

You can use `breakall` to break from multiple loops at once.

There is different syntax to determine how many loops to break from.

### `breakall`

The `breakall` keyword will break from all loops in the current scope.

```python
>>> from breakall import enable_breakall
>>>
>>> @enable_breakall
... def test():
...     for i in range(3):
...         for j in range(3):
...             if j == 1:
...                 breakall
...             print(f"  ({i}, {j})")
...         print(f"  End of i={i}")
...     print("Done")
>>>
>>> test()
  (0, 0)
Done
```

As you can see, the loops are completely exited without printing the rest of the iterations or "End of i={i}" message.

### `breakall: n`

The `breakall: n` keyword will break from `n` loops in the current scope.

```python
>>> from breakall import enable_breakall
>>>
>>> @enable_breakall
... def test():
...     for i in range(3):
...         for j in range(3):
...             for k in range(3):
...                 if k == 1:
...                     breakall: 2
...                 print(f"    ({i}, {j}, {k})")
...             print(f"  End of j={j}")
...         print(f"End of i={i}")
...     print("Done")
>>>
>>> test()
    (0, 0, 0)
End of i=0
    (1, 0, 0)
End of i=1
    (2, 0, 0)
End of i=2
Done
```

In this example, `breakall: 2` breaks from the innermost two loops (the `j` and `k` loops), but the outermost `i` loop continues.

### `breakall @ n`

The `breakall @ n` keyword will break from all loops up to and including the `n`-th loop from the inside.

```python
>>> from breakall import enable_breakall
>>>
>>> @enable_breakall
... def test():
...     for i in range(3):  # Loop 1
...         for j in range(3):  # Loop 2
...             for k in range(3):  # Loop 3
...                 if k == 1:
...                     breakall @ 2
...                 print(f"    ({i}, {j}, {k})")
...             print(f"  End of k loop")
...         print(f"End of j loop")
...     print("Done")
>>>
>>> test()
    (0, 0, 0)
    (1, 0, 0)
    (2, 0, 0)
Done
```

In this example, `breakall @ 2` targets loop 2 (the `j` loop), so it breaks from both loop 3 (`k`) and loop 2 (`j`), but loop 1 (`i`) continues.

> [!NOTE]
> The `breakall @ n` keyword is 1-indexed, where 1 is the innermost loop

## Linter and Type Checker Configuration

When using `breakall`, certain linting and type-checking tools may report false positives since they don't understand the `breakall` statement transformation.

### Importing breakall

You can import the `breakall` statement to make your type checker happy, but it is not necessary for the code to work:

```python
from breakall import breakall

def hello():
    for i in range(n):
        for j in range(m):
            if j == 1:
                breakall
            print(i, j)
```

### Ruff

Add to your module using `breakall`:

```python
# ruff: noqa: B018, F842
```

Where:

- `B018` - Useless expression (for bare `breakall` statements)
- `F842` - Local variable name is assigned to but never used (for `breakall: n` statements where the loop counter variable is not used)

### Pyright

Add to your module using `breakall`:

```python
# pyright: reportUnusedExpression=false, reportUnusedVariable=false, reportGeneralTypeIssues=false
```

Where:

- `reportUnusedExpression=false` - Allow unused expressions (for `breakall` statements)
- `reportUnusedVariable=false` - Allow unused variables (for `breakall: n` statements where the loop counter variable is not used)
- `reportGeneralTypeIssues=false` - Suppress general type issues that may when using `breakall: n` statements (`n` is an integer, not a type)

## Command-Line Interface

You can use the `breakall` module directly from the command line without decorating functions:

```bash
python -m breakall script.py
```

The CLI automatically applies `enable_breakall` to all functions in the target file:

```python
# my_script.py
def nested_loops():
    for i in range(3):
        for j in range(3):
            if j == 1:
                breakall
            print(f"  ({i}, {j})")
        print(f"  End of i={i}")
    print("Done")

nested_loops()
```

```bash
$ python -m breakall my_script.py
  (0, 0)
Done
```

### Tracing Imported Modules

By default, the CLI only applies `enable_breakall` to functions in the main file. If you're using `breakall` in imported modules, use the `--trace` flag:

```bash
python -m breakall script.py --trace
```

#### Example: Without `--trace`

If your imported module contains `breakall`, it will fail without `--trace`:

```python
# helper.py
def helper_function():
    for i in range(3):
        for j in range(3):
            if j == 1:
                breakall
            print(f"  ({i}, {j})")
        print(f"  End of i={i}")
    print("Done")
```

```python
# main.py
from helper import helper_function

helper_function()
```

```bash
$ python -m breakall main.py
  (0, 0)
Traceback (most recent call last):
  File "main.py", line 3, in <module>
    helper_function()
  File "helper.py", line 6, in helper_function
    breakall
NameError: name 'breakall' is not defined
```

#### Example: With `--trace`

Using `--trace` enables import hooking, so all imported modules support `breakall`:

```bash
$ python -m breakall main.py --trace
  (0, 0)
Done
```

The `--trace` flag automatically applies the `enable_breakall` decorator to all functions in imported modules, allowing them to use the `breakall` statement.

### Saving Transformed Code

You can save the transformed Python code to a file using the `--output` option:

```bash
python -m breakall script.py --output transformed.py
```

This generates a new file with all `breakall` statements converted to proper loop-breaking logic.

## Deployment

This module is currently in development and might contain bugs.

Feel free to use it in production if you feel like it is suitable for your production even if you may encounter issues.

## Contributing

Pull requests are welcome. For major changes, please open an discussion first to discuss what you would like to change.

Please make sure to update the tests as appropriate.

## Authors

- **Anime no Sekai** - *Initial work* - [Animenosekai](https://github.com/Animenosekai)

## Disclaimer

This project is not affiliated with the Python Software Foundation.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
