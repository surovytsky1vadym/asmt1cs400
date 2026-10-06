#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
#  KaguLang test runner
#  Runs all valid and invalid test cases and reports results.
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPILER="$SCRIPT_DIR/compiler.py"
TESTS_DIR="$SCRIPT_DIR/tests"

PASS=0
FAIL=0
TOTAL=0

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  🎮 KaguLang Test Runner"
echo "═══════════════════════════════════════════════════════"
echo ""

# ── Valid tests ──────────────────────────────────────────────────────────────
echo "${YELLOW}── Valid tests (happy path) ──${NC}"
for input in "$TESTS_DIR"/valid/*.txt; do
    test_name=$(basename "$input" .txt)
    expected="${input%.txt}.expected"
    TOTAL=$((TOTAL + 1))

    if [ ! -f "$expected" ]; then
        echo -e "  ${RED}FAIL${NC}  $test_name  (missing expected file)"
        FAIL=$((FAIL + 1))
        continue
    fi

    actual=$(python3 "$COMPILER" --ast "$input" 2>&1) || true
    rc=${PIPESTATUS[0]:-$?}

    expected_content=$(cat "$expected")

    if [ "$actual" = "$expected_content" ]; then
        echo -e "  ${GREEN}PASS${NC}  $test_name"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}FAIL${NC}  $test_name"
        echo "    Expected:"
        head -3 "$expected" | sed 's/^/      /'
        echo "    Got:"
        echo "$actual" | head -3 | sed 's/^/      /'
        FAIL=$((FAIL + 1))
    fi
done

echo ""

# ── Invalid tests ────────────────────────────────────────────────────────────
echo "${YELLOW}── Invalid tests (error scenarios) ──${NC}"
for input in "$TESTS_DIR"/invalid/*.txt; do
    test_name=$(basename "$input" .txt)
    expected="${input%.txt}.expected"
    TOTAL=$((TOTAL + 1))

    if [ ! -f "$expected" ]; then
        echo -e "  ${RED}FAIL${NC}  $test_name  (missing expected file)"
        FAIL=$((FAIL + 1))
        continue
    fi

    actual_stderr=$(python3 "$COMPILER" --ast "$input" 2>&1 >/dev/null) || true

    expected_content=$(cat "$expected")

    if [ "$actual_stderr" = "$expected_content" ]; then
        echo -e "  ${GREEN}PASS${NC}  $test_name"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}FAIL${NC}  $test_name"
        echo "    Expected: $(cat "$expected")"
        echo "    Got:      $actual_stderr"
        FAIL=$((FAIL + 1))
    fi
done

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════"
echo -e "  Results: ${GREEN}$PASS passed${NC}, ${RED}$FAIL failed${NC}, $TOTAL total"
echo "═══════════════════════════════════════════════════════"
echo ""

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
exit 0
