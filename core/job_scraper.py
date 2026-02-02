import requests
from bs4 import BeautifulSoup
import urllib.parse
import ssl
import re
from core.logger import logger
from core.extractor import extract_json, extract_html, extract_items_html
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Create an unverified SSL context for all requests calls to avoid CERT_VERIFY_FAILED
ssl._create_default_https_context = ssl._create_unverified_context


class JobScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
            }
        )

    def fetch_jobs(self, studio):
        scraping = studio.get("scraping", {})
        strategy = scraping.get("strategy")

        if strategy == "json":
            try:
                return self.fetch_json(studio)
            except Exception as e:
                logger.error(f"Error fetching {studio.get('id')} (JSON): {e}")
                return []
        elif strategy == "html":
            try:
                return self.fetch_html(studio)
            except Exception as e:
                logger.error(f"Error fetching {studio.get('id')} (HTML): {e}")
                return []
        elif strategy == "rss":
            try:
                return self.fetch_rss(studio)
            except Exception as e:
                logger.error(f"Error fetching {studio.get('id')} (RSS): {e}")
                return []
        else:
            logger.warning(f"No valid strategy for {studio.get('id')}: {strategy}")
            return []

    def fetch_json(self, studio):
        careers_url = studio.get("careers_url")
        scraping = studio.get("scraping", {})

        method = scraping.get("method", "GET").upper()
        params = scraping.get("params", {})
        payload = scraping.get("payload")
        headers = scraping.get("headers", {})

        if method == "POST":
            form_data = scraping.get("form_data")
            if form_data:
                response = self.session.post(careers_url, data=form_data, params=params, headers=headers)
            else:
                response = self.session.post(careers_url, json=payload, params=params, headers=headers)
        else:
            response = self.session.get(careers_url, params=params, headers=headers)

        response.raise_for_status()
        data = response.json()

        items = extract_json(data, scraping.get("path", ""), default=[])
        if not items:
            return []
        if not isinstance(items, list):
            items = [items]

        # Filter
        filter_cfg = scraping.get("filter")
        if filter_cfg:
            key = filter_cfg.get("key")
            sw = filter_cfg.get("startswith")
            if key and sw:
                items = [it for it in items if str(extract_json(it, key, "")).startswith(sw)]

        mapping = scraping.get("map", {})
        jobs = []
        for item in items:

            def get_val(m, default=""):
                if isinstance(m, dict):
                    path = m.get("path")
                    prefix = m.get("prefix", "")
                    suffix = m.get("suffix", "")
                    val = extract_json(item, path, default)
                    val = str(val if val is not None else default)

                    split_cfg = m.get("split")
                    if split_cfg and val:
                        sep = split_cfg.get("sep", ":")
                        idx = split_cfg.get("index", 0)
                        parts = val.split(sep)
                        if 0 <= idx < len(parts):
                            val = parts[idx].strip()
                        else:
                            val = ""

                    regex = m.get("regex")
                    if regex and val:
                        match = re.search(regex, val)
                        if match:
                            val = match.group(0)

                    if val and val != default:
                        return f"{prefix}{val}{suffix}"
                    return val

                val = extract_json(item, m, default)
                return str(val if val is not None else default)

            title = get_val(mapping.get("title", "title"), "Unknown")
            link = get_val(mapping.get("link", "link"), "")
            location = get_val(mapping.get("location", "location"), "")

            # Cleanup
            if title:
                title = BeautifulSoup(title, "html.parser").get_text(strip=True)
            if location:
                location = BeautifulSoup(location, "html.parser").get_text(strip=True)

            if link and not link.startswith("http"):
                base = studio.get("website") or careers_url
                link = urllib.parse.urljoin(base, link)

            jobs.append({"title": title, "link": link, "location": location})

        return jobs

    def fetch_html(self, studio):
        careers_url = studio.get("careers_url")
        scraping = studio.get("scraping", {})

        method = scraping.get("method", "GET").upper()
        params = scraping.get("params", {})
        payload = scraping.get("payload")
        headers = scraping.get("headers", {})

        if method == "POST":
            response = self.session.post(careers_url, json=payload, params=params, headers=headers)
        else:
            response = self.session.get(careers_url, params=params, headers=headers)

        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        container_sel = scraping.get("container")
        if not container_sel:
            return []

        # Check if we should split the container text into multiple items
        split_items_cfg = scraping.get("split_items")
        if split_items_cfg:
            container = soup.select_one(container_sel)
            if not container:
                return []

            # Use html to preserve <br> tags if delimiter is <br>
            text = str(container) if split_items_cfg.get("use_html") else container.get_text("\n")
            delim = split_items_cfg.get("delimiter", "<br>")

            # Split and clean
            raw_parts = [p.strip() for p in text.split(delim) if p.strip()]

            # Convert parts back to soup snippets for mapping
            items = [BeautifulSoup(p, "html.parser") for p in raw_parts]
        else:
            items = extract_items_html(soup, container_sel)

        mapping = scraping.get("map", {})
        title_map = mapping.get("title", "title")
        link_map = mapping.get("link", "a")
        loc_map = mapping.get("location")

        jobs = []
        seen_links = set()

        for item in items:

            def get_val(m, def_attr="text"):
                if m is None or m == "":
                    # If selector is empty, we still result in a string
                    if m == "":
                        # Special case: if mapping is empty string, extract from element itself
                        val = extract_html(item, "", attr=def_attr, default="")
                        return str(val if val is not None else "")
                    return ""

                if isinstance(m, dict):
                    if "find_previous" in m:
                        node = item.find_previous(m["find_previous"])
                        if node:
                            if m.get("attr") == "html":
                                return str(node)
                            return node.get_text(separator=" ", strip=True)
                        return ""

                    val = extract_html(
                        item,
                        m.get("selector"),
                        attr=m.get("attr", def_attr),
                        default="",
                        index=m.get("index"),
                    )
                    val = str(val if val is not None else "")

                    split_cfg = m.get("split")
                    if split_cfg and val:
                        sep = split_cfg.get("sep", ":")
                        idx = split_cfg.get("index", 0)
                        parts = val.split(sep)
                        if 0 <= idx < len(parts):
                            val = parts[idx].strip()
                        else:
                            val = ""

                    regex = m.get("regex")
                    if regex and val:
                        match = re.search(regex, val)
                        if match:
                            val = match.group(0)
                        else:
                            val = ""
                    return val

                val = extract_html(item, m, attr=def_attr, default="")
                return str(val if val is not None else "")

            title = get_val(title_map, "text") or "Unknown"
            title = title.rstrip(":")

            # Skip generic labels
            if title.lower() in ["view job", "details", "read more", "apply", "careers", "open positions"]:
                continue

            link = get_val(link_map, "href")
            location = get_val(loc_map, "text")
            if location:
                location = " ".join(location.split())
                location = location.strip("·•| ").strip()
                # Remove spaces before commas/periods
                location = re.sub(r"\s+([,.])", r"\1", location)

                # Optional: Remove location from title if it's embedded
                if mapping.get("remove_location_from_title") and title:
                    # Try removing the full location first
                    pattern = re.compile(re.escape(location), re.IGNORECASE)
                    title = pattern.sub("", title)

                    # Also try removing individual parts (for "London, UK" cases where only "London" is in title)
                    if "," in location:
                        parts = [p.strip() for p in location.split(",") if len(p.strip()) > 2]
                        for p in parts:
                            # Use word boundaries to avoid partial word removal
                            p_pattern = re.compile(r"\b" + re.escape(p) + r"\b", re.IGNORECASE)
                            title = p_pattern.sub("", title)

                    # Remove empty parens/brackets that might be left over
                    while True:
                        new_title = re.sub(r"\(\s*\)|\[\s*\]", "", title)
                        if new_title == title:
                            break
                        title = new_title

            if title:
                # Cleanup separators that might be left hanging
                title = title.strip("·•| -").strip()
                # Remove double separators
                title = re.sub(r"\s*[-|•·]\s*[-|•·]\s*", " - ", title)
                # Collapse extra spaces
                title = " ".join(title.split())

            extra_map = mapping.get("extra_link")
            extra_link = ""
            if extra_map and isinstance(extra_map, dict):
                # We need to process description as raw HTML to extract link
                raw_desc = get_val(extra_map, "html")
                if extra_map.get("regex_link"):
                    m = re.search(extra_map["regex_link"], raw_desc)
                    if m:
                        extra_link = m.group(1) if m.groups() else m.group(0)

            if not link:
                # If no link found, fallback to careers URL to at least show the job exists
                link = careers_url
            else:
                link = str(link)

            if not link.startswith("http"):
                link = urllib.parse.urljoin(studio.get("website") or careers_url, link)

            if link in seen_links and link != careers_url:
                continue

            if link != careers_url:
                seen_links.add(link)

            jobs.append({"title": title, "link": link, "location": location, "extra_link": extra_link})

        return jobs

    def fetch_rss(self, studio):
        # Prefer careers_url for RSS feeds if it's specified
        rss_url = studio.get("careers_url") or studio.get("website")
        scraping = studio.get("scraping", {})

        response = self.session.get(rss_url)
        response.raise_for_status()

        # Use 'xml' parser if available for better RSS handling
        try:
            soup = BeautifulSoup(response.text, "xml")
        except Exception:
            soup = BeautifulSoup(response.text, "html.parser")

        # In RSS, items are usually <item> tags
        container_sel = scraping.get("container") or "item"
        items = soup.select(container_sel)
        if not items:
            # Fallback for some feed types
            items = soup.find_all("item") or soup.find_all("entry")

        mapping = scraping.get("map", {})
        jobs = []
        for item in items:

            def get_val(m, def_tag):
                if not m:
                    # If no mapping, try the default tag
                    node = item.find(def_tag)
                    if not node and def_tag == "link":
                        node = item.find("guid")

                    if node:
                        text = node.get_text(strip=True)
                        if not text and def_tag == "link":
                            # If <link> is empty (common in html.parser), check next sibling
                            nxt = node.next_sibling
                            if nxt and isinstance(nxt, str):
                                text = nxt.strip()
                        return text
                    return ""

                if isinstance(m, dict):
                    sel = m.get("selector") or m.get("path") or def_tag
                    # Try find first as it's more reliable for simple RSS tags
                    node = item.find(sel)
                    if not node and (sel == "link" or def_tag == "link"):
                        node = item.find("guid")

                    if node:
                        val = node.get_text(strip=True) if m.get("attr", "text") == "text" else node.get(m.get("attr"))
                        if not val and (sel == "link" or def_tag == "link"):
                            nxt = node.next_sibling
                            if nxt and isinstance(nxt, str):
                                val = nxt.strip()
                    else:
                        # Fallback to selector
                        val = extract_html(item, sel, attr=m.get("attr", "text"), default="")

                    val = str(val if val is not None else "")

                    split_cfg = m.get("split")
                    if split_cfg and val:
                        sep = split_cfg.get("sep", ":")
                        idx = split_cfg.get("index", 0)
                        parts = val.split(sep)
                        if 0 <= idx < len(parts):
                            val = parts[idx].strip()
                        else:
                            val = ""

                    regex = m.get("regex")
                    if regex and val:
                        match = re.search(regex, val)
                        if match:
                            val = match.group(0)
                    return val

                # String mapping
                node = item.find(m)
                if not node and m == "link":
                    node = item.find("guid")

                if node:
                    text = node.get_text(strip=True)
                    if not text and m == "link":
                        nxt = node.next_sibling
                        if nxt and isinstance(nxt, str):
                            text = nxt.strip()
                    return text

                # Fallback for link mapping
                if m == "link" or def_tag == "link":
                    text = str(item)
                    # Look for URL inside <link>...</link> or following <link/>
                    match = re.search(r"<link[^>]*>(.*?)</link>", text, re.I | re.S)
                    if match:
                        return BeautifulSoup(match.group(1), "html.parser").get_text(strip=True)

                    match = re.search(r'https?://[^\s<>"]+application\.php[^\s<>"]+', text)
                    if not match:
                        match = re.search(r'https?://[^\s<>"]+', text)
                    if match:
                        return match.group(0)

                return str(extract_html(item, m, attr="text", default=""))

            title = get_val(mapping.get("title"), "title") or "Unknown"
            link = get_val(mapping.get("link"), "link")
            location = get_val(mapping.get("location"), "description")

            if link and not link.startswith("http"):
                base = studio.get("website") or rss_url
                link = urllib.parse.urljoin(base, link)

            jobs.append({"title": title, "link": link, "location": location})

        return jobs
