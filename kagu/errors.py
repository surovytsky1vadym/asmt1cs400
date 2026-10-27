"""Compilation errors shared by every compiler phase."""


class CompileError(Exception):
    """A lexical, syntax or semantic error at a source position."""

    def __init__(self, line: int, col: int, message: str):
        super().__init__(message)
        self.line    = line
        self.col     = col
        self.message = message

    def report(self) -> str:
        return f"compilation error: line {self.line}:{self.col}: {self.message}"


def error_at(node, message: str):
    """Raise a CompileError at the position of a token or AST node."""
    raise CompileError(node.line, node.col, message)
