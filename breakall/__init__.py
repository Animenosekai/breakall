"""
Enables the `breakall` statement in Python which allows you to break multiple loops at once.

Example
-------
>>> from breakall import breakall, enable_breakall, supports_breakall
>>> @enable_breakall
... def test():
...     for i in range(10):
...         for j in range(10):
...             breakall
...     # Should continue here because it breaks all the loops
...     for i in range(10):  # 3 up from breakall
...         for j in range(10):  # 2 up from breakall
...             for k in range(10):  # 1 up from breakall
...                 breakall: 2
...         # Should continue here because it breaks 2 loops
...     for i in range(10):  # Loop 1
...         for j in range(10):  # Loop 2
...             while True:  # Loop 3
...                 for l in range(10):  # Loop 4
...                     breakall @ 3
...             # Should continue here because it breaks loop 3
...             # (would infinite loop otherwise)
"""

from .__info__ import __author__, __copyright__, __license__, __version__
from .breakall import (BreakAllTransformer, breakall, enable_breakall,
                       fix_source, supports_breakall)
from .exceptions import BreakAllError, BreakAllEnvironmentError, BreakAllRuntimeError, BreakAllSyntaxError
from .runtime import destination_from_break_count, destination_from_loop_number

__all__ = [
    "breakall",
    "enable_breakall",
    "supports_breakall",
    "BreakAllTransformer",
    "fix_source",
    "destination_from_break_count",
    "destination_from_loop_number",
    "BreakAllError",
    "BreakAllEnvironmentError",
    "BreakAllRuntimeError",
    "BreakAllSyntaxError",
    "__author__",
    "__version__",
    "__license__",
    "__copyright__",
]

