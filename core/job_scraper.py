import requests
from bs4 import BeautifulSoup
import urllib.parse
import ssl
import re
from .logger import logger
from .extractor import extract_json, extract_html, extract_items_html
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
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
        """Main entry point for fetching jobs for a studio."""
        scraping = studio.get("scraping", {})
        strategy = scraping.get("strategy")
        careers_urls = studio.get("careers_url")

        if not isinstance(careers_urls, list):
            careers_urls = [careers_urls]

        all_jobs = []
        seen_links = set()

        for url in careers_urls:
            if not url:
                continue

            studio_for_url = studio.copy()
            studio_for_url["careers_url"] = url

            try:
                if strategy == "json":
                    jobs = self.fetch_json(studio_for_url)
                elif strategy == "html":
                    jobs = self.fetch_html(studio_for_url)
                elif strategy == "rss":
                    jobs = self.fetch_rss(studio_for_url)
                else:
                    logger.warning(f"No valid strategy for {studio.get('id')}: {strategy}")
                    continue
            except Exception as e:
                logger.error(f"Error fetching jobs from {url}: {e}")
                continue

            for job in jobs:
                title = job.get("title", "").strip()
                link = job.get("link", "").strip()

                # Normalize title and link for reliable matching
                t_key = title.lower()
                l_key = ""
                if link:
                    # Strip common tracking params and normalize
                    l_key = re.sub(r"[?&](utm_|portal|ref|source|jobid)=[^&]*", "", link).rstrip("?&").lower()

                # Per-studio deduplication: we skip if we've seen this exact title+link combo
                # OR if the unique link has been seen already.
                dup_key = (t_key, l_key)
                if dup_key in seen_links or (l_key and l_key in seen_links and l_key != url.lower()):
                    continue

                all_jobs.append(job)
                seen_links.add(dup_key)
                if l_key and l_key != url.lower():
                    seen_links.add(l_key)

        return all_jobs

    def _apply_mapping_logic(self, val, m):
        """Centralized logic for split, regex, prefix, and suffix."""
        if not val or not isinstance(m, dict):
            return val

        # 1. Split
        split_cfg = m.get("split")
        if split_cfg:
            sep = split_cfg.get("sep", ":")
            idx = split_cfg.get("index", 0)
            parts = val.split(sep)
            val = parts[idx].strip() if 0 <= idx < len(parts) else ""

        # 2. Regex
        regex = m.get("regex")
        if regex and val:
            match = re.search(regex, val)
            if match:
                val = match.group(1) if match.groups() else match.group(0)
            else:
                val = ""

        # 3. Prefix/Suffix
        prefix = m.get("prefix", "")
        suffix = m.get("suffix", "")
        if val:
            val = f"{prefix}{val}{suffix}"

        # 4. Default if empty
        if not val and "default" in m:
            val = m["default"]

        return val

    def _remove_location_from_title(self, title, location):
        """Removes the location from the title and cleans up orphaned separators like ' - - '."""
        if not title or not location:
            return title

        # 1. Basic removal of the full location string
        title = re.sub(re.escape(location), "", title, flags=re.I).strip()

        # 2. If it's a comma-separated location (like 'London, UK'), remove components
        if "," in location:
            for p in location.split(","):
                p_strip = p.strip()
                if p_strip:
                    title = re.sub(r"\b" + re.escape(p_strip) + r"\b", "", title, flags=re.I).strip()

        # 3. Collapse multiple separators (e.g. ' -  - ' -> ' - ')
        # This handles symbols like -, |, /, \, ·, •
        title = re.sub(r"\s*([ \-\|/\\·•])\s*([ \-\|/\\·•]\s*)+", r" \1 ", title)

        # 4. Remove empty brackets left behind
        title = re.sub(r"\(\s*\)|\[\s*\]|\{\s*\}", "", title).strip()

        # 5. Final cleanup from ends is handled by _clean_text later
        return title.strip()

    def _clean_text(self, text):
        """Cleans common HTML noise from extracted text."""
        if not text:
            return ""
        # Remove HTML tags if present
        if "<" in text and ">" in text:
            text = BeautifulSoup(text, "html.parser").get_text(strip=True)
        # Normalize whitespace
        text = " ".join(text.split())
        return text.strip("·•| -:").strip()

    def fetch_json(self, studio):
        careers_url = studio.get("careers_url")
        scraping = studio.get("scraping", {})

        # Request
        method = scraping.get("method", "GET").upper()
        params = scraping.get("params", {})
        payload = scraping.get("payload")
        headers = scraping.get("headers", {})

        if method == "POST":
            form_data = scraping.get("form_data")
            response = self.session.post(
                careers_url,
                data=form_data if form_data else None,
                json=payload if not form_data else None,
                params=params,
                headers=headers,
            )
        else:
            response = self.session.get(careers_url, params=params, headers=headers)

        response.raise_for_status()
        data = response.json()

        items = extract_json(data, scraping.get("path", ""), default=[])
        if not items:
            return []
        if not isinstance(items, list):
            items = [items]

        return self._parse_json_items(items, studio, careers_url)

    def _parse_json_items(self, items, studio, careers_url):
        scraping = studio.get("scraping", {})
        mapping = scraping.get("map", {})

        # Filter
        filter_cfg = scraping.get("filter")
        if filter_cfg:
            key, sw = filter_cfg.get("key"), filter_cfg.get("startswith")
            if key and sw:
                items = [it for it in items if str(extract_json(it, key, "")).startswith(sw)]

        jobs = []
        for item in items:

            def get_val(field_key, default=""):
                m = mapping.get(field_key)
                if not m:
                    return default

                # Support source="url" for direct URL inference
                if isinstance(m, dict) and m.get("source") == "url":
                    val = careers_url
                else:
                    path = m.get("path") if isinstance(m, dict) else m
                    val = str(extract_json(item, path, default) or default)

                return self._apply_mapping_logic(val, m)

            title = get_val("title", "Unknown")
            link = get_val("link", "")
            location = get_val("location", "")

            title = self._clean_text(title)

            # Support remove_location_from_title in JSON too
            if mapping.get("remove_location_from_title") and location:
                title = self._remove_location_from_title(title, location)
                title = self._clean_text(title)

            if link and not link.startswith("http"):
                base = studio.get("website") or careers_url
                link = urllib.parse.urljoin(base, link)

            jobs.append({"title": title, "link": link, "location": location})

        return jobs

    def fetch_html(self, studio):
        careers_url = studio.get("careers_url")
        scraping = studio.get("scraping", {})
        mapping = scraping.get("map", {})

        method = scraping.get("method", "GET").upper()
        params, payload, headers = scraping.get("params", {}), scraping.get("payload"), scraping.get("headers", {})

        if method == "POST":
            response = self.session.post(careers_url, json=payload, params=params, headers=headers)
        else:
            response = self.session.get(careers_url, params=params, headers=headers)

        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        container_sel = scraping.get("container")
        if not container_sel:
            return []

        # Items Extraction
        split_cfg = scraping.get("split_items")
        if split_cfg:
            container = soup.select_one(container_sel)
            if not container:
                return []
            text = str(container) if split_cfg.get("use_html") else container.get_text("\n")
            delim = split_cfg.get("delimiter", "<br>")
            items = [BeautifulSoup(p.strip(), "html.parser") for p in text.split(delim) if p.strip()]
        elif scraping.get("strategy_override") == "json_text":
            # Extract JSON from a script tag or text content
            text = ""
            regex = scraping.get("json_regex", r"const jobsData\s*=\s*(\[.*?\])\s*;?\n")
            target = soup.select_one(container_sel)
            if target:
                text = target.get_text()
            else:
                # Fallback: search all script tags for the pattern
                for s in soup.find_all("script"):
                    contents = s.get_text()
                    if re.search(regex, contents, re.DOTALL):
                        text = contents
                        break

            if not text:
                logger.error(f"Could not find JSON text matching {regex} in any script tag")
                return []

            match = re.search(regex, text, re.DOTALL)
            if not match:
                logger.warning(f"Could not find JSON matching {regex}")
                return []
            try:
                import json

                items = json.loads(match.group(1))
            except Exception as e:
                logger.error(f"Error parsing JSON: {e}")
                return []

            # Since items are now dicts from JSON, we use the JSON mapping logic
            return self._parse_json_items(items, studio, careers_url)
        else:
            items = extract_items_html(soup, container_sel)

        jobs = []

        for item in items:

            def get_val(field_key, default="", def_attr="text"):
                m = mapping.get(field_key)
                if m is None:
                    return default

                # Support source="url"
                if isinstance(m, dict) and m.get("source") == "url":
                    val = careers_url
                elif isinstance(m, dict) and "find_previous" in m:
                    node = item.find_previous(m["find_previous"])
                    return node.get_text(separator=" ", strip=True) if node else default
                else:
                    selector = m.get("selector") if isinstance(m, dict) else m
                    attr = m.get("attr", def_attr) if isinstance(m, dict) else def_attr
                    val = extract_html(
                        item,
                        selector,
                        attr=attr,
                        default=default,
                        index=m.get("index") if isinstance(m, dict) else None,
                    )

                return self._apply_mapping_logic(str(val or default), m)

            title = get_val("title", "Unknown")
            if title.lower() in ["view job", "details", "read more", "apply", "careers", "unknown"]:
                continue

            link = get_val("link", "", "href")
            location = self._clean_text(get_val("location", ""))

            title = self._clean_text(title)

            if mapping.get("remove_location_from_title") and location:
                title = self._remove_location_from_title(title, location)
                title = self._clean_text(title)

            # Extra Link
            extra_link = ""
            extra_cfg = mapping.get("extra_link")
            if isinstance(extra_cfg, dict):
                raw = get_val("extra_link", "", "html")
                match = re.search(extra_cfg.get("regex_link", ""), raw)
                if match:
                    extra_link = match.group(1) if match.groups() else match.group(0)

            if not link:
                link = careers_url
            elif not str(link).startswith("http"):
                link = urllib.parse.urljoin(studio.get("website") or careers_url, str(link))

            jobs.append({"title": title, "link": link, "location": location, "extra_link": extra_link})

        return jobs

    def fetch_rss(self, studio):
        rss_url = studio.get("careers_url") or studio.get("website")
        scraping = studio.get("scraping", {})
        mapping = scraping.get("map", {})

        response = self.session.get(rss_url)
        response.raise_for_status()

        # Always use html.parser to avoid requiring the 'lxml' or 'xml' feature of BS4
        soup = BeautifulSoup(response.text, "html.parser")

        items = soup.select(scraping.get("container") or "item") or soup.find_all(["item", "entry"])
        jobs = []

        for item in items:

            def get_val(field_key, def_tag):
                m = mapping.get(field_key)
                if not m:
                    node = item.find(def_tag) or (item.find("guid") if def_tag == "link" else None)
                    return node.get_text(strip=True) if node else ""

                val = ""
                # Support source="url"
                if isinstance(m, dict) and m.get("source") == "url":
                    val = rss_url
                elif isinstance(m, dict):
                    sel = m.get("selector") or m.get("path") or def_tag
                    node = item.find(sel) or (item.find("guid") if def_tag == "link" else None)
                    if node:
                        val = node.get_text(strip=True) if m.get("attr", "text") == "text" else node.get(m.get("attr"))
                    else:
                        val = extract_html(item, sel, attr=m.get("attr", "text"), default="")
                    return self._apply_mapping_logic(str(val or ""), m)

                node = item.find(m) or (item.find("guid") if m == "link" else None)
                if node:
                    return node.get_text(strip=True)
                return str(extract_html(item, m, attr="text", default=""))

            title = self._clean_text(get_val("title", "title") or "Unknown")
            link = get_val("link", "link")
            location = self._clean_text(get_val("location", "description"))

            if mapping.get("remove_location_from_title") and location:
                title = self._remove_location_from_title(title, location)
                title = self._clean_text(title)

            # Fallback for some common RSS link patterns
            if not link or "application.php" not in link:
                match = re.search(r'https?://[^\s<>"]+application\.php[^\s<>"]+', str(item))
                if match:
                    link = match.group(0)

            # Extra Link
            extra_link = ""
            extra_cfg = mapping.get("extra_link")
            if isinstance(extra_cfg, dict):
                raw = get_val("extra_link", "description")
                match = re.search(extra_cfg.get("regex_link", ""), raw)
                if match:
                    extra_link = match.group(1) if match.groups() else match.group(0)

            if link and not link.startswith("http"):
                link = urllib.parse.urljoin(studio.get("website") or rss_url, link)

            jobs.append({"title": title, "link": link, "location": location, "extra_link": extra_link})

        return jobs
