"""Test to enforce that no fake data or simulated completions exist in app/ui."""

from scripts.check_no_fake_data import scan_ui_directory


def test_ui_contains_zero_fake_data():
    """Fail if app/ui contains random, completion singleShots, or hardcoded numeric unit strings."""
    violations = scan_ui_directory()
    formatted_errors = [
        f"{path.name}:{lineno} [{rule}] {detail}"
        for path, lineno, rule, detail in violations
    ]
    assert len(violations) == 0, (
        f"Detected {len(violations)} fake data / simulated completion violation(s) in app/ui:\n"
        + "\n".join(formatted_errors)
    )
