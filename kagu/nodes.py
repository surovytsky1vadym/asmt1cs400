"""AST node hierarchy.  Every node keeps the line:column it started at and
can dump itself as an indented tree for --ast."""

from __future__ import annotations

class ASTNode:
    """Base class for all AST nodes."""
    def __init__(self, line: int, col: int):
        self.line = line
        self.col  = col

    def dump(self, indent: int = 0) -> str:
        raise NotImplementedError


class ProgramNode(ASTNode):
    """Root node: a sequence of statements."""
    def __init__(self, stmts: list["StmtNode"], line: int, col: int):
        super().__init__(line, col)
        self.stmts = stmts

    def dump(self, indent: int = 0) -> str:
        prefix = "  " * indent
        lines = [f"{prefix}Program"]
        for s in self.stmts:
            lines.append(s.dump(indent + 1))
        return "\n".join(lines)


# ── Statements ──────────────────────────────────────────────────────────────

class StmtNode(ASTNode):
    """Abstract base for statements."""
    pass


class VarDeclNode(StmtNode):
    """Variable declaration (mutable)."""
    def __init__(self, name: str, type_name: str, value: "ExprNode",
                 line: int, col: int):
        super().__init__(line, col)
        self.name      = name
        self.type_name = type_name
        self.value     = value
        self.mutable   = True

    def dump(self, indent: int = 0) -> str:
        prefix = "  " * indent
        lines = [
            f"{prefix}VarDecl(name={self.name}, type={self.type_name}, mutable={self.mutable})",
        ]
        lines.append(f"{prefix}  value:")
        lines.append(self.value.dump(indent + 2))
        return "\n".join(lines)


class ConstDeclNode(StmtNode):
    """Constant / immutable variable declaration."""
    def __init__(self, name: str, type_name: str, value: "ExprNode",
                 line: int, col: int):
        super().__init__(line, col)
        self.name      = name
        self.type_name = type_name
        self.value     = value
        self.mutable   = False

    def dump(self, indent: int = 0) -> str:
        prefix = "  " * indent
        lines = [
            f"{prefix}ConstDecl(name={self.name}, type={self.type_name}, mutable={self.mutable})",
        ]
        lines.append(f"{prefix}  value:")
        lines.append(self.value.dump(indent + 2))
        return "\n".join(lines)


class AssignNode(StmtNode):
    """Assignment statement."""
    def __init__(self, name: str, value: "ExprNode", line: int, col: int):
        super().__init__(line, col)
        self.name  = name
        self.value = value

    def dump(self, indent: int = 0) -> str:
        prefix = "  " * indent
        lines = [f"{prefix}Assign(name={self.name})"]
        lines.append(f"{prefix}  value:")
        lines.append(self.value.dump(indent + 2))
        return "\n".join(lines)


class IfNode(StmtNode):
    """If / else statement."""
    def __init__(self, condition: "ExprNode",
                 then_body: list[StmtNode],
                 else_body: list[StmtNode] | None,
                 line: int, col: int):
        super().__init__(line, col)
        self.condition = condition
        self.then_body = then_body
        self.else_body = else_body

    def dump(self, indent: int = 0) -> str:
        prefix = "  " * indent
        lines = [f"{prefix}If"]
        lines.append(f"{prefix}  condition:")
        lines.append(self.condition.dump(indent + 2))
        lines.append(f"{prefix}  then:")
        for s in self.then_body:
            lines.append(s.dump(indent + 2))
        if self.else_body is not None:
            lines.append(f"{prefix}  else:")
            for s in self.else_body:
                lines.append(s.dump(indent + 2))
        return "\n".join(lines)


class PrintNode(StmtNode):
    """Print statement."""
    def __init__(self, expr: "ExprNode", line: int, col: int):
        super().__init__(line, col)
        self.expr = expr

    def dump(self, indent: int = 0) -> str:
        prefix = "  " * indent
        lines = [f"{prefix}Print"]
        lines.append(f"{prefix}  expr:")
        lines.append(self.expr.dump(indent + 2))
        return "\n".join(lines)


class OverflowCheckNode(StmtNode):
    """Overflow check statement."""
    def __init__(self, expr: "ExprNode", type_name: str, line: int, col: int):
        super().__init__(line, col)
        self.expr      = expr
        self.type_name = type_name

    def dump(self, indent: int = 0) -> str:
        prefix = "  " * indent
        lines = [f"{prefix}OverflowCheck(type={self.type_name})"]
        lines.append(f"{prefix}  expr:")
        lines.append(self.expr.dump(indent + 2))
        return "\n".join(lines)


# ── Expressions ─────────────────────────────────────────────────────────────

class ExprNode(ASTNode):
    """Abstract base for expressions."""
    pass


class IntLiteralNode(ExprNode):
    """Integer literal."""
    def __init__(self, value: int, line: int, col: int):
        super().__init__(line, col)
        self.value = value

    def dump(self, indent: int = 0) -> str:
        return f"{'  ' * indent}IntLiteral({self.value})"


class BoolLiteralNode(ExprNode):
    """Boolean literal."""
    def __init__(self, value: bool, line: int, col: int):
        super().__init__(line, col)
        self.value = value

    def dump(self, indent: int = 0) -> str:
        return f"{'  ' * indent}BoolLiteral({self.value})"


class IdentifierNode(ExprNode):
    """Variable reference."""
    def __init__(self, name: str, line: int, col: int):
        super().__init__(line, col)
        self.name = name

    def dump(self, indent: int = 0) -> str:
        return f"{'  ' * indent}Identifier({self.name})"


class BinaryOpNode(ExprNode):
    """Binary operator expression."""
    def __init__(self, op: str, left: ExprNode, right: ExprNode,
                 line: int, col: int):
        super().__init__(line, col)
        self.op    = op
        self.left  = left
        self.right = right

    def dump(self, indent: int = 0) -> str:
        prefix = "  " * indent
        lines = [f"{prefix}BinaryOp(op={self.op})"]
        lines.append(f"{prefix}  left:")
        lines.append(self.left.dump(indent + 2))
        lines.append(f"{prefix}  right:")
        lines.append(self.right.dump(indent + 2))
        return "\n".join(lines)


class UnaryOpNode(ExprNode):
    """Unary operator expression."""
    def __init__(self, op: str, operand: ExprNode, line: int, col: int):
        super().__init__(line, col)
        self.op      = op
        self.operand = operand

    def dump(self, indent: int = 0) -> str:
        prefix = "  " * indent
        lines = [f"{prefix}UnaryOp(op={self.op})"]
        lines.append(f"{prefix}  operand:")
        lines.append(self.operand.dump(indent + 2))
        return "\n".join(lines)
