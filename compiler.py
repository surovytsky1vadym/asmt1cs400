#!/usr/bin/env python3
from __future__ import annotations
"""
KaguLang Compiler — Stage 1: Lexer + Parser → AST
A gaming-themed emoji programming language.

Usage:
    python3 compiler.py --ast input.txt
"""

import sys
from enum import Enum, auto


# ═══════════════════════════════════════════════════════════════════════════════
#  Token kinds
# ═══════════════════════════════════════════════════════════════════════════════

class TokenKind(Enum):
    # ── Literals & identifiers ──
    INT_LITERAL  = auto()
    IDENTIFIER   = auto()

    # ── Keywords ──
    KW_SPAWN     = auto()   # 🎮  mutable variable declaration
    KW_FORGE     = auto()   # 🏰  constant / immutable variable declaration
    KW_QUEST     = auto()   # 🐉  if
    KW_HAUNT     = auto()   # 👻  else
    KW_SHOUT     = auto()   # 📢  print
    KW_CLASH     = auto()   # 💥  overflow check
    KW_VICTORY   = auto()   # 🏆  true
    KW_DEFEAT    = auto()   # 💀  false

    # ── Types ──
    TYPE_I32     = auto()   # 💎32
    TYPE_I64     = auto()   # 💎64
    TYPE_BOOL    = auto()   # 🛡️

    # ── Operators ──
    OP_ASSIGN    = auto()   # 🎯
    OP_TYPE_ANN  = auto()   # 🔫
    OP_EQ        = auto()   # ⚖️
    OP_NEQ       = auto()   # 💢
    OP_GT        = auto()   # ⬆️
    OP_LT        = auto()   # ⬇️
    OP_GTE       = auto()   # ⬆️⚖️
    OP_LTE       = auto()   # ⬇️⚖️
    OP_PLUS      = auto()   # ➕
    OP_MINUS     = auto()   # ➖
    OP_MUL       = auto()   # ✖️
    OP_DIV       = auto()   # ➗
    OP_MOD       = auto()   # 🎲
    OP_OR        = auto()   # 👾
    OP_AND       = auto()   # 🤝
    OP_NOT       = auto()   # 🚫

    # ── Delimiters ──
    ARENA        = auto()   # 🏟️  block delimiter
    TERMINATOR   = auto()   # ⚔️  statement terminator
    LPAREN       = auto()   # (
    RPAREN       = auto()   # )

    # ── Special ──
    EOF          = auto()
    ERROR        = auto()


# ═══════════════════════════════════════════════════════════════════════════════
#  Token
# ═══════════════════════════════════════════════════════════════════════════════

class Token:
    __slots__ = ("kind", "text", "line", "col")

    def __init__(self, kind: TokenKind, text: str, line: int, col: int):
        self.kind = kind
        self.text = text
        self.line = line
        self.col  = col

    def __repr__(self):
        return f"Token({self.kind.name}, {self.text!r}, {self.line}:{self.col})"


# ═══════════════════════════════════════════════════════════════════════════════
#  Lexer — hand-written state machine over bytes
# ═══════════════════════════════════════════════════════════════════════════════

# Emoji byte sequences (UTF-8 encoded)
_EMOJI_MAP: "list[tuple[bytes, TokenKind]]" = []

def _e(emoji: str, kind: TokenKind):
    """Register an emoji → token mapping."""
    _EMOJI_MAP.append((emoji.encode("utf-8"), kind))

# Register all emoji tokens (order matters: longer prefixes first for
# composite emojis like ⬆️⚖️ vs ⬆️)
_e("⬆️⚖️", TokenKind.OP_GTE)
_e("⬇️⚖️", TokenKind.OP_LTE)
_e("💎32",  TokenKind.TYPE_I32)
_e("💎64",  TokenKind.TYPE_I64)
_e("🛡️",   TokenKind.TYPE_BOOL)
_e("🎮",    TokenKind.KW_SPAWN)
_e("🏰",    TokenKind.KW_FORGE)
_e("🐉",    TokenKind.KW_QUEST)
_e("👻",    TokenKind.KW_HAUNT)
_e("📢",    TokenKind.KW_SHOUT)
_e("💥",    TokenKind.KW_CLASH)
_e("🏆",    TokenKind.KW_VICTORY)
_e("💀",    TokenKind.KW_DEFEAT)
_e("🎯",    TokenKind.OP_ASSIGN)
_e("🔫",    TokenKind.OP_TYPE_ANN)
_e("⚖️",    TokenKind.OP_EQ)
_e("💢",    TokenKind.OP_NEQ)
_e("⬆️",    TokenKind.OP_GT)
_e("⬇️",    TokenKind.OP_LT)
_e("➕",    TokenKind.OP_PLUS)
_e("➖",    TokenKind.OP_MINUS)
_e("✖️",    TokenKind.OP_MUL)
_e("➗",    TokenKind.OP_DIV)
_e("🎲",    TokenKind.OP_MOD)
_e("👾",    TokenKind.OP_OR)
_e("🤝",    TokenKind.OP_AND)
_e("🚫",    TokenKind.OP_NOT)
_e("🏟️",   TokenKind.ARENA)
_e("⚔️",    TokenKind.TERMINATOR)

# Sort by descending byte-length so longer sequences match first.
_EMOJI_MAP.sort(key=lambda pair: len(pair[0]), reverse=True)


class Lexer:
    """Hand-written state-machine lexer that operates on raw bytes."""

    def __init__(self, source: str, filename: str = "<stdin>"):
        self._data: bytes = source.encode("utf-8")
        self._pos: int = 0
        self._line: int = 1
        self._col: int = 1
        self._filename: str = filename
        self._tokens: list[Token] = []

    # ── public API ──────────────────────────────────────────────────────

    def tokenize(self) -> list[Token]:
        """Scan the entire source and return a list of tokens (including EOF)."""
        while True:
            tok = self._next_token()
            self._tokens.append(tok)
            if tok.kind == TokenKind.EOF:
                break
            if tok.kind == TokenKind.ERROR:
                _compilation_error(tok.line, tok.col, tok.text)
        return self._tokens

    # ── internal scanning ───────────────────────────────────────────────

    @staticmethod
    def _utf8_seq_len(lead: int) -> int:
        """Return the number of bytes in a UTF-8 sequence from its leading byte."""
        if lead < 0x80:
            return 1
        if lead < 0xC0:          # continuation byte (shouldn't be a lead)
            return 1
        if lead < 0xE0:
            return 2
        if lead < 0xF0:
            return 3
        return 4

    def _peek_byte(self) -> int | None:
        if self._pos < len(self._data):
            return self._data[self._pos]
        return None

    def _advance(self) -> int:
        """Advance one byte.  Column is incremented only for ASCII bytes and
        for UTF-8 *leading* bytes (not continuation bytes 10xxxxxx), so that
        the column number reflects visible characters, not raw bytes."""
        b = self._data[self._pos]
        self._pos += 1
        if b == ord("\n"):
            self._line += 1
            self._col = 1
        elif b < 0x80 or b >= 0xC0:
            # ASCII byte or UTF-8 leading byte → new visible character
            self._col += 1
        # else: continuation byte (10xxxxxx) → same visible character
        return b

    def _advance_codepoint(self) -> str:
        """Advance a full UTF-8 codepoint (1-4 bytes) and return it as a str."""
        lead = self._data[self._pos]
        length = self._utf8_seq_len(lead)
        raw = self._data[self._pos:self._pos + length]
        for _ in range(length):
            self._advance()
        return raw.decode("utf-8", errors="replace")

    def _skip_whitespace_and_comments(self):
        while self._pos < len(self._data):
            b = self._data[self._pos]
            # whitespace
            if b in (ord(" "), ord("\t"), ord("\r"), ord("\n")):
                self._advance()
                continue
            # single-line comment: // …
            if (b == ord("/") and self._pos + 1 < len(self._data)
                    and self._data[self._pos + 1] == ord("/")):
                self._advance()  # first /
                self._advance()  # second /
                while self._pos < len(self._data) and self._data[self._pos] != ord("\n"):
                    self._advance()
                continue
            break

    def _next_token(self) -> Token:
        self._skip_whitespace_and_comments()

        if self._pos >= len(self._data):
            return Token(TokenKind.EOF, "", self._line, self._col)

        start_line = self._line
        start_col  = self._col

        b = self._data[self._pos]

        # ── Try emoji matches (state machine over byte sequences) ───────
        for emoji_bytes, kind in _EMOJI_MAP:
            length = len(emoji_bytes)
            if self._data[self._pos:self._pos + length] == emoji_bytes:
                text = emoji_bytes.decode("utf-8")
                for _ in range(length):
                    self._advance()
                return Token(kind, text, start_line, start_col)

        # ── Parentheses ────────────────────────────────────────────────
        if b == ord("("):
            self._advance()
            return Token(TokenKind.LPAREN, "(", start_line, start_col)
        if b == ord(")"):
            self._advance()
            return Token(TokenKind.RPAREN, ")", start_line, start_col)

        # ── Integer literal ─────────────────────────────────────────────
        if b >= ord("0") and b <= ord("9"):
            return self._scan_integer(start_line, start_col)

        # ── Identifier (ASCII letters, digits, underscores) ─────────────
        if self._is_ident_start(b):
            return self._scan_identifier(start_line, start_col)

        # ── Unknown character → error ───────────────────────────────────
        # Consume the full codepoint (1-4 bytes) to avoid cascading errors
        # from orphan continuation bytes.
        ch = self._advance_codepoint()
        return Token(TokenKind.ERROR, f"unexpected character '{ch}'", start_line, start_col)

    def _scan_integer(self, line: int, col: int) -> Token:
        start = self._pos
        while self._pos < len(self._data) and ord("0") <= self._data[self._pos] <= ord("9"):
            self._advance()
        text = self._data[start:self._pos].decode("utf-8")
        return Token(TokenKind.INT_LITERAL, text, line, col)

    def _scan_identifier(self, line: int, col: int) -> Token:
        start = self._pos
        while self._pos < len(self._data) and self._is_ident_cont(self._data[self._pos]):
            self._advance()
        text = self._data[start:self._pos].decode("utf-8")
        return Token(TokenKind.IDENTIFIER, text, line, col)

    @staticmethod
    def _is_ident_start(b: int) -> bool:
        return (ord("a") <= b <= ord("z") or
                ord("A") <= b <= ord("Z") or
                b == ord("_"))

    @staticmethod
    def _is_ident_cont(b: int) -> bool:
        return (ord("a") <= b <= ord("z") or
                ord("A") <= b <= ord("Z") or
                ord("0") <= b <= ord("9") or
                b == ord("_"))


# ═══════════════════════════════════════════════════════════════════════════════
#  AST Node hierarchy
# ═══════════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════════
#  Parser — recursive descent
# ═══════════════════════════════════════════════════════════════════════════════

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
            _compilation_error(
                tok.line, tok.col,
                f"expected {kind.name}, got {tok.kind.name} ('{tok.text}')"
            )
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

        _compilation_error(
            tok.line, tok.col,
            f"unexpected token {tok.kind.name} ('{tok.text}') at start of statement"
        )

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
        _compilation_error(
            tok.line, tok.col,
            f"expected type name (💎32, 💎64 or 🛡️), got {tok.kind.name} ('{tok.text}')"
        )

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

        _compilation_error(
            tok.line, tok.col,
            f"expected expression, got {tok.kind.name} ('{tok.text}')"
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  Error reporting
# ═══════════════════════════════════════════════════════════════════════════════

def _compilation_error(line: int, col: int, message: str):
    """Print an error to stderr and exit with code 1."""
    print(f"compilation error: line {line}:{col}: {message}", file=sys.stderr)
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) != 3 or sys.argv[1] != "--ast":
        print("Usage: python3 compiler.py --ast <input_file>", file=sys.stderr)
        sys.exit(1)

    filename = sys.argv[2]
    try:
        with open(filename, "r", encoding="utf-8") as f:
            source = f.read()
    except FileNotFoundError:
        print(f"error: file not found: {filename}", file=sys.stderr)
        sys.exit(1)

    lexer  = Lexer(source, filename)
    tokens = lexer.tokenize()

    parser = Parser(tokens)
    ast    = parser.parse()

    print(ast.dump())


if __name__ == "__main__":
    main()
