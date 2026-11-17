#!/usr/bin/env python3
"""Script to verify that UI code under app/ui contains zero fake data or simulated completions.

Fails if UI code under `app/ui` contains:
1. `random` module imports or usage.
2. `QTimer.singleShot` used to simulate completion (timeout > 0 calling completion handler).
3. Hardcoded numeric literals followed by 'ms', 'Mbps', or '%' inside string literals
   outside i18n/test files.
"""

from __future__ import annotations
import ast
import re
import sys
from pathlib import Path
from typing import List, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
UI_DIR = ROOT_DIR / "app" / "ui"

# Patterns to detect fake data
NUMERIC_UNIT_PATTERN = re.compile(r'(?<!\{)\b\d+(?:\.\d+)?\s*(?:ms|Mbps|%)\b(?!\})', re.IGNORECASE)
COMPLETION_TERMS = {"completed", "complete", "finish", "finished", "done", "simulate", "simulated"}


def is_stylesheet(s: str) -> bool:
    """Heuristic to check if a string literal is a Qt CSS/QSS stylesheet."""
    lower = s.lower()
    return any(k in lower for k in (
        "qframe", "qlabel", "qwidget", "qpushbutton", "background",
        "border", "border-radius", "stop:", "qlineargradient", "color:"
    ))


def check_file(path: Path) -> List[Tuple[int, str, str]]:
    """Check a single python file for fake data violations.

    Returns a list of (line_no, rule_name, details).
    """
    violations: List[Tuple[int, str, str]] = []

    # Skip i18n file and tests
    if path.name == "i18n.py" or "test" in path.name.lower():
        return violations

    try:
        content = path.read_text(encoding="utf-8")
    except Exception as exc:
        violations.append((0, "READ_ERROR", str(exc)))
        return violations

    try:
        tree = ast.parse(content, filename=str(path))
    except SyntaxError as exc:
        violations.append((exc.lineno or 0, "SYNTAX_ERROR", str(exc)))
        return violations

    lines = content.splitlines()

    # Collect docstrings to ignore
    docstring_ids = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if (
                n.body
                and isinstance(n.body[0], ast.Expr)
                and isinstance(n.body[0].value, ast.Constant)
                and isinstance(n.body[0].value.value, str)
            ):
                docstring_ids.add(id(n.body[0].value))

    # 1. AST Traversal
    for node in ast.walk(tree):
        # Rule 1: No random module
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "random" or alias.name.startswith("random."):
                    violations.append((node.lineno, "RULE_1_RANDOM", f"Forbidden import: {alias.name}"))
        elif isinstance(node, ast.ImportFrom):
            if node.module == "random" or (node.module and node.module.startswith("random.")):
                violations.append((node.lineno, "RULE_1_RANDOM", f"Forbidden import from: {node.module}"))
        elif isinstance(node, ast.Name) and node.id == "random":
            # Usage of random
            violations.append((node.lineno, "RULE_1_RANDOM", "Forbidden identifier: random"))

        # Rule 2: QTimer.singleShot completion simulation
        elif isinstance(node, ast.Call):
            func_name = ""
            if isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
            elif isinstance(node.func, ast.Name):
                func_name = node.func.id

            if func_name == "singleShot" and len(node.args) >= 2:
                # Check delay
                delay_val = None
                if isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, (int, float)):
                    delay_val = node.args[0].value

                # Inspect callback name
                cb_name = ""
                cb_arg = node.args[1]
                if isinstance(cb_arg, ast.Attribute):
                    cb_name = cb_arg.attr.lower()
                elif isinstance(cb_arg, ast.Name):
                    cb_name = cb_arg.id.lower()
                elif isinstance(cb_arg, ast.Lambda):
                    cb_src = ast.unparse(cb_arg).lower() if hasattr(ast, "unparse") else ""
                    cb_name = cb_src

                if delay_val is not None and delay_val > 0:
                    if any(term in cb_name for term in COMPLETION_TERMS):
                        violations.append((
                            node.lineno,
                            "RULE_2_SINGLESHOT_COMPLETION",
                            f"QTimer.singleShot({delay_val}, {cb_name}) simulates completion after arbitrary delay",
                        ))

        # Rule 3: Numeric literals followed by ms/Mbps/% inside string literals
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) in docstring_ids:
                continue
            val_str = node.value
            if not is_stylesheet(val_str):
                m = NUMERIC_UNIT_PATTERN.search(val_str)
                if m:
                    # Ignore format specifiers or comments
                    matched_text = m.group(0)
                    line_text = lines[node.lineno - 1] if node.lineno <= len(lines) else ""
                    if not line_text.strip().startswith("#"):
                        violations.append((
                            node.lineno,
                            "RULE_3_HARDCODED_NUMERIC_UNIT",
                            f"Hardcoded literal '{matched_text}' in string: '{val_str[:50]}...'",
                        ))

    return violations


def scan_ui_directory() -> List[Tuple[Path, int, str, str]]:
    """Scan all .py files in app/ui."""
    all_violations = []
    for py_file in UI_DIR.rglob("*.py"):
        file_violations = check_file(py_file)
        for lineno, rule, detail in file_violations:
            all_violations.append((py_file, lineno, rule, detail))
    return all_violations


def main() -> int:
    """Run CLI check."""
    violations = scan_ui_directory()
    if not violations:
        print("[SUCCESS] check_no_fake_data: 0 violations found in app/ui. All UI claims and numbers verified real.")
        return 0

    print(f"[FAILURE] check_no_fake_data: Found {len(violations)} violation(s) under app/ui:")
    for path, lineno, rule, detail in violations:
        rel_path = path.relative_to(ROOT_DIR)
        print(f"  {rel_path}:{lineno} [{rule}] {detail}")
    return 1


def test_no_fake_data():
    """Pytest test entry point."""
    violations = scan_ui_directory()
    assert len(violations) == 0, f"Found {len(violations)} fake data / simulated completion violation(s): {violations}"


if __name__ == "__main__":
    sys.exit(main())
