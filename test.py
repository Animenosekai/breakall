
def main():
    """wow a nice test function"""
    for i in range(10):
        for j in range(10):
            for k in range(10):
                print(i, j, k)
                # raise locals()[f"@BreakAll{callable()}"]()
                breakall: 2
            print("This will not print")
    print("Hey")
    for i in range(10):
        for j in range(10):
            for k in range(10):
                print(i, j, k)
                # raise locals()[f"@BreakAll{callable()}"]()
                breakall: 3
            breakall @ 3
            print("This will not print")
    print("Hey")

if __name__ == "__main__":
    main()

