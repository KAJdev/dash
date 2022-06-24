import random
import sys
from interpreter import Interpreter, Memory, StandardLibrary

from sys import stderr, stdout

class StdLib(StandardLibrary):
    def print(memory, *args):
        print(*args)

    def input(memory, *args):
        return input(*args)
    
    def len(memory, *args):
        return len(args[0])
    
    def range(memory, *args):
        return range(*args)

    def random(memory, *args):
        return random.randint(*args)

i = Interpreter(StdLib())

def count_blocks(i):
    c = 0
    for char in i:
        if char in "{(":
            c += 1
        elif char in "})":
            c -= 1
    return c

# get cli args to see if a filepath was passed
if len(sys.argv) > 1:
    with open(sys.argv[1], 'r') as f:
        code = f.read()

    try:
        i.eval(code)
    except Exception as e:
        stderr.write(f"\n  {sys.argv[1]} exited with errors:\n\n    {e.__class__.__name__}: {e}\n\n")

else:
    print("[DASH interactive interpreter v0.1]\n")

    while True:

        x = input(">> ")

        if x == "exit":
            break

        if x == "":
            continue
        
        opened = count_blocks(x)
        should_break_next = False
        while not x.endswith(";") or opened > 0:
            new_input = input(">  " + ("  " * opened))

            if new_input == "":
                should_break_next = True

            if should_break_next and new_input == "":
                break

            x += " " + new_input
            opened = count_blocks(x)

        try:
            i.eval(x)
        except Exception as e:
            print(e)