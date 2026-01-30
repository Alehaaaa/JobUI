import requests
from bs4 import BeautifulSoup
import json
import urllib.parse
import ssl

# Create an unverified SSL context for all requests calls to avoid CERT_VERIFY_FAILED
ssl._create_default_https_context = ssl._create_unverified_context


class JobScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
            }
        )

    def fetch_jobs(self, studio):
        strategy = studio.get("scraping_strategy")
        if not strategy:
            return []

        method_name = f"fetch_{strategy}"
        if hasattr(self, method_name):
            try:
                return getattr(self, method_name)(studio)
            except Exception as e:
                print(f"Error fetching jobs for {studio.get('name')}: {e}")
                return []
        else:
            print(f"Strategy {strategy} not implemented")
            return []

    # --- Strategy Implementations ---

    def fetch_netflix_json(self, studio):
        careers_url = studio.get("careers_url")
        # studio["careers_url"] is base API url
        # Logic from Swift:
        # params: domain=netflix.com, num=10, sort_by=relevance, Teams=[...]

        params = {
            "domain": "netflix.com",
            "num": 100,  # Fetch more at once instead of pagination for now
            "sort_by": "relevance",
            "Teams": [
                "Animation",
                "Feature Animation - Art",
                "Feature Animation - Editorial + Post",
                "Feature Animation - Production Management",
                "Feature Animation - Story",
                "Feature Animation",
            ],
        }

        response = self.session.get(careers_url, params=params)
        response.raise_for_status()
        data = response.json()

        jobs = []
        for pos in data.get("positions", []):
            loc = pos.get("location")
            location = loc if loc else ""
            title = pos.get("name", "Unknown")
            link = pos.get("canonicalPositionUrl")
            jobs.append({"title": title, "link": link, "location": location})

        return jobs

    def fetch_pixar_json(self, studio):
        # Workday JSON POST
        # URL: studio.get("careers_url")

        url = studio.get("careers_url")
        payload = {"appliedFacets": {}, "limit": 20, "searchText": ""}
        headers = {"Content-Type": "application/json"}

        response = self.session.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

        website_base = studio.get("website")

        jobs = []
        for post in data.get("jobPostings", []):
            title = post.get("title")
            external_path = post.get("externalPath")
            link = f"{website_base}{external_path}"
            jobs.append({"title": title, "link": link, "location": ""})

        return jobs

    def fetch_dreamworks_json(self, studio):
        url = studio.get("careers_url")
        try:
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()  # List of ResponseData
        except json.JSONDecodeError:
            return []

        jobs = []
        # Swift: response.first?.rows
        if data and isinstance(data, list) and len(data) > 0:
            rows = data[0].get("rows", [])
            for row in rows:
                title = row.get("title")
                # title might contain HTML entities, BS4 can clean
                title = BeautifulSoup(title, "html.parser").get_text()
                link = row.get("field_detailurl")
                location = row.get("field_location", "")
                location = BeautifulSoup(location, "html.parser").get_text()

                jobs.append({"title": title, "link": link, "location": location})

        return jobs

    def fetch_disney_html(self, studio):
        url = studio.get("careers_url")
        response = self.session.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        jobs = []
        # tr:has(span.job-location)
        for row in soup.select("tr"):
            if not row.select_one("span.job-location"):
                continue

            title_elem = row.select_one("h2")
            link_elem = row.select_one("a")
            loc_elem = row.select_one("span.job-location")

            if title_elem and link_elem:
                title = title_elem.get_text(strip=True)
                href = link_elem.get("href")
                location = loc_elem.get_text(strip=True) if loc_elem else ""

                # Resolve relative URL
                full_link = urllib.parse.urljoin(studio.get("website"), href)
                jobs.append({"title": title, "link": full_link, "location": location})

        return jobs

    def fetch_lever_json(self, studio):
        url = studio.get("careers_url")
        response = self.session.get(url)
        data = response.json()

        jobs = []
        for post in data:
            title = post.get("text")
            link = post.get("hostedUrl")
            loc = post.get("categories", {}).get("location", "")
            jobs.append({"title": title, "link": link, "location": loc})
        return jobs

    def fetch_bamboohr_json(self, studio):
        base_url = studio.get("careers_url")
        url = f"{base_url}/careers/list"
        response = self.session.get(url)
        data = response.json()

        jobs = []
        result = data.get("result", [])
        for post in result:
            title = post.get("jobOpeningName")
            pid = post.get("id")

            loc_obj = post.get("location", {})
            city = loc_obj.get("city") or ""
            state = loc_obj.get("state") or ""
            location = f"{city}, {state}".strip(", ")

            # Link construction depends on studio usually
            # Swift: studio.website + "careers/" + id
            # Studio website logic seems variable, let's use base_url if possible or construct
            # The swift code used studio.website.appendingPathComponent("careers/\($0.id)")
            # Checking studio json, flyingbark website is empty? No, let's assume valid website in studio data.
            website = studio.get("website") or base_url
            link = f"{website}/careers/{pid}"

            jobs.append({"title": title, "link": link, "location": location})

        return jobs

    def fetch_smartrecruiters_json(self, studio):
        url = studio.get("careers_url")
        response = self.session.get(url)
        data = response.json()

        content = data.get("content", [])
        jobs = []
        website = studio.get("website")

        for post in content:
            title = post.get("name")
            pid = post.get("id")
            loc = post.get("location", {}).get("fullLocation", "")

            # Swift: studio.website.appendingPathComponent($0.id)
            link = f"{website}/{pid}"
            jobs.append({"title": title, "link": link, "location": loc})

        return jobs

    def fetch_dneg_html(self, studio):
        url = studio.get("careers_url")
        response = self.session.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        jobs = []
        for row in soup.select("li.mb1"):
            title_elem = row.select_one("p")
            link_elem = row.select_one("a")
            loc_elem = row.select_one("div.jv-job-list-location")

            if title_elem and link_elem:
                title = title_elem.get_text(strip=True)
                href = link_elem.get("href")

                location = ""
                if loc_elem:
                    location = " ".join(loc_elem.get_text().split())

                full_link = f"https://jobs.jobvite.com{href}"
                jobs.append({"title": title, "link": full_link, "location": location})

        return jobs

    def fetch_greenhouse_html(self, studio):
        url = studio.get("careers_url")
        response = self.session.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        jobs = []
        # tr.job-post
        for row in soup.select("tr.job-post"):
            title_elem = row.select_one("p")  # Or sometimes 'a' directly? Swift says 'p'
            # Wait, Swift says title is 'p', link is 'a'.
            # In standard Greenhouse boards, the structure is usually <td class="cell"> <a href="...">Title</a> </td>
            # But let's trust the Swift selectors: p, a, p.body__secondary

            # If the Swift selector is specific to a custom greenhouse board, it might fail on others.
            # Standard Greenhouse:
            # <section class="level-0"> ... <div class="opening"> <a href="...">Title</a> <span class="location">...</span>

            # Swift implementation:
            # titleElement = row.select("p").first()
            # linkElement = row.select("a").first()

            if not title_elem:
                # Try finding 'a' as title if p missing
                link_elem = row.select_one("a")
                if link_elem:
                    title = link_elem.get_text(strip=True)
                    href = link_elem.get("href")
                    loc_elem = row.select_one("span.location")
                    location = loc_elem.get_text(strip=True) if loc_elem else ""

                    full_link = urllib.parse.urljoin("https://boards.greenhouse.io", href)
                    if not href.startswith("http"):
                        # Greenhouse usually absolute but just in case
                        pass
                    else:
                        full_link = href

                    jobs.append({"title": title, "link": full_link, "location": location})
                continue

            # Following Swift exactly
            link_elem = row.select_one("a")
            loc_elem = row.select_one("p.body__secondary")

            if title_elem and link_elem:
                title = title_elem.get_text(strip=True)
                href = link_elem.get("href")
                location = loc_elem.get_text(strip=True) if loc_elem else ""

                # Check if href is relative or absolute
                full_link = href
                if not href.startswith("http"):
                    # Basic greenhouse
                    full_link = urllib.parse.urljoin(url, href)

                jobs.append({"title": title, "link": full_link, "location": location})

        return jobs

    def fetch_ranchito_html(self, studio):
        url = studio.get("careers_url")
        response = self.session.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        jobs = []
        for li in soup.select("li"):
            # Swift: li:has(h5.post-date)
            # BS4 doesn't support :has comfortably in all versions, manual check
            if not li.select_one("h5.post-date"):
                continue

            h2 = li.select_one("h2")
            a = li.select_one("a")
            h5 = li.select_one("h5.post-date")

            if h2 and a:
                title = h2.get_text(strip=True)
                href = a.get("href")
                location = h5.get_text(strip=True) if h5 else ""

                link = urllib.parse.urljoin(studio.get("website"), href)
                jobs.append({"title": title, "link": link, "location": location})

        return jobs

    def fetch_mikros_html(self, studio):
        # API JSON approach from Swift
        url = studio.get("careers_url")
        response = self.session.get(url)
        data = response.json()

        content = data.get("content", [])
        jobs = []
        website = studio.get("website")

        for post in content:
            label = post.get("department", {}).get("label", "")
            if not label or not label.startswith("Mikros Animation"):
                continue

            title = post.get("name")
            pid = post.get("id")
            loc = post.get("location", {}).get("fullLocation", "")

            link = f"{website}/{pid}"  # appendingPathComponent might add slash
            jobs.append({"title": title, "link": link, "location": loc})

        return jobs

    def fetch_fortiche_html(self, studio):
        url = studio.get("careers_url")
        response = self.session.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        jobs = []
        for elem in soup.select(".jet-engine-listing-overlay-wrap"):
            h3 = elem.select_one("h3")
            if not h3:
                continue

            title = h3.get_text(strip=True)
            link = elem.get("data-url")

            jobs.append({"title": title, "link": link, "location": ""})

        return jobs

    def fetch_steamroller_html(self, studio):
        url = studio.get("careers_url")
        response = self.session.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        jobs = []
        for elem in soup.select("div.css-aapqz6"):
            a = elem.select_one("a[href]")
            # location is span[data-icon=LOCATION_OUTLINE] + p
            # finding adjacent p
            loc_span = elem.select_one("span[data-icon='LOCATION_OUTLINE']")
            loc_p = loc_span.find_next("p") if loc_span else None

            if a:
                title = a.get_text(strip=True)
                href = a.get("href")
                location = loc_p.get_text(strip=True) if loc_p else ""

                if "/jobs/" in href:
                    """link = urllib.parse.urljoin(
                        studio.get("website"), href
                    )  # actually relative to website? Swift says so
                    # But website might be different domain. Swift says relative to studio.website
                    # However in studios.json steamroller website is missing?
                    # The URL in json is "https://ats.rippling.com/steamroller-animation/jobs" for careers
                    # The link is likely relative to that domain."""

                    full_link = urllib.parse.urljoin("https://ats.rippling.com", href)
                    jobs.append({"title": title, "link": full_link, "location": location})

        return jobs

    def fetch_framestore_html(self, studio):
        url = studio.get("careers_url")
        response = self.session.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        jobs = []
        seen = set()

        # Swift: select("div").filter childAnchor href^=/o/
        # Simplified: select a[href^='/o/'] directly

        for a in soup.select("a[href^='/o/']"):
            href = a.get("href")
            if href in seen:
                continue

            title = a.get_text(strip=True)
            if title.lower() == "view job":
                continue

            seen.add(href)

            # Location finding: container row
            # Swift assumes a specific structure
            row = a.find_parent("div")  # Approximate parent call

            location = ""
            if row:
                city = row.select_one(".custom-css-style-job-location-city")
                country = row.select_one(".custom-css-style-job-location-country")
                if city and country:
                    location = f"{city.get_text(strip=True)}, {country.get_text(strip=True)}"

            full_link = urllib.parse.urljoin(url, href)
            jobs.append({"title": title, "link": full_link, "location": location})

        return jobs

    def fetch_giant_html(self, studio):
        url = studio.get("careers_url")
        response = self.session.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        jobs = []
        for elem in soup.select(".g-careers .row .col-12"):
            h4 = elem.select_one("h4")
            span = elem.select_one("span")
            a = elem.select_one("a")

            if h4 and span and a:
                title = h4.get_text(strip=True)
                location = span.get_text(strip=True)
                href = a.get("href")

                jobs.append({"title": title, "link": href, "location": location})

        return jobs

    def fetch_skydance_html(self, studio):
        url = studio.get("careers_url")
        response = self.session.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        jobs = []
        # div[id^=skydance_animation].mb-60
        for section in soup.select("div[id^='skydance_animation'].mb-60"):
            for element in section.select(".mb-40"):
                title_elem = element.select_one(".treatment-title-small")
                link_elem = element.select_one("a")
                loc_elem = element.select_one(".treatment-button")

                if title_elem and link_elem:
                    title = title_elem.get_text(strip=True)
                    href = link_elem.get("href")
                    location = loc_elem.get_text(strip=True) if loc_elem else ""

                    full_link = urllib.parse.urljoin(studio.get("website"), href)
                    jobs.append({"title": title, "link": full_link, "location": location})

        return jobs

    def fetch_illusorium_html(self, studio):
        url = studio.get("careers_url")
        response = self.session.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        jobs = []
        seen = set()

        for container in soup.select("div.row-container"):
            btn_container = container.select_one("span.btn-container")
            if not btn_container:
                continue

            a = btn_container.select_one("a[href]")
            if not a:
                continue

            href = a.get("href")
            if "/job_posting/" not in href:
                continue

            if href in seen:
                continue
            seen.add(href)

            # Title finding
            text_col = container.select_one("div.uncode_text_column.text-lead")
            title = "Title not found"
            if text_col:
                h4 = text_col.select_one("h4")
                if h4:
                    title = h4.get_text(strip=True)
                else:
                    p = text_col.select_one("p")
                    if p:
                        title = p.get_text(strip=True)

            full_link = urllib.parse.urljoin(studio.get("website"), href)
            jobs.append({"title": title, "link": full_link, "location": ""})

        return jobs

    def fetch_littlezoo_html(self, studio):
        url = studio.get("careers_url")
        try:
            response = self.session.get(url)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Error fetching Little Zoo: {e}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        jobs = []

        # Site appears to be Squarespace or similar.
        # Often jobs are headers (h1, h2, h3) or links in a text block.
        # Strategy: Search for typical "Artist", "Director", "Generalist" keywords
        # or structure: <h3>Job Title</h3> <p>Description/Link</p>

        # Searching for links that look like potential job detail pages is rare on single-pagers.
        # Little Zoo often lists positions on the main careers page.

        # Heuristic 1: Look for H tags that might be job titles
        # and see if there is a 'mailto' or 'apply' text nearby?

        # Simplified: iterate all headers or bold text?
        # Let's try to capture list items or headers followed by text.

        # Specific to littlezoo website structure (assumed generic):
        # Often <div class="sqs-block-content"><h3 ...>TITLE</h3> ... </div>

        for h3 in soup.select("h3"):
            text = h3.get_text(strip=True)
            if not text:
                continue

            # Filter non-job headers
            if text.lower() in ["careers", "open positions", "jobs", "apply"]:
                continue

            # Assume this is a job title
            title = text
            location = "Orlando, FL"  # Known location

            # Link? Usually mailto on this site, or just text.
            # If no link, we link to careers page.
            link = url

            # Check if wrapped in A or has A nearby
            a = h3.find_parent("a") or h3.find("a")
            if a:
                href = a.get("href")
                if href:
                    link = urllib.parse.urljoin(url, href)

            jobs.append({"title": title, "link": link, "location": location})

        return jobs
