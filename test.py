import random

from breakall import enable_breakall


def random_number():
    """A random number generator"""
    return random.randint(1, 2)

def not_an_integer():
    """A function that returns a string"""
    return "not an integer"


def basic_breakall():
    """A basic function with a `breakall` statement"""
    print("basic_breakall")
    for i in range(10):
        for j in range(10):
            for k in range(10):
                if k == 5:
                    breakall
                print(i, j, k)


def breakall_count():
    """A function with a `breakall` statement with a count"""
    print("breakall_count")
    for i in range(10):  # 3 from the outermost loop
        for j in range(10):  # 2 from the innermost loop
            for k in range(10):  # 1 from the innermost loop
                breakall: 2
            print("This will not be printed")


def breakall_random_count():
    """A function with a `breakall` statement with a count"""
    print("breakall_random_count")
    for i in range(10):  # 3 from the outermost loop
        for j in range(10):  # 2 from the innermost loop
            for k in range(10):  # 1 from the innermost loop
                breakall: random_number()
            print("This has a chance of 1/2 to be printed")


def breakall_number():
    """A function with a `breakall` statement with a loop number"""
    print("breakall_number")
    for i in range(10):  # Loop 1
        for j in range(10):  # Loop 2
            for k in range(10):  # Loop 3
                for l in range(10):  # Loop 4
                    breakall @ 2
                print("This will not be printed")
            print("This will not be printed")


def breakall_expr_number():
    """A function with a `breakall` statement with a loop number"""
    print("breakall_expr_number")
    for i in range(10):  # Loop 1
        for j in range(10):  # Loop 2
            breakall @ (2 - 1)
        print("This will not be printed")

def breakall_minus_number():
    """A function with a `breakall` statement with a loop number"""
    print("breakall_random_number")
    for i in range(10):  # Loop 1
        for j in range(10):  # Loop 2
            breakall @ -1
            print("This will error out")

def breakall_non_valid_runtime_number():
    """A function with a `breakall` statement with a loop number"""
    print("breakall_random_number")
    for i in range(10):  # Loop 1
        for j in range(10):  # Loop 2
            breakall @ not_an_integer()
            print("This will error out")


if __name__ == "__main__":
    enable_breakall()
    basic_breakall()
    breakall_count()
    breakall_random_count()
    breakall_number()
    breakall_expr_number()
    breakall_minus_number()
    breakall_non_valid_runtime_number()

