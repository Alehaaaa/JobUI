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


def extract_json(data: Any, path: str, default: Any = None) -> Any:
    """
    Extract values from nested dict/list structures using a simple path string.
    Examples: "items[*].id", "data.results[0].name"
    """
    if not path:
        return data

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


def extract_html(soup_or_elem, selector, attr="text", default=None):
    """
    Extracts data from a BeautifulSoup object or Tag using CSS selectors.
    """
    if not selector:
        elem = soup_or_elem
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
