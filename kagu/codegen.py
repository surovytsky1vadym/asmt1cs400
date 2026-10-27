"""LLVM IR generation through the llvmlite.ir builder.

Runs after semantic analysis and relies on its annotations (`.ty`, `.sym`,
`.func`, `.field`).  The only IR text produced is str(module).

Naming in the module:
    kagu.fn.<name>               function of the program
    kagu.member.<Struct>.<name>  member function; first parameter is the object
    kagu.struct.<Struct>         identified struct type
    kagu.global.<name>           top-level variable
    main                         the top-level statements
"""

from __future__ import annotations

from llvmlite import binding, ir

from .nodes import (
    VarDeclNode, ConstDeclNode, AssignNode, IfNode, PrintNode,
    OverflowCheckNode, ReturnNode, CallStmtNode, IntLiteralNode,
    BoolLiteralNode, IdentifierNode, BinaryOpNode, UnaryOpNode,
    StringLiteralNode, CallNode, NewNode, ReadNode, FieldStep, ChainNode,
)
from .semantic import Analyzer, StructInfo, FieldInfo, VarSymbol, I32, I64, BOOL, INT_RANGE


INT32 = ir.IntType(32)
INT64 = ir.IntType(64)
INT1  = ir.IntType(1)
INT8P = ir.IntType(8).as_pointer()

_CMP = {"EQ": "==", "NEQ": "!=", "GT": ">", "LT": "<", "GTE": ">=", "LTE": "<="}
_CHECKED = {"PLUS": "sadd", "MINUS": "ssub", "MUL": "smul"}


class CodeGen:
    def __init__(self, sem: Analyzer):
        self.sem = sem
        self.module = ir.Module(name="kagulang")
        self.module.triple = binding.get_process_triple()
        self.builder: ir.IRBuilder | None = None
        self.fn: ir.Function | None = None
        self.func = None                     # FuncInfo being generated; None in main
        self.self_ptr = None                 # object pointer inside a member function
        self._strings: dict[str, ir.GlobalVariable] = {}
        self._overflow_fns: dict[tuple[str, int], ir.Function] = {}

    # ═══════════════════════════════════════════════════════════════════════
    #  Module
    # ═══════════════════════════════════════════════════════════════════════

    def generate(self) -> str:
        self._declare_runtime()
        self._declare_structs()
        self._declare_functions()
        self._declare_globals()

        for func in self.sem.functions.values():
            self._gen_function(func)
        for member in self.sem.members:
            self._gen_function(member)
        self._gen_main()
        return str(self.module)

    def _declare_runtime(self):
        """C library functions, declared without a body; clang links them."""
        c_fmt = ir.FunctionType(INT32, [INT8P], var_arg=True)
        self.printf = ir.Function(self.module, c_fmt, name="printf")
        self.scanf  = ir.Function(self.module, c_fmt, name="scanf")
        self.dprintf = ir.Function(self.module,
                                   ir.FunctionType(INT32, [INT32, INT8P], var_arg=True),
                                   name="dprintf")
        self.exit = ir.Function(self.module, ir.FunctionType(ir.VoidType(), [INT32]),
                                name="exit")

        # kagu.rt.fail(line, col, message): report a runtime error and exit(1).
        fail_ty = ir.FunctionType(ir.VoidType(), [INT32, INT32, INT8P])
        self.fail = ir.Function(self.module, fail_ty, name="kagu.rt.fail")
        self.fail.attributes.add("noreturn")
        b = ir.IRBuilder(self.fail.append_basic_block("entry"))
        line, col, msg = self.fail.args
        b.call(self.dprintf, [ir.Constant(INT32, 2),
                              self._cstr("runtime error: line %d:%d: %s\n"),
                              line, col, msg])
        b.call(self.exit, [ir.Constant(INT32, 1)])
        b.unreachable()

    def _declare_structs(self):
        for info in self.sem.structs.values():
            info.ir_type = self.module.context.get_identified_type(f"kagu.struct.{info.name}")
        for info in self.sem.structs.values():
            info.ir_type.set_body(*[self._ir_type(f.ty) for f in info.fields])

    def _declare_functions(self):
        """Every function is declared before any body is generated, so a
        call to a function defined further down resolves."""
        for func in self.sem.functions.values():
            fn_ty = ir.FunctionType(self._ir_type(func.result),
                                    [self._ir_type(t) for t in func.params])
            func.ir = ir.Function(self.module, fn_ty, name=f"kagu.fn.{func.name}")
        for member in self.sem.members:
            params = [member.owner.ir_type.as_pointer()]
            params += [self._ir_type(t) for t in member.params]
            fn_ty = ir.FunctionType(self._ir_type(member.result), params)
            member.ir = ir.Function(self.module, fn_ty,
                                    name=f"kagu.member.{member.owner.name}.{member.name}")

    def _declare_globals(self):
        """Top-level variables are module globals so that function bodies can
        reach them; they start zeroed and are set when their declaration runs."""
        for sym in self.sem.globals:
            gv = ir.GlobalVariable(self.module, self._ir_type(sym.ty),
                                   name=f"kagu.global.{sym.name}")
            gv.initializer = ir.Constant(self._ir_type(sym.ty), None)
            gv.linkage = "internal"
            sym.ptr = gv

    @staticmethod
    def _ir_type(ty):
        if ty == I32:
            return INT32
        if ty == I64:
            return INT64
        if ty == BOOL:
            return INT1
        return ty.ir_type

    def _cstr(self, text: str):
        """An i8* to a private global holding `text` as a C string."""
        if text not in self._strings:
            data = bytearray(text.encode("utf-8") + b"\0")
            arr_ty = ir.ArrayType(ir.IntType(8), len(data))
            gv = ir.GlobalVariable(self.module, arr_ty, name=f"kagu.str.{len(self._strings)}")
            gv.initializer = ir.Constant(arr_ty, data)
            gv.global_constant = True
            gv.linkage = "private"
            gv.unnamed_addr = True
            self._strings[text] = gv
        zero = ir.Constant(INT32, 0)
        return self._strings[text].gep([zero, zero])

    # ═══════════════════════════════════════════════════════════════════════
    #  Functions
    # ═══════════════════════════════════════════════════════════════════════

    def _begin(self, fn: ir.Function):
        """Start a body.  The entry block holds only the stack slots; it
        jumps to the body block once the function is complete (_finish)."""
        self.fn = fn
        self.alloca_builder = ir.IRBuilder(fn.append_basic_block("entry"))
        self.body_bb = fn.append_basic_block("body")
        self.builder = ir.IRBuilder(self.body_bb)

    def _finish(self):
        self.alloca_builder.branch(self.body_bb)

    def _alloca(self, ty, name: str = ""):
        """Stack slot in the entry block, so every slot exists once per call."""
        return self.alloca_builder.alloca(ty, name=name)

    def _gen_function(self, func):
        self._begin(func.ir)
        self.func = func
        args = list(func.ir.args)
        self.self_ptr = args.pop(0) if func.owner is not None else None
        if self.self_ptr is not None:
            self.self_ptr.name = "self"
        for pnode, arg in zip(func.decl.params, args):
            arg.name = pnode.name
            slot = self._alloca(arg.type, pnode.name)
            self.builder.store(arg, slot)
            pnode.sym.ptr = slot
        self._gen_block(func.decl.body)
        if not self.builder.block.is_terminated:
            self.builder.unreachable()      # semantic pass: every path returns
        self._finish()

    def _gen_main(self):
        main = ir.Function(self.module, ir.FunctionType(INT32, []), name="main")
        self._begin(main)
        self.func = None
        self.self_ptr = None
        self._gen_block(self.sem.main_body)
        if not self.builder.block.is_terminated:
            self.builder.ret(ir.Constant(INT32, 0))
        self._finish()

    # ═══════════════════════════════════════════════════════════════════════
    #  Statements
    # ═══════════════════════════════════════════════════════════════════════

    def _gen_block(self, stmts):
        for stmt in stmts:
            self._gen_stmt(stmt)

    def _gen_stmt(self, stmt):
        b = self.builder
        if isinstance(stmt, (VarDeclNode, ConstDeclNode)):
            sym: VarSymbol = stmt.sym
            if sym.ptr is None:
                sym.ptr = self._alloca(self._ir_type(sym.ty), sym.name)
            b.store(self._gen_value(stmt.value, sym.ty), sym.ptr)
        elif isinstance(stmt, AssignNode):
            value = self._gen_value(stmt.value, stmt.target.ty)
            b.store(value, self._address(stmt.target))
        elif isinstance(stmt, IfNode):
            self._gen_if(stmt)
        elif isinstance(stmt, PrintNode):
            for item in stmt.items:
                self._print_item(item)
            b.call(self.printf, [self._cstr("\n")])
        elif isinstance(stmt, OverflowCheckNode):
            self._gen_overflow_check(stmt)
        elif isinstance(stmt, ReturnNode):
            b.ret(self._gen_value(stmt.value, self.func.result))
        elif isinstance(stmt, CallStmtNode):
            self._gen_expr(stmt.call)

    def _gen_if(self, stmt: IfNode):
        b = self.builder
        cond = self._gen_expr(stmt.condition)
        then_bb = self.fn.append_basic_block("if.then")
        else_bb = self.fn.append_basic_block("if.else") if stmt.else_body else None
        end_bb = self.fn.append_basic_block("if.end")
        b.cbranch(cond, then_bb, else_bb or end_bb)

        b.position_at_end(then_bb)
        self._gen_block(stmt.then_body)
        if not b.block.is_terminated:
            b.branch(end_bb)

        if else_bb is not None:
            b.position_at_end(else_bb)
            self._gen_block(stmt.else_body)
            if not b.block.is_terminated:
                b.branch(end_bb)

        b.position_at_end(end_bb)
        if getattr(stmt, "always_returns", False):
            b.unreachable()                 # both branches returned

    def _gen_overflow_check(self, stmt: OverflowCheckNode):
        value = self._gen_expr(stmt.expr)
        if stmt.expr.ty == stmt.type_name or stmt.type_name == I64:
            return                          # always fits: nothing to check at run time
        lo, hi = INT_RANGE[stmt.type_name]
        b = self.builder
        too_low = b.icmp_signed("<", value, ir.Constant(value.type, lo))
        too_high = b.icmp_signed(">", value, ir.Constant(value.type, hi))
        self._fail_if(b.or_(too_low, too_high), stmt,
                      f"value does not fit in {stmt.type_name}")

    def _fail_if(self, cond, node, message: str):
        """Branch to a runtime error when `cond` holds."""
        fail_bb = self.fn.append_basic_block("fail")
        ok_bb = self.fn.append_basic_block("ok")
        self.builder.cbranch(cond, fail_bb, ok_bb)
        self.builder.position_at_end(fail_bb)
        self.builder.call(self.fail, [ir.Constant(INT32, node.line),
                                      ir.Constant(INT32, node.col),
                                      self._cstr(message)])
        self.builder.unreachable()
        self.builder.position_at_end(ok_bb)

    # ── print ───────────────────────────────────────────────────────────

    def _print_item(self, item):
        if isinstance(item, StringLiteralNode):
            self.builder.call(self.printf, [self._cstr("%s"), self._cstr(item.value)])
        elif isinstance(item.ty, StructInfo):
            self._print_struct(self._address_or_temp(item), item.ty)
        else:
            self._print_scalar(self._gen_expr(item), item.ty, "")

    def _print_scalar(self, value, ty, prefix: str):
        if ty == I32:
            fmt = prefix + "%d"
        elif ty == I64:
            fmt = prefix + "%lld"
        else:
            value = self.builder.select(value, self._cstr("true"), self._cstr("false"))
            fmt = prefix + "%s"
        self.builder.call(self.printf, [self._cstr(fmt), value])

    def _print_struct(self, ptr, info: StructInfo):
        """Walk the field table: one gep, load and printf per field.
        Output: Name(field: value, field: value)."""
        b = self.builder
        b.call(self.printf, [self._cstr(f"{info.name}(")])
        for field in info.fields:
            prefix = (", " if field.index else "") + f"{field.name}: "
            field_ptr = self._field_ptr(ptr, field)
            if isinstance(field.ty, StructInfo):
                b.call(self.printf, [self._cstr(prefix)])
                self._print_struct(field_ptr, field.ty)
            else:
                self._print_scalar(b.load(field_ptr), field.ty, prefix)
        b.call(self.printf, [self._cstr(")")])

    # ═══════════════════════════════════════════════════════════════════════
    #  Addresses
    # ═══════════════════════════════════════════════════════════════════════

    def _field_ptr(self, obj_ptr, field: FieldInfo):
        """gep by the field's index from the symbol table, not by its name."""
        return self.builder.gep(obj_ptr, [ir.Constant(INT32, 0),
                                          ir.Constant(INT32, field.index)],
                                inbounds=True, name=field.name)

    def _address(self, e):
        """Address of a variable, a field of `self`, or a field chain."""
        if isinstance(e, IdentifierNode):
            if isinstance(e.sym, FieldInfo):
                return self._field_ptr(self.self_ptr, e.sym)
            return e.sym.ptr
        kind, ptr = self._gen_chain(e)
        assert kind == "ptr"
        return ptr

    def _address_or_temp(self, e):
        """Address of a structure value; a temporary is stored to a fresh slot."""
        if isinstance(e, IdentifierNode):
            return self._address(e)
        if isinstance(e, ChainNode):
            kind, x = self._gen_chain(e)
            return x if kind == "ptr" else self._temp(x)
        return self._temp(self._gen_expr(e))

    def _temp(self, value):
        slot = self._alloca(value.type, "tmp")
        self.builder.store(value, slot)
        return slot

    def _gen_chain(self, e: ChainNode):
        """Walk a chain.  Returns ("ptr", address) when it ends in a field,
        ("val", value) when it ends in a member call."""
        b = self.builder
        ptr = self._address_or_temp(e.base)
        value = None
        for step in e.steps:
            if value is not None:
                ptr, value = self._temp(value), None
            if isinstance(step, FieldStep):
                ptr = self._field_ptr(ptr, step.field)
            else:
                args = [ptr] + self._gen_args(step.args, step.func.params)
                value = b.call(step.func.ir, args)
        return ("ptr", ptr) if value is None else ("val", value)

    # ═══════════════════════════════════════════════════════════════════════
    #  Expressions
    # ═══════════════════════════════════════════════════════════════════════

    def _gen_value(self, e, target_ty):
        """Evaluate `e` and widen it to `target_ty` (i32 → i64) if needed."""
        return self._widen(self._gen_expr(e), e.ty, target_ty)

    def _widen(self, value, src, dst):
        if src == I32 and dst == I64:
            return self.builder.sext(value, INT64)
        return value

    def _gen_args(self, args, param_types):
        return [self._gen_value(a, t) for a, t in zip(args, param_types)]

    def _gen_expr(self, e):
        b = self.builder
        if isinstance(e, IntLiteralNode):
            return ir.Constant(self._ir_type(e.ty), e.value)
        if isinstance(e, BoolLiteralNode):
            return ir.Constant(INT1, int(e.value))
        if isinstance(e, IdentifierNode):
            return b.load(self._address(e), name=e.name)
        if isinstance(e, BinaryOpNode):
            return self._gen_binary(e)
        if isinstance(e, UnaryOpNode):
            return self._gen_unary(e)
        if isinstance(e, CallNode):
            args = self._gen_args(e.args, e.func.params)
            if e.on_self:
                args.insert(0, self.self_ptr)
            return b.call(e.func.ir, args)
        if isinstance(e, NewNode):
            obj = self._alloca(e.ty.ir_type, "new")
            for arg, field in zip(e.args, e.ty.fields):
                b.store(self._gen_value(arg, field.ty), self._field_ptr(obj, field))
            return b.load(obj)
        if isinstance(e, ReadNode):
            slot = self._alloca(INT32, "read")
            b.store(ir.Constant(INT32, 0), slot)
            b.call(self.scanf, [self._cstr("%d"), slot])
            return b.load(slot)
        if isinstance(e, ChainNode):
            kind, x = self._gen_chain(e)
            return b.load(x) if kind == "ptr" else x
        raise AssertionError(f"cannot generate {type(e).__name__}")

    def _gen_binary(self, e: BinaryOpNode):
        b = self.builder
        if e.op in ("AND", "OR"):
            return self._gen_logical(e)

        lhs = self._gen_value(e.left, e.operand_ty)
        rhs = self._gen_value(e.right, e.operand_ty)
        if e.op in _CMP:
            return b.icmp_signed(_CMP[e.op], lhs, rhs)
        if e.op in _CHECKED:
            return self._checked(_CHECKED[e.op], lhs, rhs, e)

        # DIV / MOD: division by zero and MIN / -1 are runtime errors.
        self._fail_if(b.icmp_signed("==", rhs, ir.Constant(rhs.type, 0)), e,
                      "division by zero")
        lo = INT_RANGE[e.operand_ty][0]
        is_min = b.icmp_signed("==", lhs, ir.Constant(lhs.type, lo))
        is_neg1 = b.icmp_signed("==", rhs, ir.Constant(rhs.type, -1))
        self._fail_if(b.and_(is_min, is_neg1), e, "integer overflow")
        return b.sdiv(lhs, rhs) if e.op == "DIV" else b.srem(lhs, rhs)

    def _checked(self, op: str, lhs, rhs, node):
        """lhs <op> rhs through llvm.<op>.with.overflow; overflow is a runtime error."""
        width = lhs.type.width
        key = (op, width)
        if key not in self._overflow_fns:
            res_ty = ir.LiteralStructType([lhs.type, INT1])
            fn_ty = ir.FunctionType(res_ty, [lhs.type, lhs.type])
            self._overflow_fns[key] = ir.Function(
                self.module, fn_ty, name=f"llvm.{op}.with.overflow.i{width}")
        pair = self.builder.call(self._overflow_fns[key], [lhs, rhs])
        self._fail_if(self.builder.extract_value(pair, 1), node, "integer overflow")
        return self.builder.extract_value(pair, 0)

    def _gen_logical(self, e: BinaryOpNode):
        """Short-circuit && and ||: the right side runs only when needed."""
        b = self.builder
        lhs = self._gen_expr(e.left)
        lhs_bb = b.block
        rhs_bb = self.fn.append_basic_block("logic.rhs")
        end_bb = self.fn.append_basic_block("logic.end")
        if e.op == "AND":
            b.cbranch(lhs, rhs_bb, end_bb)
        else:
            b.cbranch(lhs, end_bb, rhs_bb)
        b.position_at_end(rhs_bb)
        rhs = self._gen_expr(e.right)
        rhs_end = b.block
        b.branch(end_bb)
        b.position_at_end(end_bb)
        phi = b.phi(INT1)
        phi.add_incoming(ir.Constant(INT1, int(e.op == "OR")), lhs_bb)
        phi.add_incoming(rhs, rhs_end)
        return phi

    def _gen_unary(self, e: UnaryOpNode):
        if hasattr(e, "folded"):
            return ir.Constant(self._ir_type(e.ty), e.folded)
        value = self._gen_expr(e.operand)
        if e.op == "NOT":
            return self.builder.not_(value)
        return self._checked("ssub", ir.Constant(value.type, 0), value, e)
