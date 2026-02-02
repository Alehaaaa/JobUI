import contextlib
import datetime
import time
import ssl
import json

try:
    import urllib.request
    from urllib.request import urlopen
    from urllib.error import HTTPError
except ImportError:
    from urllib2 import urlopen, HTTPError

try:
    from ..core.logger import logger
except ImportError:
    logger = None


def check_remote_version():
    """
    Checks for updates by comparing local version with remote VERSION file.
    Returns: (remote_version, last_modified_date_str)
    """
    remote_url = "https://raw.githubusercontent.com/Alehaaaa/JobUI/main/VERSION"
    api_url = "https://api.github.com/repos/Alehaaaa/JobUI/commits?path=VERSION&per_page=1"

    remote_ver = None
    last_modified = None

    try:
        context = ssl._create_unverified_context()
        with contextlib.closing(urlopen(remote_url, timeout=5, context=context)) as response:
            if response.getcode() == 200:
                last_modified = response.info().get("Last-Modified")
                content = response.read()
                try:
                    remote_ver = content.decode("utf-8").strip()
                except UnicodeDecodeError:
                    remote_ver = content.decode("utf-16").strip()

        if not last_modified and remote_ver:
            try:
                req_headers = {"User-Agent": "JobUI-Updater"}
                if hasattr(urllib, "request"):  # Python 3
                    req = urllib.request.Request(api_url, headers=req_headers)
                else:  # Python 2
                    import urllib2

                    req = urllib2.Request(api_url, headers=req_headers)

                with contextlib.closing(urlopen(req, timeout=5, context=context)) as api_res:
                    if api_res.getcode() == 200:
                        commits = json.loads(api_res.read().decode("utf-8"))
                        if commits and isinstance(commits, list):
                            last_modified = commits[0].get("commit", {}).get("committer", {}).get("date")
            except Exception as e:
                if logger:
                    logger.debug("Failed to fetch date from GitHub API: {}".format(e))

        return remote_ver, last_modified

    except HTTPError as e:
        if e.code != 404:
            if logger:
                logger.warning("Update check failed for {}: {}".format(remote_url, e))
    except Exception as e:
        if logger:
            logger.warning("Failed to check for updates: {}".format(e))

    return None, None


def format_relative_time(date_str):
    """
    Converts a date string (HTTP or ISO format) to a relative string (e.g., '3 days ago').
    """
    if not date_str:
        return ""

    try:
        dt = None

        if "T" in date_str and "Z" in date_str:
            try:
                clean_iso = date_str.replace("T", " ").replace("Z", "")
                t = time.strptime(clean_iso, "%Y-%m-%d %H:%M:%S")
                dt = datetime.datetime(*t[:6])
            except ValueError:
                pass

        if not dt:
            try:
                clean_date = date_str.replace(" GMT", "")
                clean_date = clean_date.split(" (")[0]
                t = time.strptime(clean_date, "%a, %d %b %Y %H:%M:%S")
                dt = datetime.datetime(*t[:6])
            except ValueError:
                pass

        if not dt:
            return date_str

        now = datetime.datetime.utcnow()
        diff = now - dt

        seconds = diff.total_seconds()
        if seconds < 0:  # Future?
            return "just now"
        if seconds < 60:
            return "just now"
        if seconds < 3600:
            minutes = int(seconds / 60)
            return "{} min{} ago".format(minutes, "s" if minutes > 1 else "")
        if seconds < 86400:
            hours = int(seconds / 3600)
            return "{} hour{} ago".format(hours, "s" if hours > 1 else "")
        if seconds < 2592000:  # 30 days
            days = int(seconds / 86400)
            return "{} day{} ago".format(days, "s" if days > 1 else "")
        if seconds < 31536000:  # 365 days
            months = int(seconds / 2592000)
            return "{} month{} ago".format(months, "s" if months > 1 else "")

        years = int(seconds / 31536000)
        return "{} year{} ago".format(years, "s" if years > 1 else "")

    except Exception as e:
        if logger:
            logger.debug("Relative time conversion failed: {}".format(e))
        return date_str


if __name__ == "__main__":
    print(check_remote_version())
