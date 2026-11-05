#!/usr/bin/env python3
"""
KaguLang Compiler — a gaming-themed emoji programming language.

Usage:
    python3 compiler.py input.txt output.ll     compile to LLVM IR
    python3 compiler.py --ast input.txt         print the AST

--optimize, anywhere on the command line, runs the tree optimizer before code
generation; together with --ast it prints the tree after the optimizer.
"""

from __future__ import annotations

import sys

from kagu.errors import CompileError
from kagu.lexer import Lexer
from kagu.parser import Parser


USAGE = ("usage: python3 compiler.py [--optimize] <input_file> <output.ll>\n"
         "       python3 compiler.py [--optimize] --ast <input_file>")


def read_source(filename: str) -> bytes | None:
    try:
        with open(filename, "rb") as f:
            return f.read()
    except OSError as exc:
        print(f"error: cannot read {filename}: {exc.strerror}", file=sys.stderr)
        return None


def optimized_tree(data: bytes):
    """Parse, check and optimize; return the tree and its final analysis."""
    from kagu.optimizer import optimize

    program = Parser(Lexer(data).tokenize()).parse()
    return program, optimize(program)


def compile_to_ir(data: bytes, opt: bool) -> str:
    # Imported here so that --ast works without llvmlite installed.
    from kagu.semantic import Analyzer
    from kagu.codegen import CodeGen

    if opt:
        _, analyzer = optimized_tree(data)
    else:
        program = Parser(Lexer(data).tokenize()).parse()
        analyzer = Analyzer()
        analyzer.analyze(program)
    return CodeGen(analyzer).generate()


def main() -> int:
    args = sys.argv[1:]
    opt = "--optimize" in args
    args = [a for a in args if a != "--optimize"]
    ast_mode = "--ast" in args
    args = [a for a in args if a != "--ast"]
    if len(args) != (1 if ast_mode else 2):
        print(USAGE, file=sys.stderr)
        return 2

    if ast_mode:
        data = read_source(args[0])
        if data is None:
            return 2
        try:
            if opt:
                ast, _ = optimized_tree(data)
            else:
                ast = Parser(Lexer(data).tokenize()).parse()
        except CompileError as err:
            print(err.report(), file=sys.stderr)
            return 1
        print(ast.dump())
        return 0

    in_file, out_file = args
    data = read_source(in_file)
    if data is None:
        return 2
    try:
        module_text = compile_to_ir(data, opt)
    except CompileError as err:
        print(err.report(), file=sys.stderr)
        return 1
    except RecursionError:
        print("compilation error: line 1:1: program is nested too deeply", file=sys.stderr)
        return 1

    try:
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(module_text)
    except OSError as exc:
        print(f"error: cannot write {out_file}: {exc.strerror}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
