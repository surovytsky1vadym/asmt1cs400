# 🎮 KaguLang — A Gaming-Themed Emoji Programming Language

**KaguLang** is a programming language designed for the Compilers Design course (CS 400), where every keyword and operator is an emoji from the gaming world. Instead of boring text keywords, you _spawn_ variables, _forge_ constants, _quest_ through conditionals, _cast spells_ (functions), pack _crates_ (structures) and _shout_ output — all with emojis.

The compiler turns a KaguLang program into LLVM IR through the `llvmlite` builder; `clang` builds it into a native program.

---

## 📋 Language Features

### Types

| Emoji | Type | Description |
|-------|------|-------------|
| `💎32` | `i32` | 32-bit signed integer (−2,147,483,648 to 2,147,483,647) |
| `💎64` | `i64` | 64-bit signed integer |
| `🛡️` | `bool` | Boolean type |
| `Name` | structure | Any structure declared with `📦 Name` |

### Keywords

| Emoji | Name | Meaning |
|-------|------|---------|
| `🎮` | spawn | Declare a mutable variable / mutable field |
| `🏰` | forge | Declare a constant / constant field |
| `🐉` | quest | `if` statement |
| `👻` | haunt | `else` clause |
| `📢` | shout | Print |
| `💥` | clash | Type overflow check |
| `🏆` | victory | Boolean `true` |
| `💀` | defeat | Boolean `false` |
| `🪄` | spell | Function / member function declaration |
| `🏁` | finish | Return: leave the function with a value |
| `📦` | crate | Structure declaration |
| `🆕` | new | Create an object |
| `📥` | read | Read one integer from standard input |

### Operators

| Emoji | Meaning |
|-------|---------|
| `🎯` | Assignment (`=`) |
| `🔫` | Type annotation (`:`) |
| `➡️` | Result type of a function (`->`) |
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
| `👾` | Logical OR (`\|\|`), short-circuit |
| `🤝` | Logical AND (`&&`), short-circuit |
| `🚫` | Logical NOT (`!`) |

### Delimiters

| Symbol | Meaning |
|-------|---------|
| `🏟️` | Block delimiter (arena — replaces `{` and `}`) |
| `⚔️` | Statement terminator (replaces `;`) |
| `(` `)` | Grouping, parameter lists, call arguments |
| `,` | Separates parameters, arguments and print items |
| `.` | Field access / member call |
| `"…"` | String literal (only in `📢`; escapes `\n \t \" \\`) |

The full grammar, with the lexical rules, is in [`grammar.ebnf`](grammar.ebnf).

---

## 📝 Syntax Examples

### Variables and Constants

```
🎮 hp 🔫 💎32 🎯 100 ⚔️          // mutable i32
🏰 MAX_SCORE 🔫 💎64 🎯 1000 ⚔️  // constant i64
🎮 alive 🔫 🛡️ 🎯 🏆 ⚔️          // bool
hp 🎯 hp ➖ 10 ⚔️                // assignment
```

### Expressions

```
🎮 result 🔫 💎32 🎯 (10 ➕ 20) ✖️ 3 ⚔️
🎮 ok 🔫 🛡️ 🎯 hp ⬆️ 0 🤝 🚫(hp ⚖️ 100) ⚔️
```

### If / Else

```
🐉 hp ⬆️ 0 🏟️
  📢 hp ⚔️
🏟️ 👻 🏟️
  📢 "game over" ⚔️
🏟️
```

### Overflow Check

```
💥 big_value 🔫 💎32 ⚔️
```
> Stops the program with a runtime error if `big_value` does not fit in i32.

### Functions

```
🪄 add(a 🔫 💎32, b 🔫 💎64) ➡️ 💎64 🏟️
  🏁 a ➕ b ⚔️
🏟️

📢 add(1, add(2, 3)) ⚔️          // a call is an expression; calls nest
```
> `🪄 name(params) ➡️ resultType 🏟️ body 🏟️`. `🏁 expr ⚔️` leaves the function with a value.

**There are no void functions.** Every function and member function declares a result type after `➡️` and must leave with `🏁` on every path. A function that is called only for its effect still returns a value (for example the new value of the field it changed); the call can be used as a statement and the value is then discarded:

```
p.shift(1) ⚔️                    // result of shift is ignored
```

### Structures

```
📦 Point 🏟️
  🏰 x 🔫 💎32 ⚔️                 // constant field
  🎮 y 🔫 💎32 ⚔️                 // mutable field
🏟️

🎮 p 🔫 Point 🎯 🆕 Point(3, 4) ⚔️   // one value per field, in declaration order
p.y 🎯 p.x ➕ p.y ⚔️                 // field access and assignment
```

### Chains

```
📦 Circle 🏟️
  🎮 center 🔫 Point ⚔️
  🏰 r 🔫 💎32 ⚔️
🏟️

🎮 c 🔫 Circle 🎯 🆕 Circle(🆕 Point(1, 2), 5) ⚔️
c.center.y 🎯 10 ⚔️              // mutable at every step: c, center, y
```

### Member Functions

```
📦 Point 🏟️
  🏰 x 🔫 💎32 ⚔️
  🎮 y 🔫 💎32 ⚔️

  🪄 d2() ➡️ 💎32 🏟️              // fields are visible by name
    🏁 x ✖️ x ➕ y ✖️ y ⚔️
  🏟️

  🪄 shift(dy 🔫 💎32) ➡️ 💎32 🏟️ // assigns a field → mutating
    y 🎯 y ➕ dy ⚔️
    🏁 d2() ⚔️                    // other members are callable by name
  🏟️
🏟️

📢 p.d2() ⚔️
p.shift(1) ⚔️                    // allowed only because p is 🎮
```

### Read and Print

```
🎮 n 🔫 💎32 🎯 📥() ⚔️           // read one integer from stdin
📢 "n = ", n, ", alive = ", 🏆 ⚔️  // n = 7, alive = true
📢 p ⚔️                           // Point(x: 3, y: 5)
```

### Comments

```
// This is a single-line comment
🎮 x 🔫 💎32 🎯 42 ⚔️  // inline comment
```

---

## 📏 Semantic Rules

The semantic pass (`kagu/semantic.py`) runs over the whole AST before any code is generated. The first rule that is broken is reported as `compilation error: line L:C: message`. Each rule below names a program that follows it (`tests/run/` or `tests/valid/`) and one that breaks it (`tests/invalid/`).

### Names and scopes

| # | Rule | Follows | Breaks |
|---|------|---------|--------|
| 1 | A variable must be declared before it is used: a name is visible from the statement after its declaration. | `run/read_sum` | `undeclared_variable` |
| 2 | A scope is the top level, a function body (together with its parameters), or one `🐉` / `👻` block. A name can be declared only once per scope. An inner block may declare a name that already exists outside; the inner declaration hides the outer one until the block ends. | `run/scopes_shadowing` | `redeclared_variable` |
| 3 | Inside a function, a name is looked up among the parameters and locals (innermost block first), then the globals declared **above** the function. Top-level variables declared below a function are not visible in it. | `run/globals` | `global_declared_below` |
| 4 | Inside a member function, a name is looked up among the parameters and locals, **then the fields** of the structure, then the globals declared above the structure. So a parameter hides a field of the same name, and a field hides a global of the same name. | `run/member_lookup` | `member_param_shadows_field` |
| 5 | A call `name(…)` inside a member function calls a member function of the same structure first, then a top-level function. Functions, structures and variables have separate names: a variable may share a name with a function. | `run/member_mutation` | `unknown_function` |
| 6 | A function may call itself and any function declared anywhere in the program, above or below it. | `run/call_order`, `run/factorial_recursion` | `unknown_function` |
| 7 | Functions and structures are declared only at the top level. Their names are unique, and so are field and member names within one structure. | `valid/ast_struct` | `nested_function` |

### Types

| # | Rule | Follows | Breaks |
|---|------|---------|--------|
| 8 | An integer literal is `i32` if it fits in i32, otherwise `i64`. A literal that does not fit the type it is assigned or passed to is an error (`🎮 x 🔫 💎32 🎯 2147483648 ⚔️`). `➖` directly before a literal is part of it, so `➖2147483648` is a valid i32. | `run/print_formats` | `literal_overflow` |
| 9 | An `i32` value is widened to `i64` automatically wherever an `i64` is expected (declaration, assignment, argument, `🏁`, mixed arithmetic). Nothing is ever narrowed: an `i64` where an `i32` is expected is an error. | `run/widening` | `narrowing_assign` |
| 10 | `➕ ➖ ✖️ ➗ 🎲` and the comparisons `⬆️ ⬇️ ⬆️⚖️ ⬇️⚖️` take integers; `⚖️ 💢` take two integers or two bools; `🤝 👾 🚫` take bools. The result of an arithmetic operator is `i64` if either operand is `i64`. | `run/short_circuit` | `bool_arithmetic` |
| 11 | The condition of `🐉` must be a bool. | `run/scopes_shadowing` | `condition_not_bool` |
| 12 | A string literal can appear only as an item of `📢`. | `run/print_formats` | `string_outside_print` |
| 13 | A type name is `💎32`, `💎64`, `🛡️` or the name of a structure. A structure may not contain itself, directly or through other structures. | `run/struct_chain` | `unknown_type`, `recursive_struct` |

### Functions

| # | Rule | Follows | Breaks |
|---|------|---------|--------|
| 14 | A call passes exactly one argument per parameter, and each argument must have the parameter's type (rule 9 applies). | `run/call_order` | `too_many_args`, `too_few_args`, `wrong_arg_type` |
| 15 | The value after `🏁` must have the function's result type (rule 9 applies). | `run/widening` | `wrong_return_type` |
| 16 | Every path through a function body ends in `🏁`. An `🐉` without `👻` never counts as returning. A statement after `🏁` in the same block is unreachable and is an error. `🏁` at the top level is an error. | `run/factorial_recursion` | `missing_return`, `unreachable_after_return`, `return_outside_function` |
| 17 | Parameters are constants: they cannot be assigned. Objects are passed and returned **by value**: a function gets its own copy. | `run/struct_values` | `member_param_shadows_field` |

### Structures and mutability

| # | Rule | Follows | Breaks |
|---|------|---------|--------|
| 18 | `🆕 Name(…)` gives one value per field, in declaration order, each of the field's type. | `run/struct_chain` | `new_missing_field` |
| 19 | `.name` must name a field of the structure, and `.name(…)` a member function of it. | `run/struct_chain` | `unknown_field`, `unknown_member_function` |
| 20 | A variable or constant field declared with `🏰` cannot be assigned. An assignment through a chain `a.b.c 🎯 v` is allowed only if **every step is mutable**: `a` is a `🎮` variable, and `b` and `c` are `🎮` fields. Assigning a whole object (`p 🎯 q ⚔️`) copies it. | `run/struct_chain` | `assign_constant`, `assign_const_field`, `assign_const_chain`, `assign_const_object` |
| 21 | A member function is **mutating** if it assigns a field of its object, or calls a mutating member function on its object or on one of its fields (decided over all member functions together). A mutating member function can be called only on a chain that is mutable at every step; a constant variable, a parameter, a `🏰` field or a call result is not. Non-mutating member functions can be called on anything. | `run/member_mutation` | `mutating_call_on_const`, `mutating_call_transitive` |

### Overflow and runtime errors

| # | Rule | Follows | Breaks |
|---|------|---------|--------|
| 22 | `💥 expr 🔫 type ⚔️` checks that the integer value of `expr` fits in the integer `type`. A literal that does not fit is a compilation error; any other value is checked when the program runs. | `run/clash_runtime` | `clash_literal_overflow` |
| 23 | `➕ ➖ ✖️` and unary `➖` that overflow their type, division or modulo by zero, and `MIN ➗ ➖1` stop the program. It prints `runtime error: line L:C: message` to stderr and exits with code 1. | `run/overflow_runtime` | `run/overflow_runtime` (the runtime error itself) |

### Printing

| # | Rule | Follows |
|---|------|---------|
| 24 | `📢 item, item, … ⚔️` prints the items one after another with **no separator**, then **one newline**. A string prints as written, an integer in decimal, a bool as `true` / `false`. | `run/print_formats` |
| 25 | An object prints as its structure name and its fields in declaration order: `Name(field: value, field: value)`. A field that is an object prints the same way, nested: `Circle(center: Point(x: 1, y: 2), r: 5)`. | `run/struct_chain` |
| 26 | `📥()` reads one decimal integer from stdin and has type `i32`. If there is no integer to read, it gives `0`. | `run/point_read`, `run/read_sum` |

---

## 🚀 Building and Running

### Prerequisites

- **Python 3.9+** (tested with Python 3.13)
- **llvmlite** (tested with 0.50): `python3 -m pip install llvmlite`
- **clang** to build the generated IR (any recent version; tested with Apple clang 17)

`--ast` works without llvmlite.

### Compiling a program

```bash
python3 compiler.py program.txt program.ll   # KaguLang → LLVM IR
clang program.ll -o program                  # LLVM IR → native executable
./program
```

clang may warn that it overrides the module's target triple; the warning is harmless (`-Wno-override-module` silences it). With `llc` instead of clang: `llc program.ll -o program.s && cc program.s -o program`.

### Printing the AST

```bash
python3 compiler.py --ast tests/valid/ast_struct.txt
```

```
Program
  StructDecl(name=Point)
    fields:
      Field(name=x, type=i32, index=0, mutable=False)
      Field(name=y, type=i32, index=1, mutable=True)
    members:
      MemberFunc(struct=Point, name=shift, result=i32)
        params:
          Param(name=dy, type=i32, mutable=False)
        ...
  CallStmt
    call:
      Chain(ends_in_member_call=True)
        base:
          Identifier(p)
        steps:
          MemberCall(.shift, args=1)
  ...
```

### Errors

Every lexical, syntax or semantic error is one line on stderr, the exit code is 1, and no output file is written:

```
compilation error: line 13:3: 'add' expects 2 argument(s), got 3
```

---

## 🧪 Running the Tests

```bash
bash run_tests.sh
```

| Directory | What the runner does | Count |
|-----------|----------------------|-------|
| `tests/valid/` | `--ast` output must equal `NAME.expected` | 25 |
| `tests/run/` | compile to `.ll`, build with clang, run with `NAME.in` as stdin when it exists; stdout must equal `NAME.expected` exactly, and stderr `NAME.stderr` if that file exists | 15 |
| `tests/invalid/` | compilation must fail with exit code ≠ 0, no output file, and stderr equal to `NAME.expected` | 56 |

**40 valid programs** (25 AST + 15 end to end, two of which read input) and **56 invalid programs** (27 syntax / lexical, 29 semantic). The runner lists every failing test by name and exits non-zero if any failed. Set `PYTHON` or `CLANG` to use other executables.

---

## 📂 Project Structure

```
.
├── compiler.py          # Driver: --ast, or compile input.txt → output.ll
├── kagu/
│   ├── errors.py        # CompileError and its one-line report
│   ├── lexer.py         # Hand-written state-machine lexer over UTF-8 bytes
│   ├── nodes.py         # AST node classes with --ast dumps
│   ├── parser.py        # Recursive-descent parser, one method per rule
│   ├── semantic.py      # Symbol tables and the semantic checks
│   └── codegen.py       # LLVM IR through llvmlite.ir
├── grammar.ebnf         # Complete EBNF grammar with lexical rules
├── run_tests.sh         # Test runner
├── ai_usage.txt         # AI usage disclosure (Stage 1)
├── ai_usage_2.txt       # AI usage disclosure (Stage 2)
├── README.md
└── tests/
    ├── valid/           # NAME.txt + NAME.expected (AST dump)
    ├── run/             # NAME.txt + NAME.expected (+ NAME.in, NAME.stderr)
    └── invalid/         # NAME.txt + NAME.expected (error line)
```

---

## 🔧 Implementation Details

### Lexer
- **Hand-written state machine** over the raw bytes; the source is first checked to be valid UTF-8 (an invalid byte is reported with its line:column)
- Emoji tokens are matched by comparing byte sequences (longest match first)
- Columns count characters, not bytes
- Error messages name tokens as they are written (`'🎯'`, `identifier 'x'`, `end of file`)

### Parser
- **Recursive descent** with `peek`/`eat`, one method per grammar rule
- A statement that starts with an identifier is read as a postfix chain first; then `🎯` makes it an assignment (the chain must be a variable or a field chain), otherwise it must end in a call
- Every syntax error reports the line:column of the token that broke the rule

### Semantic analysis
- Pass 1 collects structure and function names; pass 2 resolves field types and every signature; pass 3 rejects recursive structures; pass 4 checks the top-level statements and every body in source order
- Symbol tables: `VarSymbol` (type, mutability, global / local / param), `FuncInfo` (parameter types, result type, mutating flag), `StructInfo` (fields in order with index, type and mutability; member functions)
- The mutating flag of member functions is computed as a fixed point over member-to-member calls, then every member call on an object is checked

### Code generation (`llvmlite.ir`)
- The module text is only `str(module)`; no IR is written by hand
- Names: `kagu.fn.<f>`, `kagu.member.<S>.<m>`, `kagu.struct.<S>`, `kagu.global.<v>`, and `main` for the top-level statements, so a KaguLang function named `main` or `printf` does not clash with the runtime
- All functions are declared before any body is generated
- Every function has an `entry` block holding only its `alloca`s, which jumps to `body`
- A structure is an identified struct type; an object is an `alloca` of it; a field is a `gep` with the index from the symbol table
- A member function takes a pointer to the object as its first parameter
- `printf`, `scanf`, `dprintf` and `exit` are declarations only; format strings are private global constants. Printing an object walks the structure's field table, one `gep`, `load` and `printf` per field
- Checked arithmetic uses `llvm.sadd/ssub/smul.with.overflow`; `🤝` / `👾` short-circuit with a `phi`
