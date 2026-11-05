"""Semantic analysis: a separate pass over the AST before code generation.

It builds the symbol tables (variables, functions, structures), checks every
rule listed in README.md ("Semantic rules") and annotates the AST for the
code generator:

  * every expression gets `.ty`      — its type (a builtin name or StructInfo)
  * every identifier gets `.sym`     — the VarSymbol or FieldInfo it names
  * every call gets `.func`          — the FuncInfo it calls
  * every field step gets `.field`   — the FieldInfo it reaches
  * every declaration gets `.sym`    — the VarSymbol it creates
"""

from __future__ import annotations

from .errors import error_at
from .nodes import (
    ProgramNode, StmtNode, VarDeclNode, ConstDeclNode, AssignNode, IfNode,
    PrintNode, OverflowCheckNode, ReturnNode, CallStmtNode, FuncDeclNode,
    StructDeclNode, ExprNode, IntLiteralNode, BoolLiteralNode, IdentifierNode,
    BinaryOpNode, UnaryOpNode, StringLiteralNode, CallNode, NewNode, ReadNode,
    FieldStep, ChainNode,
)


I32, I64, BOOL = "i32", "i64", "bool"
INT_TYPES = (I32, I64)

INT_RANGE = {
    I32: (-2**31, 2**31 - 1),
    I64: (-2**63, 2**63 - 1),
}

_OP_TEXT = {
    "PLUS": "+", "MINUS": "-", "MUL": "*", "DIV": "/", "MOD": "%",
    "EQ": "==", "NEQ": "!=", "GT": ">", "LT": "<", "GTE": ">=", "LTE": "<=",
    "AND": "&&", "OR": "||", "NEG": "-", "NOT": "!",
}


def type_name(ty) -> str:
    return ty if isinstance(ty, str) else ty.name


# ═══════════════════════════════════════════════════════════════════════════════
#  Symbol table entries
# ═══════════════════════════════════════════════════════════════════════════════

class VarSymbol:
    """A variable, constant or parameter.  `kind` is global / local / param."""
    def __init__(self, name: str, ty, mutable: bool, kind: str):
        self.name    = name
        self.ty      = ty
        self.mutable = mutable
        self.kind    = kind
        self.ptr     = None          # storage, filled in by the code generator


class FieldInfo:
    """A structure field: its position in the structure is `index`."""
    def __init__(self, name: str, ty, mutable: bool, index: int, owner: "StructInfo"):
        self.name    = name
        self.ty      = ty
        self.mutable = mutable
        self.index   = index
        self.owner   = owner


class FuncInfo:
    """A function or member function signature and its analysis results."""
    def __init__(self, decl: FuncDeclNode, owner: "StructInfo | None"):
        self.decl   = decl
        self.name   = decl.name
        self.owner  = owner
        self.params: list = []       # parameter types, in order
        self.result = None
        # Member functions only: does the body assign a field of the object,
        # directly or through another member function called on it?
        self.assigns_field = False
        self.self_calls: list[FuncInfo] = []
        self.mutating = False
        self.ir = None               # llvmlite function, filled in by codegen

    @property
    def display(self) -> str:
        return self.name if self.owner is None else f"{self.owner.name}.{self.name}"


class StructInfo:
    """A structure: fields in declaration order, member functions by name."""
    def __init__(self, decl: StructDeclNode):
        self.decl    = decl
        self.name    = decl.name
        self.fields: list[FieldInfo] = []
        self.field_map: dict[str, FieldInfo] = {}
        self.members: dict[str, FuncInfo] = {}
        self.ir_type = None          # llvmlite identified struct, filled in by codegen


class Scope:
    """One block of declarations; lookups walk outwards through `parent`."""
    def __init__(self, parent: "Scope | None" = None):
        self.names: dict[str, VarSymbol] = {}
        self.parent = parent

    def lookup(self, name: str) -> VarSymbol | None:
        scope = self
        while scope is not None:
            if name in scope.names:
                return scope.names[name]
            scope = scope.parent
        return None


class _Context:
    """Where a statement is being checked."""
    def __init__(self, scope: Scope, func: FuncInfo | None = None,
                 globals_seen: dict | None = None):
        self.scope        = scope
        self.func         = func
        self.struct       = func.owner if func else None
        self.globals_seen = globals_seen     # globals visible from a function body


# ═══════════════════════════════════════════════════════════════════════════════
#  Analyzer
# ═══════════════════════════════════════════════════════════════════════════════

class Analyzer:
    def __init__(self):
        self.structs: dict[str, StructInfo] = {}
        self.functions: dict[str, FuncInfo] = {}
        self.members: list[FuncInfo] = []
        self.global_scope = Scope()
        self.globals: list[VarSymbol] = []
        self.main_body: list[StmtNode] = []
        # (callee, receiver is mutable, call node) for every member call
        self._member_calls: list = []

    # ── entry point ─────────────────────────────────────────────────────

    def analyze(self, program: ProgramNode):
        self._collect(program)
        self._resolve_signatures()
        self._check_struct_cycles()

        main_ctx = _Context(self.global_scope)
        returned = False
        for item in program.stmts:
            if isinstance(item, StructDeclNode):
                for member in item.members:
                    self._check_function(self.structs[item.name].members[member.name])
            elif isinstance(item, FuncDeclNode):
                self._check_function(self.functions[item.name])
            else:
                if returned:
                    error_at(item, "unreachable statement after 🏁")
                returned = self._check_stmt(item, main_ctx)
                self.main_body.append(item)

        self._resolve_mutating_members()

    # ── pass 1: names of structures and functions ───────────────────────

    def _collect(self, program: ProgramNode):
        for item in program.stmts:
            if isinstance(item, StructDeclNode):
                if item.name in self.structs:
                    error_at(item, f"structure '{item.name}' is already declared")
                self.structs[item.name] = StructInfo(item)
            elif isinstance(item, FuncDeclNode):
                if item.name in self.functions:
                    error_at(item, f"function '{item.name}' is already declared")
                self.functions[item.name] = FuncInfo(item, None)

    # ── pass 2: field types and every signature ─────────────────────────

    def _resolve_type(self, name: str, node):
        if name in (I32, I64, BOOL):
            return name
        if name in self.structs:
            return self.structs[name]
        error_at(node, f"unknown type '{name}'")

    def _resolve_signatures(self):
        for info in self.structs.values():
            for fdecl in info.decl.fields:
                if fdecl.name in info.field_map:
                    error_at(fdecl, f"field '{fdecl.name}' is declared twice in '{info.name}'")
                field = FieldInfo(fdecl.name, self._resolve_type(fdecl.type_name, fdecl),
                                  fdecl.mutable, fdecl.index, info)
                info.fields.append(field)
                info.field_map[field.name] = field
            for mdecl in info.decl.members:
                if mdecl.name in info.members:
                    error_at(mdecl, f"member function '{mdecl.name}' is declared twice "
                                    f"in '{info.name}'")
                if mdecl.name in info.field_map:
                    error_at(mdecl, f"'{mdecl.name}' is both a field and a member function "
                                    f"of '{info.name}'")
                member = FuncInfo(mdecl, info)
                self._resolve_func_types(member)
                info.members[member.name] = member
                self.members.append(member)
        for func in self.functions.values():
            self._resolve_func_types(func)

    def _resolve_func_types(self, func: FuncInfo):
        seen = set()
        for p in func.decl.params:
            if p.name in seen:
                error_at(p, f"parameter '{p.name}' is declared twice")
            seen.add(p.name)
            func.params.append(self._resolve_type(p.type_name, p))
        func.result = self._resolve_type(func.decl.result, func.decl)

    def _check_struct_cycles(self):
        """A structure may not contain itself, directly or through its fields."""
        state: dict[str, str] = {}

        def visit(info: StructInfo):
            state[info.name] = "visiting"
            for field in info.fields:
                if isinstance(field.ty, StructInfo):
                    if state.get(field.ty.name) == "visiting":
                        error_at(info.decl, f"structure '{info.name}' contains itself "
                                            f"through field '{field.name}'")
                    if field.ty.name not in state:
                        visit(field.ty)
            state[info.name] = "done"

        for info in self.structs.values():
            if info.name not in state:
                visit(info)

    # ── function bodies ─────────────────────────────────────────────────

    def _check_function(self, func: FuncInfo):
        scope = Scope()
        for pnode, pty in zip(func.decl.params, func.params):
            sym = VarSymbol(pnode.name, pty, False, "param")
            scope.names[pnode.name] = sym
            pnode.sym = sym
        # A body sees the globals declared above the function, not below it.
        ctx = _Context(scope, func, dict(self.global_scope.names))
        if not self._check_block(func.decl.body, ctx):
            error_at(func.decl, f"function '{func.display}' can reach its end without "
                                f"🏁 returning a value of type {type_name(func.result)}")

    def _check_block(self, stmts: list[StmtNode], ctx: _Context) -> bool:
        """Check statements in order; return True if the block always returns."""
        returned = False
        for stmt in stmts:
            if returned:
                error_at(stmt, "unreachable statement after 🏁")
            returned = self._check_stmt(stmt, ctx)
        return returned

    # ── statements ──────────────────────────────────────────────────────

    def _check_stmt(self, stmt: StmtNode, ctx: _Context) -> bool:
        if isinstance(stmt, (VarDeclNode, ConstDeclNode)):
            self._check_decl(stmt, ctx)
        elif isinstance(stmt, AssignNode):
            self._check_assign(stmt, ctx)
        elif isinstance(stmt, IfNode):
            return self._check_if(stmt, ctx)
        elif isinstance(stmt, PrintNode):
            for item in stmt.items:
                if isinstance(item, StringLiteralNode):
                    item.ty = "string"
                else:
                    self._expr(item, ctx)
        elif isinstance(stmt, OverflowCheckNode):
            self._check_overflow(stmt, ctx)
        elif isinstance(stmt, ReturnNode):
            if ctx.func is None:
                error_at(stmt, "🏁 can be used only inside a function")
            ty = self._expr(stmt.value, ctx)
            self._expect(stmt.value, ty, ctx.func.result,
                         f"function '{ctx.func.display}' returns")
            return True
        elif isinstance(stmt, CallStmtNode):
            self._expr(stmt.call, ctx)
        return False

    def _check_decl(self, decl, ctx: _Context):
        ty = self._resolve_type(decl.type_name, decl)
        value_ty = self._expr(decl.value, ctx)
        self._expect(decl.value, value_ty, ty, f"'{decl.name}' is declared as")
        if decl.name in ctx.scope.names:
            error_at(decl, f"'{decl.name}' is already declared in this scope")
        is_global = ctx.scope is self.global_scope
        sym = VarSymbol(decl.name, ty, decl.mutable, "global" if is_global else "local")
        ctx.scope.names[decl.name] = sym
        if is_global:
            self.globals.append(sym)
        decl.sym = sym

    def _check_if(self, stmt: IfNode, ctx: _Context) -> bool:
        cond_ty = self._expr(stmt.condition, ctx)
        if cond_ty != BOOL:
            error_at(stmt.condition, f"condition must be 🛡️ bool, got {type_name(cond_ty)}")
        then_returns = self._check_block(stmt.then_body, self._child(ctx))
        if stmt.else_body is None:
            return False
        else_returns = self._check_block(stmt.else_body, self._child(ctx))
        stmt.always_returns = then_returns and else_returns
        return stmt.always_returns

    @staticmethod
    def _child(ctx: _Context) -> _Context:
        return _Context(Scope(ctx.scope), ctx.func, ctx.globals_seen)

    def _check_overflow(self, stmt: OverflowCheckNode, ctx: _Context):
        ty = self._expr(stmt.expr, ctx)
        if ty not in INT_TYPES:
            error_at(stmt.expr, f"💥 checks an integer value, got {type_name(ty)}")
        if stmt.type_name not in INT_TYPES:
            error_at(stmt, f"💥 checks against an integer type, got {stmt.type_name}")
        value = self._literal_value(stmt.expr)
        lo, hi = INT_RANGE[stmt.type_name]
        if value is not None and not lo <= value <= hi:
            error_at(stmt.expr, f"value {value} does not fit in {stmt.type_name}")

    def _check_assign(self, stmt: AssignNode, ctx: _Context):
        target = stmt.target
        target_ty = self._expr(target, ctx)

        if isinstance(target, IdentifierNode):
            sym = target.sym
            if isinstance(sym, FieldInfo):
                if not sym.mutable:
                    error_at(target, f"cannot assign to constant field '{sym.name}'")
                ctx.func.assigns_field = True
            elif not sym.mutable:
                if sym.kind == "param":
                    error_at(target, f"cannot assign to parameter '{sym.name}': "
                                     f"parameters are constant")
                error_at(target, f"cannot assign to constant '{sym.name}'")
        else:
            # A chain of fields: every step, from the root on, must be mutable.
            root = target.base.sym
            path = ".".join([target.base.name] + [s.name for s in target.steps])
            if not root.mutable:
                what = "parameter" if getattr(root, "kind", None) == "param" else "constant"
                error_at(target.base, f"cannot assign to '{path}': {what} "
                                      f"'{root.name}' is not mutable")
            for step in target.steps:
                if not step.field.mutable:
                    error_at(step, f"cannot assign to '{path}': field '{step.name}' "
                                   f"of '{step.field.owner.name}' is constant")
            if isinstance(root, FieldInfo):
                ctx.func.assigns_field = True

        value_ty = self._expr(stmt.value, ctx)
        self._expect(stmt.value, value_ty, target_ty, "assignment target has type")

    # ── type compatibility ──────────────────────────────────────────────

    @staticmethod
    def _assignable(src, dst) -> bool:
        """An i32 widens to i64 implicitly; every other type must match."""
        return src == dst or (src == I32 and dst == I64)

    def _expect(self, node: ExprNode, src, dst, what: str):
        if self._assignable(src, dst):
            return
        value = self._literal_value(node)
        if value is not None and dst in INT_TYPES:
            error_at(node, f"integer literal {value} does not fit in {dst}")
        error_at(node, f"{what} {type_name(dst)}, got {type_name(src)}")

    @staticmethod
    def _literal_value(node: ExprNode):
        """The value of an integer literal, possibly negated; else None."""
        if isinstance(node, IntLiteralNode):
            return node.value
        if (isinstance(node, UnaryOpNode) and node.op == "NEG"
                and isinstance(node.operand, IntLiteralNode)):
            return -node.operand.value
        return None

    # ── expressions ─────────────────────────────────────────────────────

    def _expr(self, e: ExprNode, ctx: _Context):
        e.ty = self._expr_type(e, ctx)
        return e.ty

    def _expr_type(self, e: ExprNode, ctx: _Context):
        if isinstance(e, IntLiteralNode):
            return self._literal_type(e, e.value)
        if isinstance(e, BoolLiteralNode):
            return BOOL
        if isinstance(e, IdentifierNode):
            e.sym = self._lookup(e, ctx)
            return e.sym.ty
        if isinstance(e, BinaryOpNode):
            return self._binary(e, ctx)
        if isinstance(e, UnaryOpNode):
            return self._unary(e, ctx)
        if isinstance(e, CallNode):
            return self._call(e, ctx)
        if isinstance(e, NewNode):
            return self._new(e, ctx)
        if isinstance(e, ReadNode):
            return I32
        if isinstance(e, ChainNode):
            return self._chain(e, ctx)
        if isinstance(e, StringLiteralNode):
            error_at(e, "a string literal can be used only in 📢")
        raise AssertionError(f"unknown expression node {type(e).__name__}")

    @staticmethod
    def _literal_type(node, value: int):
        for ty in INT_TYPES:
            lo, hi = INT_RANGE[ty]
            if lo <= value <= hi:
                return ty
        error_at(node, f"integer literal {value} does not fit in i64")

    def _lookup(self, node: IdentifierNode, ctx: _Context):
        """Locals and parameters (innermost block first), then the fields of
        the enclosing structure, then the globals declared above."""
        sym = ctx.scope.lookup(node.name)
        if sym is not None:
            return sym
        if ctx.struct is not None and node.name in ctx.struct.field_map:
            return ctx.struct.field_map[node.name]
        if ctx.globals_seen is not None and node.name in ctx.globals_seen:
            return ctx.globals_seen[node.name]
        error_at(node, f"'{node.name}' is not declared")

    def _binary(self, e: BinaryOpNode, ctx: _Context):
        lt = self._expr(e.left, ctx)
        rt = self._expr(e.right, ctx)
        op = _OP_TEXT[e.op]

        if e.op in ("AND", "OR"):
            if lt != BOOL or rt != BOOL:
                error_at(e, f"operator '{op}' needs bool operands, "
                            f"got {type_name(lt)} and {type_name(rt)}")
            return BOOL

        if e.op in ("EQ", "NEQ") and lt == BOOL and rt == BOOL:
            e.operand_ty = BOOL
            return BOOL

        if lt not in INT_TYPES or rt not in INT_TYPES:
            error_at(e, f"operator '{op}' needs integer operands, "
                        f"got {type_name(lt)} and {type_name(rt)}")
        # Mixed widths: the i32 operand is widened to i64.
        e.operand_ty = I64 if I64 in (lt, rt) else I32
        if e.op in ("PLUS", "MINUS", "MUL", "DIV", "MOD"):
            return e.operand_ty
        return BOOL

    def _unary(self, e: UnaryOpNode, ctx: _Context):
        if e.op == "NEG" and isinstance(e.operand, IntLiteralNode):
            # Fold "-literal" so that the minimum i32 / i64 value is accepted.
            e.folded = -e.operand.value
            e.operand.ty = self._literal_type(e, e.folded)
            return e.operand.ty
        ty = self._expr(e.operand, ctx)
        if e.op == "NEG" and ty not in INT_TYPES:
            error_at(e, f"unary '-' needs an integer operand, got {type_name(ty)}")
        if e.op == "NOT" and ty != BOOL:
            error_at(e, f"operator '!' needs a bool operand, got {type_name(ty)}")
        return ty

    def _check_args(self, args: list[ExprNode], func: FuncInfo, node, ctx: _Context):
        if len(args) != len(func.params):
            error_at(node, f"'{func.display}' expects {len(func.params)} argument(s), "
                           f"got {len(args)}")
        for i, (arg, pty) in enumerate(zip(args, func.params), start=1):
            self._expect(arg, self._expr(arg, ctx), pty,
                         f"argument {i} of '{func.display}' must be")

    def _call(self, e: CallNode, ctx: _Context):
        # Inside a structure, a bare call names a member function first.
        if ctx.struct is not None and e.name in ctx.struct.members:
            e.func = ctx.struct.members[e.name]
            e.on_self = True
            self._check_args(e.args, e.func, e, ctx)
            ctx.func.self_calls.append(e.func)
            return e.func.result
        if e.name not in self.functions:
            error_at(e, f"unknown function '{e.name}'")
        e.func = self.functions[e.name]
        e.on_self = False
        self._check_args(e.args, e.func, e, ctx)
        return e.func.result

    def _new(self, e: NewNode, ctx: _Context):
        if e.type_name not in self.structs:
            error_at(e, f"unknown structure '{e.type_name}'")
        info = self.structs[e.type_name]
        if len(e.args) != len(info.fields):
            error_at(e, f"structure '{info.name}' has {len(info.fields)} field(s), "
                        f"but {len(e.args)} value(s) were given")
        for arg, field in zip(e.args, info.fields):
            self._expect(arg, self._expr(arg, ctx), field.ty,
                         f"field '{field.name}' of '{info.name}' is")
        return info

    def _chain(self, e: ChainNode, ctx: _Context):
        ty = self._expr(e.base, ctx)
        # Is the object reached so far mutable, and is it (part of) the
        # object a member function was called on?
        mutable, on_self = False, False
        if isinstance(e.base, IdentifierNode):
            mutable = e.base.sym.mutable
            on_self = isinstance(e.base.sym, FieldInfo)

        for step in e.steps:
            if not isinstance(ty, StructInfo):
                error_at(step, f"'.{step.name}' needs a structure, got {type_name(ty)}")
            if isinstance(step, FieldStep):
                if step.name not in ty.field_map:
                    error_at(step, f"structure '{ty.name}' has no field '{step.name}'")
                step.field = ty.field_map[step.name]
                mutable = mutable and step.field.mutable
                ty = step.field.ty
            else:
                if step.name not in ty.members:
                    error_at(step, f"structure '{ty.name}' has no member function "
                                   f"'{step.name}'")
                step.func = ty.members[step.name]
                self._check_args(step.args, step.func, step, ctx)
                self._member_calls.append((step.func, mutable, step))
                if on_self:
                    ctx.func.self_calls.append(step.func)
                ty = step.func.result
                mutable, on_self = False, False       # a call result is a temporary
            step.ty = ty
        return ty

    # ── mutating member functions ───────────────────────────────────────

    def _resolve_mutating_members(self):
        """A member function is mutating if it assigns a field, or calls a
        mutating member function on its own object or one of its fields.
        Iterate to a fixed point, then check every call on an object."""
        for member in self.members:
            member.mutating = member.assigns_field
        changed = True
        while changed:
            changed = False
            for member in self.members:
                if not member.mutating and any(c.mutating for c in member.self_calls):
                    member.mutating = True
                    changed = True

        for callee, receiver_mutable, node in sorted(
                self._member_calls, key=lambda c: (c[2].line, c[2].col)):
            if callee.mutating and not receiver_mutable:
                error_at(node, f"cannot call mutating member function "
                               f"'{callee.display}' on a constant object")
