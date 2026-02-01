import requests
from bs4 import BeautifulSoup
import urllib.parse
import ssl
from .logger import logger
from .extractor import extract_json, extract_html, extract_items_html
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
                    if val and val != default:
                        return f"{prefix}{val}{suffix}"
                    return str(val if val is not None else default)
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
        url = studio.get("careers_url")
        scraping = studio.get("scraping", {})

        response = self.session.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        container_sel = scraping.get("container")
        if not container_sel:
            return []

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

                    val = extract_html(item, m.get("selector"), attr=m.get("attr", def_attr), default="")
                    return str(val if val is not None else "")

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

            if not link:
                # If no link found, fallback to careers URL to at least show the job exists
                link = url
            else:
                link = str(link)

            if not link.startswith("http"):
                link = urllib.parse.urljoin(studio.get("website") or url, link)

            if link in seen_links and link != url:
                continue

            if link != url:
                seen_links.add(link)

            jobs.append({"title": title, "link": link, "location": location})

        return jobs
