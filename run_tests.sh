#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
#  KaguLang test runner
#
#  tests/valid/NAME.txt    --ast output must equal NAME.expected
#  tests/run/NAME.txt      compiled to .ll, built with clang and run;
#                          stdin is NAME.in when it exists; stdout must equal
#                          NAME.expected exactly (and stderr NAME.stderr, if
#                          that file exists)
#  tests/invalid/NAME.txt  compilation must fail: exit code != 0, no output
#                          file, and stderr equal to NAME.expected
#
#  Environment: PYTHON (default python3), CLANG (default clang).
# ──────────────────────────────────────────────────────────────────────────────

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPILER="$SCRIPT_DIR/compiler.py"
TESTS_DIR="$SCRIPT_DIR/tests"
PYTHON="${PYTHON:-python3}"
CLANG="${CLANG:-clang}"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

PASS=0
FAILED=()

RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
NC=$'\033[0m'

pass() {
    echo "  ${GREEN}PASS${NC}  $1"
    PASS=$((PASS + 1))
}

fail() {
    echo "  ${RED}FAIL${NC}  $1  ($2)"
    FAILED+=("$1")
}

# show_diff EXPECTED_FILE ACTUAL_FILE — first lines of the difference
show_diff() {
    diff "$1" "$2" | head -10 | sed 's/^/        /'
}

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  🎮 KaguLang Test Runner"
echo "═══════════════════════════════════════════════════════"

# ── AST tests ────────────────────────────────────────────────────────────────
echo ""
echo "${YELLOW}── AST tests (--ast) ──${NC}"
for input in "$TESTS_DIR"/valid/*.txt; do
    name="valid/$(basename "$input" .txt)"
    expected="${input%.txt}.expected"
    if [ ! -f "$expected" ]; then
        fail "$name" "missing expected file"
        continue
    fi
    "$PYTHON" "$COMPILER" --ast "$input" > "$WORK/out" 2>&1
    if diff -q "$expected" "$WORK/out" > /dev/null; then
        pass "$name"
    else
        fail "$name" "AST differs"
        show_diff "$expected" "$WORK/out"
    fi
done

# ── End-to-end tests ─────────────────────────────────────────────────────────
echo ""
echo "${YELLOW}── End-to-end tests (compile, build, run) ──${NC}"
for input in "$TESTS_DIR"/run/*.txt; do
    base="${input%.txt}"
    name="run/$(basename "$base")"
    if [ ! -f "$base.expected" ]; then
        fail "$name" "missing expected file"
        continue
    fi
    if ! "$PYTHON" "$COMPILER" "$input" "$WORK/prog.ll" 2> "$WORK/err"; then
        fail "$name" "compilation failed: $(head -1 "$WORK/err")"
        continue
    fi
    if ! "$CLANG" -Wno-override-module "$WORK/prog.ll" -o "$WORK/prog" 2> "$WORK/err"; then
        fail "$name" "clang failed: $(head -1 "$WORK/err")"
        continue
    fi
    stdin_file=/dev/null
    [ -f "$base.in" ] && stdin_file="$base.in"
    "$WORK/prog" < "$stdin_file" > "$WORK/out" 2> "$WORK/err"

    if ! diff -q "$base.expected" "$WORK/out" > /dev/null; then
        fail "$name" "stdout differs"
        show_diff "$base.expected" "$WORK/out"
    elif [ -f "$base.stderr" ] && ! diff -q "$base.stderr" "$WORK/err" > /dev/null; then
        fail "$name" "stderr differs"
        show_diff "$base.stderr" "$WORK/err"
    else
        pass "$name"
    fi
    rm -f "$WORK/prog.ll" "$WORK/prog"
done

# ── Invalid programs ─────────────────────────────────────────────────────────
echo ""
echo "${YELLOW}── Invalid programs (compilation errors) ──${NC}"
for input in "$TESTS_DIR"/invalid/*.txt; do
    name="invalid/$(basename "$input" .txt)"
    expected="${input%.txt}.expected"
    if [ ! -f "$expected" ]; then
        fail "$name" "missing expected file"
        continue
    fi
    rm -f "$WORK/bad.ll"
    "$PYTHON" "$COMPILER" "$input" "$WORK/bad.ll" > /dev/null 2> "$WORK/err"
    rc=$?
    if [ "$rc" -eq 0 ]; then
        fail "$name" "compiled without an error"
    elif [ -e "$WORK/bad.ll" ]; then
        fail "$name" "an output file was written"
    elif ! diff -q "$expected" "$WORK/err" > /dev/null; then
        fail "$name" "error message differs"
        show_diff "$expected" "$WORK/err"
    else
        pass "$name"
    fi
done

# ── Summary ──────────────────────────────────────────────────────────────────
TOTAL=$((PASS + ${#FAILED[@]}))
echo ""
echo "═══════════════════════════════════════════════════════"
echo "  Results: ${GREEN}$PASS passed${NC}, ${RED}${#FAILED[@]} failed${NC}, $TOTAL total"
if [ "${#FAILED[@]}" -gt 0 ]; then
    echo "  Failed:"
    for name in "${FAILED[@]}"; do
        echo "    - $name"
    done
fi
echo "═══════════════════════════════════════════════════════"
echo ""

[ "${#FAILED[@]}" -eq 0 ]
