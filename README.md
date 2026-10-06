# 🎮 KaguLang — A Gaming-Themed Emoji Programming Language

**KaguLang** is a programming language designed for the Compilers Design course (CS 400), where every keyword and operator is an emoji from the gaming world. Instead of boring text keywords, you _spawn_ variables, _forge_ constants, _quest_ through conditionals, and _shout_ output — all with emojis.

---

## 📋 Language Features

### Types

| Emoji | Type | Description |
|-------|------|-------------|
| `💎32` | `i32` | 32-bit signed integer (−2,147,483,648 to 2,147,483,647) |
| `💎64` | `i64` | 64-bit signed integer |
| `🛡️` | `bool` | Boolean type |

### Keywords

| Emoji | Name | Meaning |
|-------|------|---------|
| `🎮` | spawn | Declare a mutable variable |
| `🏰` | forge | Declare a constant (immutable variable) |
| `🐉` | quest | `if` statement |
| `👻` | haunt | `else` clause |
| `📢` | shout | Print / output |
| `💥` | clash | Type overflow check |
| `🏆` | victory | Boolean `true` |
| `💀` | defeat | Boolean `false` |

### Operators

| Emoji | Meaning |
|-------|---------|
| `🎯` | Assignment (`=`) |
| `🔫` | Type annotation (`:`) |
| `⚖️` | Equals (`==`) |
| `💢` | Not equals (`!=`) |
| `⬆️` | Greater than (`>`) |
| `⬇️` | Less than (`<`) |
| `⬆️⚖️` | Greater or equal (`>=`) |
| `⬇️⚖️` | Less or equal (`<=`) |
| `➕` | Addition (`+`) |
| `➖` | Subtraction / negation (`-`) |
| `✖️` | Multiplication (`*`) |
| `➗` | Division (`/`) |
| `🎲` | Modulo (`%`) |
| `👾` | Logical OR (`\|\|`) |
| `🤝` | Logical AND (`&&`) |
| `🚫` | Logical NOT (`!`) |

### Delimiters

| Emoji | Meaning |
|-------|---------|
| `🏟️` | Block delimiter (arena — replaces `{` and `}`) |
| `⚔️` | Statement terminator (replaces `;`) |
| `(` `)` | Parentheses for grouping expressions |

---

## 📝 Syntax Examples

### Mutable Variable Declaration

```
🎮 hp 🔫 💎32 🎯 100 ⚔️
```
> Spawns a mutable i32 variable `hp` with value 100.

### Constant (Immutable Variable) Declaration

```
🏰 MAX_SCORE 🔫 💎32 🎯 1000 ⚔️
```
> Forges an immutable i32 constant `MAX_SCORE` with value 1000.

### Boolean Variable

```
🎮 alive 🔫 🛡️ 🎯 🏆 ⚔️
🎮 dead 🔫 🛡️ 🎯 💀 ⚔️
```
> Declares boolean variables with `victory` (true) and `defeat` (false).

### Assignment

```
hp 🎯 50 ⚔️
```
> Assigns the value 50 to `hp`.

### Arithmetic Expressions

```
🎮 result 🔫 💎32 🎯 (10 ➕ 20) ✖️ 3 ⚔️
```
> Standard arithmetic with precedence; parentheses for grouping.

### Comparison Operators

```
🎮 is_max 🔫 🛡️ 🎯 score ⚖️ 100 ⚔️
🎮 not_zero 🔫 🛡️ 🎯 hp 💢 0 ⚔️
```
> Equality (`⚖️`) and inequality (`💢`).

### If / Else

```
🐉 hp ⬆️ 0 🏟️
  📢 hp ⚔️
🏟️ 👻 🏟️
  📢 0 ⚔️
🏟️
```
> Quest (if) checks if `hp > 0`; if true, shouts `hp`; otherwise (haunt/else) shouts 0.

### Overflow Check

```
💥 big_value 🔫 💎32 ⚔️
```
> Checks whether `big_value` fits in i32.

### Print

```
📢 42 ⚔️
📢 player_name ⚔️
```
> Shouts a value to the output.

### Comments

```
// This is a single-line comment
🎮 x 🔫 💎32 🎯 42 ⚔️  // inline comment
```

---

## 🚀 Building and Running

### Prerequisites

- **Python 3.6+** (tested with Python 3.9)
- No external dependencies required

### Running the Compiler

```bash
python3 compiler.py --ast <input_file>
```

The compiler reads the input file, tokenizes it with a hand-written state-machine lexer, parses it with a recursive-descent parser, and prints the AST to stdout.

#### Example

```bash
python3 compiler.py --ast tests/valid/complex_program.txt
```

Output:
```
Program
  ConstDecl(name=MAX_SCORE, type=i32, mutable=False)
    value:
      IntLiteral(1000)
  VarDecl(name=player_score, type=i32, mutable=True)
    value:
      IntLiteral(0)
  ...
```

#### Error Reporting

Errors are printed to stderr in the format:
```
compilation error: line L:C: message
```

The compiler exits with code 1 and produces no stdout output on error.

---

## 🧪 Running the Tests

```bash
bash run_tests.sh
```

The test runner:
1. Runs all **valid tests** (`tests/valid/*.txt`) and compares stdout against `.expected` files.
2. Runs all **invalid tests** (`tests/invalid/*.txt`) and compares stderr against `.expected` files.
3. Reports PASS/FAIL for each test and a summary at the end.

### Test Coverage

**20 valid tests** covering:
- Variable declarations (i32, i64, bool)
- Constant declarations
- Assignment
- If statements (simple, with else, nested)
- All comparison operators (==, !=, >, <, >=, <=)
- Arithmetic operators (+, −, ×, ÷, %)
- Logical operators (AND, OR, NOT)
- Unary negation
- Parenthesized expressions
- Print statements
- Overflow checks
- Complex multi-feature programs

**21 invalid tests** covering:
- Missing statement terminator
- Missing type annotation
- Missing assignment operator
- Missing identifier name
- Unclosed if blocks
- Empty if/else blocks
- Unexpected characters (lexer errors)
- Missing expressions
- Unclosed parentheses
- Missing conditions
- Invalid type names
- Double assignment operators
- Missing opening arena
- Else without if
- Missing assignment values
- Missing overflow check type
- Bare terminators
- Empty else blocks

---

## 📂 Project Structure

```
.
├── compiler.py          # Lexer + Parser + AST (main compiler)
├── grammar.ebnf         # Complete EBNF grammar
├── run_tests.sh         # Test runner script
├── ai_usage.txt         # AI usage disclosure
├── README.md            # This file
└── tests/
    ├── valid/           # Happy-path test cases
    │   ├── *.txt        # Input programs
    │   └── *.expected   # Expected AST dumps
    └── invalid/         # Error-scenario test cases
        ├── *.txt        # Input programs with errors
        └── *.expected   # Expected error messages
```

---

## 🔧 Implementation Details

### Lexer
- **Hand-written state machine** operating on raw UTF-8 bytes
- Emoji tokens are matched by comparing byte sequences (longest match first)
- Supports single-line comments (`//`)
- Every token carries: kind, text, line number, and column number
- Lexical errors report `line:column`

### Parser
- **Recursive descent** with `peek`/`eat` over the token stream
- One function per grammar rule
- Operator precedence handled by separate functions (OR < AND < equality < relational < additive < multiplicative < unary < primary)

### AST Node Hierarchy
- `ASTNode` — base class (holds line and column)
  - `ProgramNode` — root node, contains a list of statements
  - `StmtNode` — abstract base for statements
    - `VarDeclNode` — mutable variable declaration
    - `ConstDeclNode` — constant/immutable declaration
    - `AssignNode` — assignment
    - `IfNode` — if/else
    - `PrintNode` — print
    - `OverflowCheckNode` — overflow check
  - `ExprNode` — abstract base for expressions
    - `IntLiteralNode` — integer literal
    - `BoolLiteralNode` — boolean literal
    - `IdentifierNode` — variable reference
    - `BinaryOpNode` — binary operator
    - `UnaryOpNode` — unary operator
