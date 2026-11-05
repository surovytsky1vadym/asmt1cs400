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
    """Assignment to a variable (IdentifierNode) or a field chain (ChainNode)."""
    def __init__(self, target: "ExprNode", value: "ExprNode", line: int, col: int):
        super().__init__(line, col)
        self.target = target
        self.value  = value

    def dump(self, indent: int = 0) -> str:
        prefix = "  " * indent
        if isinstance(self.target, IdentifierNode):
            lines = [f"{prefix}Assign(name={self.target.name})"]
        else:
            lines = [f"{prefix}Assign(target=chain)"]
            lines.append(f"{prefix}  target:")
            lines.append(self.target.dump(indent + 2))
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
    """Print statement: one or more items, then a newline."""
    def __init__(self, items: list["ExprNode"], line: int, col: int):
        super().__init__(line, col)
        self.items = items

    def dump(self, indent: int = 0) -> str:
        prefix = "  " * indent
        lines = [f"{prefix}Print"]
        for item in self.items:
            lines.append(f"{prefix}  expr:")
            lines.append(item.dump(indent + 2))
        return "\n".join(lines)


class ReturnNode(StmtNode):
    """Leave the enclosing function with a value (🏁)."""
    def __init__(self, value: "ExprNode", line: int, col: int):
        super().__init__(line, col)
        self.value = value

    def dump(self, indent: int = 0) -> str:
        prefix = "  " * indent
        lines = [f"{prefix}Return"]
        lines.append(f"{prefix}  value:")
        lines.append(self.value.dump(indent + 2))
        return "\n".join(lines)


class CallStmtNode(StmtNode):
    """A call used as a statement; its result is discarded."""
    def __init__(self, call: "ExprNode", line: int, col: int):
        super().__init__(line, col)
        self.call = call

    def dump(self, indent: int = 0) -> str:
        prefix = "  " * indent
        lines = [f"{prefix}CallStmt"]
        lines.append(f"{prefix}  call:")
        lines.append(self.call.dump(indent + 2))
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


# ── Declarations ───────────────────────────────────────────────────────────

class ParamNode(ASTNode):
    """Function parameter (always constant inside the body)."""
    def __init__(self, name: str, type_name: str, line: int, col: int):
        super().__init__(line, col)
        self.name      = name
        self.type_name = type_name

    def dump(self, indent: int = 0) -> str:
        return f"{'  ' * indent}Param(name={self.name}, type={self.type_name}, mutable=False)"


class FuncDeclNode(StmtNode):
    """Function declaration; inside a structure it is a member function."""
    def __init__(self, name: str, params: list[ParamNode], result: str,
                 body: list[StmtNode], line: int, col: int):
        super().__init__(line, col)
        self.name   = name
        self.params = params
        self.result = result
        self.body   = body
        self.owner: str | None = None   # structure name for a member function

    def dump(self, indent: int = 0) -> str:
        prefix = "  " * indent
        if self.owner is None:
            head = f"FuncDecl(name={self.name}, result={self.result})"
        else:
            head = f"MemberFunc(struct={self.owner}, name={self.name}, result={self.result})"
        lines = [prefix + head]
        if self.params:
            lines.append(f"{prefix}  params:")
            for p in self.params:
                lines.append(p.dump(indent + 2))
        else:
            lines.append(f"{prefix}  params: (none)")
        lines.append(f"{prefix}  body:")
        for s in self.body:
            lines.append(s.dump(indent + 2))
        return "\n".join(lines)


class FieldDeclNode(ASTNode):
    """Structure field: 🎮 (mutable) or 🏰 (constant)."""
    def __init__(self, name: str, type_name: str, mutable: bool, index: int,
                 line: int, col: int):
        super().__init__(line, col)
        self.name      = name
        self.type_name = type_name
        self.mutable   = mutable
        self.index     = index

    def dump(self, indent: int = 0) -> str:
        return (f"{'  ' * indent}Field(name={self.name}, type={self.type_name}, "
                f"index={self.index}, mutable={self.mutable})")


class StructDeclNode(StmtNode):
    """Structure declaration with fields and member functions."""
    def __init__(self, name: str, fields: list[FieldDeclNode],
                 members: list[FuncDeclNode], line: int, col: int):
        super().__init__(line, col)
        self.name    = name
        self.fields  = fields
        self.members = members

    def dump(self, indent: int = 0) -> str:
        prefix = "  " * indent
        lines = [f"{prefix}StructDecl(name={self.name})"]
        lines.append(f"{prefix}  fields:" if self.fields else f"{prefix}  fields: (none)")
        for f in self.fields:
            lines.append(f.dump(indent + 2))
        if self.members:
            lines.append(f"{prefix}  members:")
            for m in self.members:
                lines.append(m.dump(indent + 2))
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


def _dump_args(args: list[ExprNode], indent: int) -> list[str]:
    prefix = "  " * indent
    if not args:
        return [f"{prefix}args: (none)"]
    lines = [f"{prefix}args:"]
    for a in args:
        lines.append(a.dump(indent + 1))
    return lines


class StringLiteralNode(ExprNode):
    """String literal; allowed only as an item of 📢."""
    def __init__(self, value: str, line: int, col: int):
        super().__init__(line, col)
        self.value = value

    def dump(self, indent: int = 0) -> str:
        escaped = (self.value.replace("\\", "\\\\").replace('"', '\\"')
                   .replace("\n", "\\n").replace("\t", "\\t"))
        return f'{"  " * indent}StringLiteral("{escaped}")'


class CallNode(ExprNode):
    """Call by bare name: a function, or (inside a structure) a member function."""
    def __init__(self, name: str, args: list[ExprNode], line: int, col: int):
        super().__init__(line, col)
        self.name = name
        self.args = args

    def dump(self, indent: int = 0) -> str:
        prefix = "  " * indent
        lines = [f"{prefix}Call(name={self.name}, args={len(self.args)})"]
        lines.extend(_dump_args(self.args, indent + 1))
        return "\n".join(lines)


class NewNode(ExprNode):
    """Object construction: 🆕 Type(one value per field, in order)."""
    def __init__(self, type_name: str, args: list[ExprNode], line: int, col: int):
        super().__init__(line, col)
        self.type_name = type_name
        self.args      = args

    def dump(self, indent: int = 0) -> str:
        prefix = "  " * indent
        lines = [f"{prefix}New(type={self.type_name}, args={len(self.args)})"]
        lines.extend(_dump_args(self.args, indent + 1))
        return "\n".join(lines)


class ReadNode(ExprNode):
    """📥() — read one integer from standard input."""
    def dump(self, indent: int = 0) -> str:
        return f"{'  ' * indent}Read"


class FieldStep(ASTNode):
    """One `.name` step of a chain."""
    def __init__(self, name: str, line: int, col: int):
        super().__init__(line, col)
        self.name = name

    def dump(self, indent: int = 0) -> str:
        return f"{'  ' * indent}Field(.{self.name})"


class MemberCallStep(ASTNode):
    """One `.name(args)` step of a chain."""
    def __init__(self, name: str, args: list[ExprNode], line: int, col: int):
        super().__init__(line, col)
        self.name = name
        self.args = args

    def dump(self, indent: int = 0) -> str:
        prefix = "  " * indent
        lines = [f"{prefix}MemberCall(.{self.name}, args={len(self.args)})"]
        lines.extend(_dump_args(self.args, indent + 1))
        return "\n".join(lines)


class ChainNode(ExprNode):
    """Postfix chain: a base expression followed by field / member-call steps."""
    def __init__(self, base: ExprNode, steps: list[ASTNode], line: int, col: int):
        super().__init__(line, col)
        self.base  = base
        self.steps = steps

    @property
    def ends_in_call(self) -> bool:
        return isinstance(self.steps[-1], MemberCallStep)

    def dump(self, indent: int = 0) -> str:
        prefix = "  " * indent
        lines = [f"{prefix}Chain(ends_in_member_call={self.ends_in_call})"]
        lines.append(f"{prefix}  base:")
        lines.append(self.base.dump(indent + 2))
        lines.append(f"{prefix}  steps:")
        for s in self.steps:
            lines.append(s.dump(indent + 2))
        return "\n".join(lines)
