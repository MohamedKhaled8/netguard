"""Unit tests for Arabic plural grammar and bidi isolates (L6)."""

from app.ui.tokens import format_arabic_connections, bidi_isolate


def test_arabic_connection_plurals():
    assert format_arabic_connections(0) == "لا توجد اتصالات"
    assert format_arabic_connections(1) == "اتصال واحد"
    assert format_arabic_connections(2) == "اتصالان"
    assert format_arabic_connections(3) == "3 اتصالات"
    assert format_arabic_connections(8) == "8 اتصالات"
    assert format_arabic_connections(10) == "10 اتصالات"
    assert format_arabic_connections(11) == "11 اتصالاً"
    assert format_arabic_connections(26) == "26 اتصالاً"


def test_bidi_isolation():
    isolated = bidi_isolate("5M")
    assert isolated.startswith("\u2066")
    assert isolated.endswith("\u2069")
    assert "5M" in isolated
