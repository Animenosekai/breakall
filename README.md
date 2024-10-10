# breakall

## Break from multiple loops at once in Python

***Why isn't this a thing in Python?***

[![PyPI version](https://badge.fury.io/py/breakall.svg)](https://pypi.org/project/breakall/)
[![Downloads](https://static.pepy.tech/personalized-badge/breakall?period=total&units=international_system&left_color=grey&right_color=blue&left_text=Total%20Downloads)](https://pepy.tech/project/breakall)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/breakall)](https://pypistats.org/packages/breakall)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/breakall)](https://pypi.org/project/breakall/)
[![PyPI - Status](https://img.shields.io/pypi/status/breakall)](https://pypi.org/project/breakall/)
[![GitHub - License](https://img.shields.io/github/license/Animenosekai/breakall)](https://github.com/Animenosekai/breakall/blob/master/LICENSE)
[![GitHub top language](https://img.shields.io/github/languages/top/Animenosekai/breakall)](https://github.com/Animenosekai/breakall)
[![CodeQL Checks Badge](https://github.com/Animenosekai/breakall/workflows/CodeQL%20Python%20Analysis/badge.svg)](https://github.com/Animenosekai/breakall/actions?query=workflow%3ACodeQL)
[![Pytest](https://github.com/Animenosekai/breakall/actions/workflows/pytest.yml/badge.svg)](https://github.com/Animenosekai/breakall/actions/workflows/pytest.yml)
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
- [Deployment](#deployment)
- [Contributing](#contributing)
- [Authors](#authors)
- [Disclaimer](#disclaimer)
- [License](#license)

## Getting Started

### Prerequisites

You will need Python +3.9 to run this module

```bash
# vermin output
Minimum required versions: 3.9
Incompatible versions:     2
```

> [!NOTE]  
> The heavy use of `ast.unparse` makes this incompatible with Python version lower than 3.9

### Installation

```bash
pip install git+https://github.com/Animenosekai/breakall.git
```

### Basic Usage

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

## Keyword

You can use `breakall` to break from multiple loops at once.

There is different syntax to determine how many loops to break from.

### `breakall`

The `breakall` keyword will break from all loops in the current scope.

```python
>>> from breakall import enable_breakall
>>>
>>> @enable_breakall
... def main():
...     for i in range(10):
...         for j in range(10):
...             breakall
...         print("This will not be printed")
```

### `breakall: n`

The `breakall: n` keyword will break from `n` loops in the current scope.

```python
>>> from breakall import enable_breakall
>>>
>>> @enable_breakall
... def main():
...     for i in range(10): # 3 from the outermost loop
...         for j in range(10): # 2 from the innermost loop
...             for k in range(10): # 1 from the innermost loop
...                 breakall: 2
...             print("This will not be printed")
```

### `breakall @ n`

The `breakall @ n` keyword will break from the `n`-th loop in the current scope.

```python
>>> from breakall import enable_breakall
>>>
>>> @enable_breakall
... def main():
...     for i in range(10): # Loop 1
...         for j in range(10): # Loop 2
...             for k in range(10): # Loop 3
...                 for l in range(10): # Loop 4
...                     breakall @ 2
...                 print("This will not be printed")
...             print("This will not be printed")
```

> [!NOTE]
> The `breakall @ n` keyword is 1-indexed

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
