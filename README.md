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
| `🔁` | repeat | `while` loop (Stage 3) |
| `🏃` | run | `for` loop over an integer range (Stage 3) |
| `🛑` | break | Leave the innermost loop (Stage 3) |

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
| `⏩` | Range in `🏃`: `from ⏩ to`, `to` excluded (Stage 3) |

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

## 🔁 Stage 3 Feature — Loops

KaguLang gets `while` (`🔁`), `for` over an integer range (`🏃`) and `break` (`🛑`).

```
🔁 condition 🏟️ statements 🏟️                          // while
🏃 i 🔫 💎32 🎯 from ⏩ to 🏟️ statements 🏟️             // for i in [from, to)
🛑 ⚔️                                                   // break
```

### Rules

| # | Rule | Follows | Breaks |
|---|------|---------|--------|
| 27 | The condition of `🔁` must be a bool. It is checked before every pass, so the body may run zero times. | `run/loops_while` | `loops_condition_not_bool` |
| 28 | `🏃 i 🔫 T 🎯 from ⏩ to` needs an integer type `T`; `from` and `to` must be assignable to `T` (rule 9). `i` takes `from, from+1, …, to−1`; `to` is evaluated **once**, before the first pass, so changing a variable used in `to` inside the body does not change the number of passes. An empty range (`to ≤ from`) runs the body zero times. | `run/loops_for_nested` | `loops_range_type` |
| 29 | The loop variable is a **constant** inside the body: only `🏃` advances it. | `run/loops_for_nested` | `loops_assign_loop_var` |
| 30 | The loop variable lives in its own scope around the body, and the body is one more block scope (rule 2): a variable declared in the body is created again on every pass and is not visible after the loop. Loops nest; a nested loop may declare the same names. | `run/loops_for_nested` | `loops_var_out_of_scope` |
| 31 | `🛑 ⚔️` leaves the **innermost** loop. It is an error outside a loop (an `🐉` alone is not a loop), and a statement after `🛑` in the same block is unreachable. | `run/loops_break` | `loops_break_outside`, `loops_unreachable_after_break` |
| 32 | A loop never counts as returning (rule 16): a function whose `🏁` is only inside a loop body still needs a `🏁` after the loop. | `run/loops_break` | — |

### Example 1 — while: Collatz steps

```
🪄 next(n 🔫 💎64) ➡️ 💎64 🏟️
  🐉 n 🎲 2 ⚖️ 0 🏟️
    🏁 n ➗ 2 ⚔️
  🏟️
  🏁 3 ✖️ n ➕ 1 ⚔️
🏟️

🎮 n 🔫 💎64 🎯 📥() ⚔️
🎮 steps 🔫 💎32 🎯 0 ⚔️
🔁 n 💢 1 🏟️
  n 🎯 next(n) ⚔️
  steps 🎯 steps ➕ 1 ⚔️
🏟️
📢 "steps: ", steps ⚔️             // input 27 → steps: 111
```

### Example 2 — nested for with break

```
🏃 i 🔫 💎32 🎯 0 ⏩ 3 🏟️
  🏃 j 🔫 💎32 🎯 0 ⏩ 10 🏟️
    🐉 j ⬆️ i 🏟️
      🛑 ⚔️                       // ends the j loop, the i loop goes on
    🏟️
    🎮 cell 🔫 💎32 🎯 i ✖️ 10 ➕ j ⚔️
    📢 cell ⚔️                    // 0 10 11 20 21 22
  🏟️
🏟️
```

### Lowering and the IR it produces

`🔁` becomes three blocks: `while.cond` evaluates the condition and branches to `while.body` or `while.end`; the body ends with a branch back to `while.cond`. `🏃` adds a fourth block, `for.step`, which adds 1 to the loop variable (`add nsw`: `i < to`, so `i + 1` cannot overflow) and jumps back to `for.cond`; the loop variable and the saved `to` live in two `alloca`s of the entry block. `🛑` is a branch to the `.end` block of the innermost loop (the code generator keeps a stack of them). Every stack slot, including those of variables declared in a loop body, is allocated once in the function's `entry` block, so a loop never grows the stack.

Excerpt of `output.ll` for

```
🎮 n 🔫 💎32 🎯 📥() ⚔️
🔁 n ⬆️ 0 🏟️
  🐉 n ⚖️ 5 🏟️ 🛑 ⚔️ 🏟️
  n 🎯 n ➖ 1 ⚔️
🏟️
```

```llvm
  br label %"while.cond"
while.cond:
  %"n" = load i32, i32* @"kagu.global.n"
  %".7" = icmp sgt i32 %"n", 0
  br i1 %".7", label %"while.body", label %"while.end"
while.body:
  %"n.1" = load i32, i32* @"kagu.global.n"
  %".9" = icmp eq i32 %"n.1", 5
  br i1 %".9", label %"if.then", label %"if.end"
while.end:
  ret i32 0
if.then:
  br label %"while.end"
if.end:
  ; ... n - 1 through llvm.ssub.with.overflow, then the store to n ...
ok:
  %".17" = extractvalue {i32, i1} %".12", 0
  store i32 %".17", i32* @"kagu.global.n"
  br label %"while.cond"
```

`while.cond` loads `n` again on every pass and compares it with 0 (`icmp sgt`); the conditional branch either enters `while.body` or leaves to `while.end`, which is the code after the loop. `if.then` is the `🛑`: an unconditional branch straight to `while.end`, which skips the rest of the body. The last line, `br label %"while.cond"` at the end of the body, is the **back edge**: it is the only branch that jumps backwards, and it is what makes the blocks a loop.

---

## ⚡ Optimizer (`--optimize`)

`--optimize`, anywhere on the command line, runs `kagu/optimizer.py` on the **checked** tree before code generation; with `--ast` it prints the tree after the optimizer. The tree is analysed again before every round, and the three transformations are repeated until a whole round changes nothing. They work on symbols from the semantic pass, not on names, so a shadowing variable is a different variable from the one it hides.

- **Unused variables.** A variable (local or global) that is never read is removed with every assignment to it. Reading means appearing anywhere except as the target of an assignment and inside the value assigned to that same variable (`x 🎯 x ➕ 1` does not make `x` used). Removing a declaration may leave another variable unread; the next round removes it. A value that calls a function, a member function or `📥()` is never dropped: if the value *is* the call it stays as a call statement, if the call is deeper inside (`noisy(2) ➕ 1`) the whole declaration stays. Parameters and loop variables are never removed.
- **Unused functions.** A top-level function is used if a call to it appears anywhere outside its own body. An unused function is removed with its body; that may leave the functions it called unused, and the next round removes them. A recursive function called only by itself, or two functions calling only each other, are removed too once nothing else calls them. Member functions are part of their structure and are kept.
- **Inlining.** A top-level function called exactly once in the whole program, and not recursive (directly or through other functions), is inlined at the call site: each parameter becomes a `🏰` constant initialised with its argument, the body follows, and the value of the final `🏁` becomes a constant `f_result_K` that stands where the call stood. Every parameter and every variable of the inlined body (loop variables too) gets a fresh name `f_name_K` that no name in the program uses. The function then has no calls left and the next round removes it as unused. A call used as a statement just leaves the body behind.

**Shapes that are inlined:** a body whose only `🏁` is its last statement, with any `🐉`, `🔁`, `🏃`, locals and calls before it, when the call is the first thing with an effect in a declaration, assignment, `🐉` condition, `📢`, `🏁`, `💥` or call statement (it may sit inside other calls' argument lists and inside arithmetic).

**Shapes that are left alone:** a body that leaves through `🏁` inside an `🐉` or a loop (it would need a jump to the end of the inlined code); a body that reads or writes a global variable (the call site may see a different variable with that name); a call on the right side of `🤝` / `👾` (it may never run) or after another call or `📥()` in the same statement (the order of effects would change); a call inside a loop condition or a `🏃` range; a call inside a member function whose structure has a member with the name of a function the body calls (a bare call there would mean the member).

Six programs in `tests/optimizer/`, two per transformation; each has `NAME.ast` (the tree after `--optimize --ast`) and `NAME.expected` (the output, which must be the same with and without the flag):

| Program | Shows |
|---------|-------|
| `unused_vars_chain` | `z` reads `y`, `y` reads `x`, nobody reads `z`: three rounds remove all three; `kept` stays |
| `unused_vars_scopes` | an unread inner `v` shadowing a read outer one; values with a call or `📥()` kept as calls; a variable in a loop body |
| `unused_funcs_chain` | `top → middle → bottom` removed one by one; `used` inlined, `helper` (two calls) kept |
| `unused_funcs_recursive` | `spin` calls only itself and is removed; recursive `fact` is used and kept |
| `inline_simple` | `square` inlined; its `x` and `r` renamed so they do not collide with the caller's `x` and `r` |
| `inline_shapes` | `sum_to` (a loop and an `🐉` in the body) inlined; `sign` (`🏁` inside `🐉`), recursive `fib` and `twice` (two calls) left alone |

`bash run_tests.sh --optimize` runs every end-to-end, invalid and program test with the flag as well; they all pass.

### Inlining in the IR

```
🪄 square(x 🔫 💎32) ➡️ 💎32 🏟️
  🏁 x ✖️ x ⚔️
🏟️
🎮 n 🔫 💎32 🎯 📥() ⚔️
📢 square(n ➕ 1) ⚔️
```

Before (without `--optimize`), `main` calls the function:

```llvm
define i32 @"kagu.fn.square"(i32 %"x")
  ...
  %".4" = call {i32, i1} @"llvm.smul.with.overflow.i32"(i32 %"x.2", i32 %"x.3")
  ...
define i32 @"main"()
  ...
  %".12" = call i32 @"kagu.fn.square"(i32 %".11")
  %".13" = call i32 (i8*, ...) @"printf"(i8* ... @"kagu.str.2" ..., i32 %".12")
```

After (`--optimize`), `kagu.fn.square` is gone and its body is in `main`:

```llvm
ok:
  %".11" = extractvalue {i32, i1} %".6", 0
  store i32 %".11", i32* @"kagu.global.square_x_1"
  %"square_x_1" = load i32, i32* @"kagu.global.square_x_1"
  %"square_x_1.1" = load i32, i32* @"kagu.global.square_x_1"
  %".13" = call {i32, i1} @"llvm.smul.with.overflow.i32"(i32 %"square_x_1", i32 %"square_x_1.1")
  ...
ok.1:
  %".18" = extractvalue {i32, i1} %".13", 0
  store i32 %".18", i32* @"kagu.global.square_result_1"
  %"square_result_1" = load i32, i32* @"kagu.global.square_result_1"
  %".20" = call i32 (i8*, ...) @"printf"(i8* ... @"kagu.str.1" ..., i32 %"square_result_1")
```

The parameter `x` became `square_x_1`, stored once from the argument `n ➕ 1`; the call became `square_result_1`. The call was at the top level, so both are top-level constants and therefore module globals; inside a function they would be `alloca`s.

---

## ⚔️ The Real Program — KaguLang Arena

`programs/arena.txt` is a turn-based battle. The player chooses how many waves to fight (1 to 5); every wave brings a stronger monster, made by the function `spawn_monster`.
Each turn the player types `1` (attack), `2` (drink a potion) or `3` (run away); the monster hits back, and damage comes from a small random generator, `next_roll`, so the same moves always give the same game.
The structures `Hero` and `Monster` have member functions `alive`, `hurt` and, for the hero, `drink`; hp, potions and gold live in their fields.
Loops are the core of the program: `🏃 wave … ⏩ waves ➕ 1` walks over the waves, `🔁 🏆` runs the turns of one fight, and `🛑` ends a fight when the monster falls, when the hero falls or when the hero runs (then a second `🛑` leaves the wave loop too).
`spawn_monster` grows the monster with a `🏃` loop, `📥()` reads every choice, `📢` prints every prompt and result.
Three recorded sessions: `arena.1` wins both waves using a potion, `arena.2` attacks through five waves and falls in wave 4, `arena.3` makes an unknown move and runs away.
Build it into a native binary (`llc` from LLVM, then `clang` to link):

```bash
python3 compiler.py programs/arena.txt arena.ll
llc -filetype=obj -mtriple="$(clang -print-target-triple)" arena.ll -o arena.o
clang arena.o -o arena
./arena < programs/arena.1.in     # session 1; compare with programs/arena.1.expected
./arena < programs/arena.2.in     # session 2
./arena < programs/arena.3.in     # session 3
```

`-mtriple` makes `llc` produce code for the machine clang links for (the module carries the triple of the Python that ran the compiler, which on a Mac with an x86_64 Python under Rosetta is not the arm64 of clang). Tested with Homebrew LLVM's `llc` and Apple clang 17. `run_tests.sh` builds the program and checks every `programs/NAME.K.in` against `programs/NAME.K.expected`.

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

python3 compiler.py --optimize program.txt program.ll   # the same, optimized
python3 compiler.py --optimize --ast program.txt        # the tree after the optimizer
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
bash run_tests.sh              # everything
bash run_tests.sh --optimize   # end-to-end, invalid and program tests built with --optimize
```

| Directory | What the runner does | Count |
|-----------|----------------------|-------|
| `tests/valid/` | `--ast` output must equal `NAME.expected` | 25 |
| `tests/run/` | compile to `.ll`, build with clang, run with `NAME.in` as stdin when it exists; stdout must equal `NAME.expected` exactly, and stderr `NAME.stderr` if that file exists | 15 |
| `tests/invalid/` | compilation must fail with exit code ≠ 0, no output file, and stderr equal to `NAME.expected` | 62 |
| `tests/optimizer/` | `--optimize --ast` must equal `NAME.ast`; the program built with and without `--optimize` must print `NAME.expected` both times | 6 |
| `programs/` | build `NAME.txt`, run every session `NAME.K.in`, output must equal `NAME.K.expected` | 3 sessions |

**44 valid programs** (26 AST + 18 end to end) and **62 invalid programs**. The loop tests are `valid/loops_ast`, `run/loops_while`, `run/loops_for_nested`, `run/loops_break` and six `invalid/loops_*`. The runner lists every failing test by name and exits non-zero if any failed. Set `PYTHON` or `CLANG` to use other executables.

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
│   ├── optimizer.py     # --optimize: unused variables / functions, inlining
│   └── codegen.py       # LLVM IR through llvmlite.ir
├── grammar.ebnf         # Complete EBNF grammar with lexical rules
├── run_tests.sh         # Test runner
├── ai_usage.txt         # AI usage disclosure (Stage 1)
├── ai_usage_2.txt       # AI usage disclosure (Stage 2)
├── ai_usage_3.txt       # AI usage disclosure (Stage 3)
├── programs/            # arena.txt + recorded sessions arena.K.in / .expected
├── README.md
└── tests/
    ├── valid/           # NAME.txt + NAME.expected (AST dump)
    ├── run/             # NAME.txt + NAME.expected (+ NAME.in, NAME.stderr)
    ├── invalid/         # NAME.txt + NAME.expected (error line)
    └── optimizer/       # NAME.txt + NAME.ast + NAME.expected (+ NAME.in)
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
