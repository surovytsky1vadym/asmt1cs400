#!/usr/bin/env python3
"""
KaguLang Compiler — a gaming-themed emoji programming language.

Usage:
    python3 compiler.py --ast input.txt
"""

import sys

from kagu.errors import CompileError
from kagu.lexer import Lexer
from kagu.parser import Parser


USAGE = "usage: python3 compiler.py --ast <input_file>"


def main() -> int:
    if len(sys.argv) != 3 or sys.argv[1] != "--ast":
        print(USAGE, file=sys.stderr)
        return 2

    filename = sys.argv[2]
    try:
        with open(filename, "rb") as f:
            data = f.read()
    except OSError as exc:
        print(f"error: cannot read {filename}: {exc.strerror}", file=sys.stderr)
        return 2

    try:
        tokens = Lexer(data).tokenize()
        ast    = Parser(tokens).parse()
    except CompileError as err:
        print(err.report(), file=sys.stderr)
        return 1

    print(ast.dump())
    return 0


if __name__ == "__main__":
    sys.exit(main())
