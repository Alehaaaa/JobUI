import re
from typing import Any

# --- JSON Extraction Logic ---

_TOKEN_RE = re.compile(
    r"""
    (?:(?P<name>[^.\[\]]+))? # optional key name
    (?:\[(?P<index>\d+|\*)\])? # optional [0] or [*]
    (?:\.)?                    # optional dot
""",
    re.VERBOSE,
)


class JsonPathError(Exception):
    pass


def _tokenize(path: str):
    path = path.strip()
    if not path:
        return []
    pos = 0
    tokens = []
    while pos < len(path):
        m = _TOKEN_RE.match(path, pos)
        if not m or (m.group("name") is None and m.group("index") is None):
            raise JsonPathError(f"Invalid path near: {path[pos : pos + 30]!r}")

        name = m.group("name")
        idx = m.group("index")
        tokens.append((name, idx))
        if m.end() == pos:
            break
        pos = m.end()
    return tokens


def _split_safe(text: str, delimiter: str):
    """
    Split text by delimiter, ignoring delimiters inside quotes.
    """
    result = []
    current = []
    quote_char = None

    for char in text:
        if quote_char:
            if char == quote_char:
                quote_char = None
            current.append(char)
        elif char in ("'", '"'):
            quote_char = char
            current.append(char)
        elif char == delimiter:
            result.append("".join(current).strip())
            current = []
        else:
            current.append(char)

    if current:
        result.append("".join(current).strip())
    elif text.endswith(delimiter):
        result.append("")

    return [r for r in result if r]  # Filter empty splits if any


def _is_literal(text: str) -> bool:
    return len(text) >= 2 and (
        (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'"))
    )


def extract_json(data: Any, path: str, default: Any = None) -> Any:
    """
    Extract values from nested dict/list structures using a path string.
    Supports:
    1. Fallbacks (comma): "pathA, pathB" -> Try A, then B.
    2. Concatenation (plus): "pathA + ' - ' + pathB" -> "ValueA - ValueB" (only if all parts exist).
    3. Literals in concatenation: strings enclosed in ' or ".
    """
    if not path:
        return data

    # 1. Fallbacks (split by comma, respecting quotes)
    # Only split if comma is present to avoid overhead
    if "," in path:
        options = _split_safe(path, ",")
        if len(options) > 1:
            for opt in options:
                val = extract_json(data, opt, default=None)
                if val is not None and val != "" and val != []:
                    return val
            return default

    # 2. Concatenation (split by plus, respecting quotes)
    if "+" in path:
        parts = _split_safe(path, "+")
        if len(parts) > 1:
            concat_res = []
            for part in parts:
                part = part.strip()
                if _is_literal(part):
                    # Remove quotes
                    concat_res.append(part[1:-1])
                else:
                    # Recursive extract
                    val = extract_json(data, part, default=None)
                    if val is None or val == "":
                        # If any part of concatenation is missing, fail this path
                        return default
                    concat_res.append(str(val))
            return "".join(concat_res)

    # 3. Standard Path Extraction
    try:
        tokens = _tokenize(path)
        if not tokens:
            return data

        used_wildcard = any(idx == "*" for _, idx in tokens)
        current = [data]

        for key, idx in tokens:
            next_nodes = []
            for node in current:
                # Key lookup
                if key:
                    if isinstance(node, dict) and key in node:
                        value = node[key]
                    else:
                        continue
                else:
                    value = node

                # Index/Wildcard
                if idx is None:
                    next_nodes.append(value)
                elif idx == "*":
                    if isinstance(value, list):
                        next_nodes.extend(value)
                else:
                    if isinstance(value, list):
                        try:
                            i = int(idx)
                            if -len(value) <= i < len(value):
                                next_nodes.append(value[i])
                        except (ValueError, IndexError):
                            continue
            current = next_nodes

        if not current and not used_wildcard:
            return default

        if used_wildcard:
            return current

        return current[0] if len(current) == 1 else (current if current else default)

    except Exception:
        return default


# --- HTML Extraction Logic ---


def extract_html(soup_or_elem, selector, attr="text", default=None, index=None):
    """
    Extracts data from a BeautifulSoup object or Tag using CSS selectors.
    """
    if not selector:
        elem = soup_or_elem
    else:
        if index is not None:
            elems = soup_or_elem.select(selector)

            # Handle slice string like "1:"
            if isinstance(index, str) and ":" in index:
                try:
                    parts = index.split(":")
                    start = int(parts[0]) if parts[0] else None
                    end = int(parts[1]) if parts[1] else None
                    subset = elems[slice(start, end)]
                    if not subset:
                        return default

                    results = []
                    for e in subset:
                        text = ""
                        if attr == "text":
                            text = e.get_text(separator=" ", strip=True)
                        elif attr == "html":
                            text = str(e)
                        else:
                            val = e.get(attr)
                            if val:
                                text = " ".join(val) if isinstance(val, list) else str(val)

                        # Skip if it's just a separator or empty
                        clean_text = text.strip("·•|* ").strip()
                        if clean_text:
                            results.append(text)

                    return " ".join(results)
                except Exception:
                    return default

            try:
                elem = elems[int(index)]
            except (IndexError, TypeError, ValueError):
                return default
        else:
            elem = soup_or_elem.select_one(selector)

    if not elem:
        return default

    if attr == "text":
        return elem.get_text(separator=" ", strip=True)
    elif attr == "html":
        return str(elem)
    else:
        # Check if elem is a Tag and has the attribute
        if hasattr(elem, "get"):
            val = elem.get(attr)
        else:
            val = None

        if val is None:
            return default
        if isinstance(val, list):
            return " ".join(val)
        return val


def extract_items_html(soup, selector):
    """Returns a list of BeautifulSoup elements matching the selector."""
    if not selector:
        return [soup]
    return soup.select(selector)
