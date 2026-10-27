"""Hand-written state-machine lexer over the raw UTF-8 bytes of the source."""

from __future__ import annotations

from enum import Enum, auto

from .errors import CompileError


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

    def describe(self) -> str:
        """How the token is named in an error message."""
        if self.kind == TokenKind.EOF:
            return "end of file"
        if self.kind == TokenKind.IDENTIFIER:
            return f"identifier '{self.text}'"
        if self.kind == TokenKind.INT_LITERAL:
            return f"integer {self.text}"
        return f"'{self.text}'"

    def __repr__(self):
        return f"Token({self.kind.name}, {self.text!r}, {self.line}:{self.col})"


# ═══════════════════════════════════════════════════════════════════════════════
#  Emoji / symbol table
# ═══════════════════════════════════════════════════════════════════════════════

# Emoji byte sequences (UTF-8 encoded)
_EMOJI_MAP: "list[tuple[bytes, TokenKind]]" = []

# Source spelling of every fixed token, used in error messages.
_SPELLING: "dict[TokenKind, str]" = {
    TokenKind.LPAREN: "(",
    TokenKind.RPAREN: ")",
}


def _e(emoji: str, kind: TokenKind):
    """Register an emoji → token mapping."""
    _EMOJI_MAP.append((emoji.encode("utf-8"), kind))
    _SPELLING[kind] = emoji


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


def describe_kind(kind: TokenKind) -> str:
    """How an expected token kind is named in an error message."""
    if kind == TokenKind.IDENTIFIER:
        return "an identifier"
    if kind == TokenKind.INT_LITERAL:
        return "an integer"
    if kind == TokenKind.EOF:
        return "end of file"
    return f"'{_SPELLING[kind]}'"


# ═══════════════════════════════════════════════════════════════════════════════
#  Lexer — hand-written state machine over bytes
# ═══════════════════════════════════════════════════════════════════════════════

class Lexer:
    """Hand-written state-machine lexer that operates on raw bytes."""

    def __init__(self, data: bytes):
        self._data: bytes = data
        self._pos: int = 0
        self._line: int = 1
        self._col: int = 1
        self._tokens: list[Token] = []

    # ── public API ──────────────────────────────────────────────────────

    def tokenize(self) -> list[Token]:
        """Scan the entire source and return a list of tokens (including EOF)."""
        self._check_utf8()
        while True:
            tok = self._next_token()
            self._tokens.append(tok)
            if tok.kind == TokenKind.EOF:
                break
        return self._tokens

    # ── internal scanning ───────────────────────────────────────────────

    def _check_utf8(self):
        """Reject a source that is not valid UTF-8, at the offending byte."""
        try:
            self._data.decode("utf-8")
        except UnicodeDecodeError as exc:
            before = self._data[:exc.start]
            line = before.count(b"\n") + 1
            line_start = before.rfind(b"\n") + 1
            col = len(before[line_start:].decode("utf-8")) + 1
            bad = self._data[exc.start]
            raise CompileError(line, col, f"invalid UTF-8 byte 0x{bad:02x}")

    @staticmethod
    def _utf8_seq_len(lead: int) -> int:
        """Return the number of bytes in a UTF-8 sequence from its leading byte."""
        if lead < 0x80:
            return 1
        if lead < 0xE0:
            return 2
        if lead < 0xF0:
            return 3
        return 4

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
        return raw.decode("utf-8")

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
        ch = self._advance_codepoint()
        raise CompileError(start_line, start_col, f"unexpected character '{ch}'")

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
