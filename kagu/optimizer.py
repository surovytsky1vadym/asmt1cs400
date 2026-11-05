"""Tree optimizer behind --optimize: runs on the checked AST, before code
generation.  Three transformations, repeated until none of them changes
the tree:

  * unused variables  — a declaration nobody reads is removed together with
                        its assignments; a value that calls a function or
                        📥() is kept as a call statement
  * unused functions  — a function nobody calls is removed with its body
  * inlining          — a function called exactly once is replaced at its
                        call site by its body (see README for the shapes)

The tree is analysed again before every round, so each transformation can
rely on the annotations of the semantic pass (`.sym`, `.func`, `.ty`).
"""

from __future__ import annotations

import copy

from .nodes import (
    ASTNode, ProgramNode, VarDeclNode, ConstDeclNode, AssignNode, IfNode,
    WhileNode, ForNode, PrintNode, OverflowCheckNode, ReturnNode, CallStmtNode,
    FuncDeclNode, StructDeclNode, IdentifierNode, BinaryOpNode, UnaryOpNode,
    CallNode, NewNode, ReadNode, ChainNode, MemberCallStep,
)
from .semantic import Analyzer, VarSymbol


# ═══════════════════════════════════════════════════════════════════════════════
#  Tree walking
# ═══════════════════════════════════════════════════════════════════════════════

def _blocks(stmt) -> list[list]:
    """The statement lists nested directly inside a statement."""
    if isinstance(stmt, IfNode):
        return [stmt.then_body] + ([stmt.else_body] if stmt.else_body is not None else [])
    if isinstance(stmt, (WhileNode, ForNode)):
        return [stmt.body]
    if isinstance(stmt, FuncDeclNode):
        return [stmt.body]
    if isinstance(stmt, StructDeclNode):
        return [m.body for m in stmt.members]
    return []


def _exprs(stmt) -> list:
    """The expressions a statement evaluates itself (not those of its blocks)."""
    if isinstance(stmt, (VarDeclNode, ConstDeclNode)):
        return [stmt.value]
    if isinstance(stmt, AssignNode):
        return [stmt.target, stmt.value]
    if isinstance(stmt, (IfNode, WhileNode)):
        return [stmt.condition]
    if isinstance(stmt, ForNode):
        return [stmt.start, stmt.end]
    if isinstance(stmt, PrintNode):
        return list(stmt.items)
    if isinstance(stmt, ReturnNode):
        return [stmt.value]
    if isinstance(stmt, CallStmtNode):
        return [stmt.call]
    if isinstance(stmt, OverflowCheckNode):
        return [stmt.expr]
    return []


def _children(e) -> list:
    if isinstance(e, BinaryOpNode):
        return [e.left, e.right]
    if isinstance(e, UnaryOpNode):
        return [e.operand]
    if isinstance(e, (CallNode, NewNode, MemberCallStep)):
        return list(e.args)
    if isinstance(e, ChainNode):
        return [e.base] + list(e.steps)
    return []


def _walk_expr(e):
    yield e
    for c in _children(e):
        yield from _walk_expr(c)


def _walk_stmts(stmts):
    """Every statement, nested ones included, with the list that holds it."""
    for stmt in stmts:
        yield stmt, stmts
        for block in _blocks(stmt):
            yield from _walk_stmts(block)


def _all_exprs(stmts):
    for stmt, _ in _walk_stmts(stmts):
        for e in _exprs(stmt):
            yield from _walk_expr(e)


def _has_effect(e) -> bool:
    """Does evaluating `e` call a function or read input?"""
    return any(isinstance(x, (CallNode, MemberCallStep, ReadNode)) for x in _walk_expr(e))


def _is_call(e) -> bool:
    return (isinstance(e, (CallNode, ReadNode))
            or (isinstance(e, ChainNode) and e.ends_in_call))


def _clone(node):
    """Copy the tree structure; annotations (.sym, .func, .ty) stay shared,
    so the copy still says which symbol every name refers to."""
    if isinstance(node, list):
        return [_clone(x) for x in node]
    if not isinstance(node, ASTNode):
        return node
    new = copy.copy(node)
    for key, value in vars(node).items():
        if isinstance(value, (ASTNode, list)):
            setattr(new, key, _clone(value))
    return new


def _replace(node, old, new) -> bool:
    """Put `new` where `old` stands among the expressions under `node`."""
    for key, value in vars(node).items():
        if value is old:
            setattr(node, key, new)
            return True
        if isinstance(value, list):
            for i, x in enumerate(value):
                if x is old:
                    value[i] = new
                    return True
                if isinstance(x, ASTNode) and _replace(x, old, new):
                    return True
        elif isinstance(value, ASTNode) and _replace(value, old, new):
            return True
    return False


# ═══════════════════════════════════════════════════════════════════════════════
#  Driver
# ═══════════════════════════════════════════════════════════════════════════════

def optimize(program: ProgramNode) -> Analyzer:
    """Optimize `program` in place; return the analysis of the final tree."""
    while True:
        sem = Analyzer()
        sem.analyze(program)
        if (_remove_unused_variables(program)
                or _remove_unused_functions(program)
                or _inline_one_call(program)):
            continue
        return sem


# ═══════════════════════════════════════════════════════════════════════════════
#  Unused variables
# ═══════════════════════════════════════════════════════════════════════════════

def _remove_unused_variables(program: ProgramNode) -> bool:
    # A name is read wherever it appears, except as the whole target of an
    # assignment and inside the value assigned to that same name (x = x + 1
    # does not make x used).  Symbols are compared by identity, so a
    # shadowing declaration is a different variable from the one it hides.
    read: set[int] = set()
    for stmt, _ in _walk_stmts(program.stmts):
        own = None
        if isinstance(stmt, AssignNode) and isinstance(stmt.target, IdentifierNode):
            own = stmt.target.sym
        for e in _exprs(stmt):
            if own is not None and e is stmt.target:
                continue
            for x in _walk_expr(e):
                if isinstance(x, IdentifierNode) and x.sym is not own:
                    read.add(id(x.sym))

    def unused(sym) -> bool:
        return isinstance(sym, VarSymbol) and sym.kind in ("local", "global") \
            and id(sym) not in read

    changed = False

    def rewrite(stmts: list):
        nonlocal changed
        out = []
        for stmt in stmts:
            for block in _blocks(stmt):
                rewrite(block)
            value = None
            if isinstance(stmt, (VarDeclNode, ConstDeclNode)) and unused(stmt.sym):
                value = stmt.value
            elif (isinstance(stmt, AssignNode) and isinstance(stmt.target, IdentifierNode)
                  and unused(stmt.target.sym)):
                value = stmt.value
            if value is None:
                out.append(stmt)
            elif not _has_effect(value):
                changed = True                      # dropped entirely
            elif _is_call(value):
                out.append(CallStmtNode(value, stmt.line, stmt.col))
                changed = True                      # the call stays, the name goes
            else:
                out.append(stmt)                    # a call deep inside: keep it all
        stmts[:] = out

    rewrite(program.stmts)
    return changed


# ═══════════════════════════════════════════════════════════════════════════════
#  Unused functions
# ═══════════════════════════════════════════════════════════════════════════════

def _calls_in(stmts) -> list[CallNode]:
    return [e for e in _all_exprs(stmts)
            if isinstance(e, CallNode) and e.func.owner is None]


def _remove_unused_functions(program: ProgramNode) -> bool:
    """A function is used if a call to it stands anywhere outside its own body."""
    callers: dict[str, int] = {}
    for item in program.stmts:
        own = item.name if isinstance(item, FuncDeclNode) else None
        body = [item] if not isinstance(item, FuncDeclNode) else item.body
        for call in _calls_in(body):
            if call.name != own:
                callers[call.name] = callers.get(call.name, 0) + 1
    before = len(program.stmts)
    program.stmts[:] = [item for item in program.stmts
                        if not isinstance(item, FuncDeclNode) or callers.get(item.name)]
    return len(program.stmts) != before


# ═══════════════════════════════════════════════════════════════════════════════
#  Inlining
# ═══════════════════════════════════════════════════════════════════════════════

def _inline_one_call(program: ProgramNode) -> bool:
    funcs = {item.name: item for item in program.stmts if isinstance(item, FuncDeclNode)}

    # Every call site: (call, statement, list holding it, enclosing structure).
    sites: dict[str, list] = {}
    for item in program.stmts:
        struct = item if isinstance(item, StructDeclNode) else None
        for stmt, holder in _walk_stmts([item]):
            if stmt is item:
                holder = program.stmts
            for e in _exprs(stmt):
                for x in _walk_expr(e):
                    if isinstance(x, CallNode) and x.func.owner is None:
                        sites.setdefault(x.name, []).append((x, stmt, holder, struct))

    graph = {name: {c.name for c in _calls_in(f.body)} for name, f in funcs.items()}
    names = _all_names(program)

    for name, func in funcs.items():
        if len(sites.get(name, [])) != 1 or _recursive(name, graph):
            continue
        call, stmt, holder, struct = sites[name][0]
        if _can_inline(func, call, stmt, struct):
            _inline(func, call, stmt, holder, names)
            return True
    return False


def _recursive(name: str, graph: dict) -> bool:
    seen, todo = set(), list(graph.get(name, ()))
    while todo:
        f = todo.pop()
        if f == name:
            return True
        if f not in seen:
            seen.add(f)
            todo.extend(graph.get(f, ()))
    return False


def _can_inline(func: FuncDeclNode, call: CallNode, stmt, struct) -> bool:
    body = func.body
    # Shape: one 🏁, the last statement of the body.
    if not isinstance(body[-1], ReturnNode):
        return False
    if any(isinstance(s, ReturnNode) for s, _ in _walk_stmts(body[:-1])):
        return False
    # Globals cannot be renamed, and the call site may not see the same one.
    for x in _all_exprs(body):
        if isinstance(x, IdentifierNode) and getattr(x.sym, "kind", None) == "global":
            return False
    # Inside a structure a bare call names a member function first.
    if struct is not None:
        members = {m.name for m in struct.members}
        if any(c.name in members for c in _calls_in(body)):
            return False
    # The body runs before the statement; that keeps the order of effects
    # only when the call is evaluated first and always.
    if not isinstance(stmt, (VarDeclNode, ConstDeclNode, AssignNode, IfNode, PrintNode,
                             ReturnNode, CallStmtNode, OverflowCheckNode)):
        return False
    path = None
    for e in _exprs(stmt):
        path = path or _path_to(e, call)
    ancestors = {id(x) for x in path}
    for i, x in enumerate(path[:-1]):
        if isinstance(x, BinaryOpNode) and x.op in ("AND", "OR") and path[i + 1] is x.right:
            return False                    # may never run
    inside = {id(x) for x in _walk_expr(call)}
    for e in _exprs(stmt):
        for x in _walk_expr(e):
            if id(x) in inside or id(x) in ancestors:
                continue
            if isinstance(x, (CallNode, MemberCallStep, ReadNode)):
                return False                # another effect in the statement
    return True


def _path_to(e, target):
    if e is target:
        return [e]
    for c in _children(e):
        p = _path_to(c, target)
        if p:
            return [e] + p
    return None


def _all_names(program: ProgramNode) -> set[str]:
    names = set()
    for stmt, _ in _walk_stmts(program.stmts):
        names.add(getattr(stmt, "name", None))
        if isinstance(stmt, FuncDeclNode):
            names.update(p.name for p in stmt.params)
        if isinstance(stmt, StructDeclNode):
            names.update(f.name for f in stmt.fields)
    for x in _all_exprs(program.stmts):
        if isinstance(x, IdentifierNode):
            names.add(x.name)
    return names


def _fresh(base: str, names: set[str]) -> str:
    k = 1
    while f"{base}_{k}" in names:
        k += 1
    names.add(f"{base}_{k}")
    return f"{base}_{k}"


def _inline(func: FuncDeclNode, call: CallNode, stmt, holder: list, names: set[str]):
    """Parameters become constants initialised with the arguments, the body
    follows, and the value of its 🏁 becomes a constant that stands where
    the call stood.  Every name of the body gets a fresh one."""
    body = _clone(func.body)
    rename: dict[int, str] = {}
    for p in func.params:
        rename[id(p.sym)] = _fresh(f"{func.name}_{p.name}", names)
    for s, _ in _walk_stmts(body):
        if isinstance(s, (VarDeclNode, ConstDeclNode, ForNode)):
            rename[id(s.sym)] = _fresh(f"{func.name}_{s.name}", names)
            s.name = rename[id(s.sym)]
    for x in _all_exprs(body):
        if isinstance(x, IdentifierNode) and id(x.sym) in rename:
            x.name = rename[id(x.sym)]

    line, col = call.line, call.col
    new = [ConstDeclNode(rename[id(p.sym)], p.type_name, arg, line, col)
           for p, arg in zip(func.params, call.args)]
    new += body[:-1]
    result = _fresh(f"{func.name}_result", names)
    new.append(ConstDeclNode(result, func.result, body[-1].value, line, col))

    index = next(i for i, s in enumerate(holder) if s is stmt)
    if isinstance(stmt, CallStmtNode) and stmt.call is call:
        holder[index:index + 1] = new       # the value was discarded anyway
    else:
        _replace(stmt, call, IdentifierNode(result, line, col))
        holder[index:index] = new
