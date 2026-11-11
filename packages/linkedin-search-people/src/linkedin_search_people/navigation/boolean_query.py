from __future__ import annotations

import re
from dataclasses import dataclass

_SMART_QUOTES = {
    "\u201c": '"',
    "\u201d": '"',
    "\u201e": '"',
    "\u00ab": '"',
    "\u00bb": '"',
    "\u2018": "'",
    "\u2019": "'",
}

_OP_RE = re.compile(r"\b(AND|OR|NOT)\b")
_LOWER_OP_RE = re.compile(r"\b(and|or|not)\b")
_PLUS_MINUS_RE = re.compile(r"(?<![A-Za-z0-9])[+\-](?=\S)")


@dataclass(frozen=True, slots=True)
class BooleanQueryResult:
    query: str
    warnings: tuple[str, ...]
    errors: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


def _replace_smart_quotes(text: str) -> str:
    out = text
    for src, dst in _SMART_QUOTES.items():
        out = out.replace(src, dst)
    return out


def _split_quoted(text: str) -> list[tuple[str, bool]]:
    """Split into (chunk, is_quoted) pieces. Unbalanced quotes leave a trailing unquoted remainder."""
    parts: list[tuple[str, bool]] = []
    buf: list[str] = []
    in_quote = False
    for ch in text:
        if ch == '"':
            if in_quote:
                buf.append(ch)
                parts.append(("".join(buf), True))
                buf = []
                in_quote = False
            else:
                if buf:
                    parts.append(("".join(buf), False))
                    buf = []
                buf.append(ch)
                in_quote = True
        else:
            buf.append(ch)
    if buf:
        parts.append(("".join(buf), in_quote))
    return parts


def _uppercase_operators(text: str) -> str:
    pieces = _split_quoted(text)

    def repl(m: re.Match[str]) -> str:
        return m.group(1).upper()

    out: list[str] = []
    for chunk, quoted in pieces:
        out.append(chunk if quoted else _LOWER_OP_RE.sub(repl, chunk))
    return "".join(out)


def _balanced(text: str) -> tuple[bool, bool]:
    """Returns (quotes_ok, parens_ok)."""
    in_quote = False
    depth = 0
    for ch in text:
        if ch == '"':
            in_quote = not in_quote
            continue
        if in_quote:
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:
                return (not in_quote, False)
    return (not in_quote, depth == 0)


def _tokens_outside_quotes(text: str) -> list[str]:
    tokens: list[str] = []
    for chunk, quoted in _split_quoted(text):
        if quoted:
            tokens.append(chunk)
            continue
        tokens.extend(re.findall(r"\(|\)|\bAND\b|\bOR\b|\bNOT\b|[^\s()]+", chunk))
    return tokens


def validate_boolean_query(text: str) -> tuple[str, ...]:
    errors: list[str] = []
    quotes_ok, parens_ok = _balanced(text)
    if not quotes_ok:
        errors.append("unbalanced quotes")
    if not parens_ok:
        errors.append("unbalanced parentheses")
    tokens = _tokens_outside_quotes(text)
    if tokens:
        first, last = tokens[0], tokens[-1]
        if first in {"AND", "OR"}:
            errors.append("query cannot start with AND/OR")
        if last in {"AND", "OR", "NOT"}:
            errors.append("query cannot end with AND/OR/NOT")
    return tuple(errors)


def normalize_boolean_query(raw: str) -> BooleanQueryResult:
    text = _replace_smart_quotes(raw or "").strip()
    warnings: list[str] = []
    if _PLUS_MINUS_RE.search(text):
        warnings.append("LinkedIn does not support + or -; use AND / NOT instead")
    text = _uppercase_operators(text)
    text = re.sub(r"\s+", " ", text).strip()
    errors = validate_boolean_query(text)
    return BooleanQueryResult(query=text, warnings=tuple(warnings), errors=errors)
