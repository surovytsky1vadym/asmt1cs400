"""Recursive-descent parser: one method per grammar rule (see grammar.ebnf)."""

from __future__ import annotations

from .errors import error_at
from .lexer import Token, TokenKind, describe_kind
from .nodes import (
    ProgramNode, StmtNode, VarDeclNode, ConstDeclNode, AssignNode, IfNode,
    PrintNode, OverflowCheckNode, ExprNode, IntLiteralNode, BoolLiteralNode,
    IdentifierNode, BinaryOpNode, UnaryOpNode,
)


class Parser:
    """Recursive-descent parser: peek/eat over the token stream."""

    def __init__(self, tokens: list[Token]):
        self._tokens = tokens
        self._pos    = 0

    # ── helpers ─────────────────────────────────────────────────────────

    def _peek(self) -> Token:
        return self._tokens[self._pos]

    def _eat(self, kind: TokenKind) -> Token:
        tok = self._peek()
        if tok.kind != kind:
            error_at(tok, f"expected {describe_kind(kind)}, got {tok.describe()}")
        self._pos += 1
        return tok

    def _at(self, kind: TokenKind) -> bool:
        return self._peek().kind == kind

    # ── program ─────────────────────────────────────────────────────────

    def parse(self) -> ProgramNode:
        stmts: list[StmtNode] = []
        first = self._peek()
        while not self._at(TokenKind.EOF):
            stmts.append(self._parse_statement())
        return ProgramNode(stmts, first.line, first.col)

    # ── statement ───────────────────────────────────────────────────────

    def _parse_statement(self) -> StmtNode:
        tok = self._peek()

        if tok.kind == TokenKind.KW_SPAWN:
            return self._parse_var_decl()
        if tok.kind == TokenKind.KW_FORGE:
            return self._parse_const_decl()
        if tok.kind == TokenKind.KW_QUEST:
            return self._parse_if()
        if tok.kind == TokenKind.KW_SHOUT:
            return self._parse_print()
        if tok.kind == TokenKind.KW_CLASH:
            return self._parse_overflow_check()
        if tok.kind == TokenKind.IDENTIFIER:
            return self._parse_assignment()

        error_at(tok, f"unexpected {tok.describe()} at start of statement")

    # ── variable declaration ────────────────────────────────────────────

    def _parse_var_decl(self) -> VarDeclNode:
        start = self._eat(TokenKind.KW_SPAWN)
        name_tok = self._eat(TokenKind.IDENTIFIER)
        self._eat(TokenKind.OP_TYPE_ANN)
        type_tok = self._parse_type_name()
        self._eat(TokenKind.OP_ASSIGN)
        value = self._parse_expr()
        self._eat(TokenKind.TERMINATOR)
        return VarDeclNode(name_tok.text, type_tok, value, start.line, start.col)

    # ── constant declaration ────────────────────────────────────────────

    def _parse_const_decl(self) -> ConstDeclNode:
        start = self._eat(TokenKind.KW_FORGE)
        name_tok = self._eat(TokenKind.IDENTIFIER)
        self._eat(TokenKind.OP_TYPE_ANN)
        type_tok = self._parse_type_name()
        self._eat(TokenKind.OP_ASSIGN)
        value = self._parse_expr()
        self._eat(TokenKind.TERMINATOR)
        return ConstDeclNode(name_tok.text, type_tok, value, start.line, start.col)

    # ── assignment ──────────────────────────────────────────────────────

    def _parse_assignment(self) -> AssignNode:
        name_tok = self._eat(TokenKind.IDENTIFIER)
        self._eat(TokenKind.OP_ASSIGN)
        value = self._parse_expr()
        self._eat(TokenKind.TERMINATOR)
        return AssignNode(name_tok.text, value, name_tok.line, name_tok.col)

    # ── if / else ───────────────────────────────────────────────────────

    def _parse_if(self) -> IfNode:
        start = self._eat(TokenKind.KW_QUEST)
        cond = self._parse_expr()

        # then block
        self._eat(TokenKind.ARENA)
        then_body = self._parse_stmt_block()
        self._eat(TokenKind.ARENA)

        # optional else
        else_body: list[StmtNode] | None = None
        if self._at(TokenKind.KW_HAUNT):
            self._eat(TokenKind.KW_HAUNT)
            self._eat(TokenKind.ARENA)
            else_body = self._parse_stmt_block()
            self._eat(TokenKind.ARENA)

        return IfNode(cond, then_body, else_body, start.line, start.col)

    def _parse_stmt_block(self) -> list[StmtNode]:
        """Parse one or more statements (the block must not be empty)."""
        stmts = [self._parse_statement()]
        while not self._at(TokenKind.ARENA) and not self._at(TokenKind.EOF):
            stmts.append(self._parse_statement())
        return stmts

    # ── print ───────────────────────────────────────────────────────────

    def _parse_print(self) -> PrintNode:
        start = self._eat(TokenKind.KW_SHOUT)
        expr = self._parse_expr()
        self._eat(TokenKind.TERMINATOR)
        return PrintNode(expr, start.line, start.col)

    # ── overflow check ──────────────────────────────────────────────────

    def _parse_overflow_check(self) -> OverflowCheckNode:
        start = self._eat(TokenKind.KW_CLASH)
        expr = self._parse_expr()
        self._eat(TokenKind.OP_TYPE_ANN)
        type_name = self._parse_type_name()
        self._eat(TokenKind.TERMINATOR)
        return OverflowCheckNode(expr, type_name, start.line, start.col)

    # ── type name ───────────────────────────────────────────────────────

    def _parse_type_name(self) -> str:
        tok = self._peek()
        if tok.kind == TokenKind.TYPE_I32:
            self._eat(TokenKind.TYPE_I32)
            return "i32"
        if tok.kind == TokenKind.TYPE_I64:
            self._eat(TokenKind.TYPE_I64)
            return "i64"
        if tok.kind == TokenKind.TYPE_BOOL:
            self._eat(TokenKind.TYPE_BOOL)
            return "bool"
        error_at(tok, f"expected a type (💎32, 💎64 or 🛡️), got {tok.describe()}")

    # ── expressions (precedence climbing) ───────────────────────────────

    def _parse_expr(self) -> ExprNode:
        return self._parse_or()

    def _parse_or(self) -> ExprNode:
        left = self._parse_and()
        while self._at(TokenKind.OP_OR):
            op_tok = self._eat(TokenKind.OP_OR)
            right = self._parse_and()
            left = BinaryOpNode("OR", left, right, op_tok.line, op_tok.col)
        return left

    def _parse_and(self) -> ExprNode:
        left = self._parse_equality()
        while self._at(TokenKind.OP_AND):
            op_tok = self._eat(TokenKind.OP_AND)
            right = self._parse_equality()
            left = BinaryOpNode("AND", left, right, op_tok.line, op_tok.col)
        return left

    def _parse_equality(self) -> ExprNode:
        left = self._parse_relational()
        if self._at(TokenKind.OP_EQ):
            op_tok = self._eat(TokenKind.OP_EQ)
            right = self._parse_relational()
            return BinaryOpNode("EQ", left, right, op_tok.line, op_tok.col)
        if self._at(TokenKind.OP_NEQ):
            op_tok = self._eat(TokenKind.OP_NEQ)
            right = self._parse_relational()
            return BinaryOpNode("NEQ", left, right, op_tok.line, op_tok.col)
        return left

    def _parse_relational(self) -> ExprNode:
        left = self._parse_additive()
        _REL = {
            TokenKind.OP_GT:  "GT",
            TokenKind.OP_LT:  "LT",
            TokenKind.OP_GTE: "GTE",
            TokenKind.OP_LTE: "LTE",
        }
        for kind, name in _REL.items():
            if self._at(kind):
                op_tok = self._eat(kind)
                right = self._parse_additive()
                return BinaryOpNode(name, left, right, op_tok.line, op_tok.col)
        return left

    def _parse_additive(self) -> ExprNode:
        left = self._parse_multiplicative()
        while self._at(TokenKind.OP_PLUS) or self._at(TokenKind.OP_MINUS):
            if self._at(TokenKind.OP_PLUS):
                op_tok = self._eat(TokenKind.OP_PLUS)
                right = self._parse_multiplicative()
                left = BinaryOpNode("PLUS", left, right, op_tok.line, op_tok.col)
            else:
                op_tok = self._eat(TokenKind.OP_MINUS)
                right = self._parse_multiplicative()
                left = BinaryOpNode("MINUS", left, right, op_tok.line, op_tok.col)
        return left

    def _parse_multiplicative(self) -> ExprNode:
        left = self._parse_unary()
        while (self._at(TokenKind.OP_MUL) or self._at(TokenKind.OP_DIV)
               or self._at(TokenKind.OP_MOD)):
            if self._at(TokenKind.OP_MUL):
                op_tok = self._eat(TokenKind.OP_MUL)
                right = self._parse_unary()
                left = BinaryOpNode("MUL", left, right, op_tok.line, op_tok.col)
            elif self._at(TokenKind.OP_DIV):
                op_tok = self._eat(TokenKind.OP_DIV)
                right = self._parse_unary()
                left = BinaryOpNode("DIV", left, right, op_tok.line, op_tok.col)
            else:
                op_tok = self._eat(TokenKind.OP_MOD)
                right = self._parse_unary()
                left = BinaryOpNode("MOD", left, right, op_tok.line, op_tok.col)
        return left

    def _parse_unary(self) -> ExprNode:
        if self._at(TokenKind.OP_MINUS):
            op_tok = self._eat(TokenKind.OP_MINUS)
            operand = self._parse_unary()
            return UnaryOpNode("NEG", operand, op_tok.line, op_tok.col)
        if self._at(TokenKind.OP_NOT):
            op_tok = self._eat(TokenKind.OP_NOT)
            operand = self._parse_unary()
            return UnaryOpNode("NOT", operand, op_tok.line, op_tok.col)
        return self._parse_primary()

    def _parse_primary(self) -> ExprNode:
        tok = self._peek()

        if tok.kind == TokenKind.INT_LITERAL:
            self._eat(TokenKind.INT_LITERAL)
            return IntLiteralNode(int(tok.text), tok.line, tok.col)

        if tok.kind == TokenKind.KW_VICTORY:
            self._eat(TokenKind.KW_VICTORY)
            return BoolLiteralNode(True, tok.line, tok.col)

        if tok.kind == TokenKind.KW_DEFEAT:
            self._eat(TokenKind.KW_DEFEAT)
            return BoolLiteralNode(False, tok.line, tok.col)

        if tok.kind == TokenKind.IDENTIFIER:
            self._eat(TokenKind.IDENTIFIER)
            return IdentifierNode(tok.text, tok.line, tok.col)

        if tok.kind == TokenKind.LPAREN:
            self._eat(TokenKind.LPAREN)
            expr = self._parse_expr()
            self._eat(TokenKind.RPAREN)
            return expr

        error_at(tok, f"expected an expression, got {tok.describe()}")
