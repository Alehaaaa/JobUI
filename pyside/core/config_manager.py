import json
import os
import urllib.request
import ssl
from PySide2 import QtCore, QtGui


class LogoWorker(QtCore.QThread):
    logo_downloaded = QtCore.Signal(str)  # studio_id
    finished = QtCore.Signal()

    def __init__(self, studios, logos_dir, parent=None):
        super(LogoWorker, self).__init__(parent)
        self.studios = studios
        self.logos_dir = logos_dir
        self._is_running = True

    def run(self):
        # Create unverified context to bypass SSL errors
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        for studio in self.studios:
            if not self._is_running:
                break

            logo_url = studio.get("logo_url")
            studio_id = studio.get("id")

            if not logo_url or not studio_id:
                continue

            # We always save as PNG after processing
            filename = f"{studio_id}.png"
            filepath = os.path.join(self.logos_dir, filename)

            try:
                # Download data
                req = urllib.request.Request(
                    logo_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
                    },
                )
                with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
                    data = response.read()

                # Process Image
                image = QtGui.QImage.fromData(data)
                if image.isNull():
                    print(f"Failed to load image data for {studio_id}")
                    continue

                # 1. Make White (preserve alpha)
                # Convert to ARGB32 Premultiplied for consistent composition
                image = image.convertToFormat(QtGui.QImage.Format_ARGB32_Premultiplied)

                painter = QtGui.QPainter(image)
                painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceIn)
                painter.fillRect(image.rect(), QtGui.QColor("white"))
                painter.end()

                # 2. Trim Padding
                image = self.trim_image(image)

                # Save
                image.save(filepath, "PNG")

                self.logo_downloaded.emit(studio_id)

            except Exception as e:
                print(f"Failed to process logo for {studio_id}: {e}")

        self.finished.emit()

    def trim_image(self, image):
        """
        Trims transparent padding from the image.
        """
        width = image.width()
        height = image.height()

        min_x = width
        min_y = height
        max_x = 0
        max_y = 0

        found = False

        # We need to scan pixels.
        # Optimized approach: check alpha of pixel.
        # Format is ARGB32, so pixel values are integers.

        for y in range(height):
            for x in range(width):
                # get alpha
                # QImage.pixel() returns #AARRGGBB unsigned int
                pixel = image.pixel(x, y)
                alpha = (pixel >> 24) & 0xFF

                if alpha > 0:
                    found = True
                    if x < min_x:
                        min_x = x
                    if x > max_x:
                        max_x = x
                    if y < min_y:
                        min_y = y
                    if y > max_y:
                        max_y = y

        if not found:
            return image

        # Add 1 to max to include the pixel
        rect = QtCore.QRect(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)
        return image.copy(rect)

    def stop(self):
        self._is_running = False


class ConfigManager(QtCore.QObject):
    logos_updated = QtCore.Signal()  # Emitted when any logo is downloaded (general update)
    logo_downloaded = QtCore.Signal(str)  # Emitted when a specific logo is ready
    logo_cleared = QtCore.Signal(str)  # Emitted when a logo is removed (to show text placeholder)

    jobs_updated = QtCore.Signal(str, list)  # studio_id, date

    def __init__(self, parent=None):
        super(ConfigManager, self).__init__(parent)
        # Root dir is up one level from 'core'
        self.root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_path = os.path.join(self.root_dir, "config", "studios.json")
        self.logos_dir = os.path.join(self.root_dir, "resources", "logos")

        if not os.path.exists(self.logos_dir):
            os.makedirs(self.logos_dir)

        self.studios = []
        self.jobs_cache = {}  # {studio_id: [jobs]}

        self.logo_worker = None
        self.job_worker = None

        from .job_scraper import JobScraper

        self.scraper = JobScraper()

        self.load_config()
        self.download_missing_logos()

    def load_config(self):
        # Check local config first
        if os.path.exists(self.config_path):
            pass
        else:
            # Fallback to mac resources
            # self.root_dir is .../pyside
            project_root = os.path.dirname(self.root_dir)
            mac_config = os.path.join(project_root, "mac", "Resources", "studios.json")
            if os.path.exists(mac_config):
                print(f"Using shared config from {mac_config}")
                self.config_path = mac_config
            else:
                print(f"Config file not found at {self.config_path} or {mac_config}")

        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                try:
                    self.studios = json.load(f)
                except json.JSONDecodeError:
                    print(f"Error decoding {self.config_path}")
                    self.studios = []
        else:
            self.studios = []

    def save_config(self):
        with open(self.config_path, "w") as f:
            json.dump(self.studios, f, indent=4)

    def get_studios(self):
        return self.studios

    def get_studio_jobs(self, studio_id):
        return self.jobs_cache.get(studio_id, [])

    def add_studio(self, studio_data):
        self.studios.append(studio_data)
        self.save_config()
        # Auto download logo for new studio
        self.download_logos([studio_data])

    def update_studio(self, studio_data):
        """Updates an existing studio's data."""
        updated = False
        for i, studio in enumerate(self.studios):
            if studio.get("id") == studio_data.get("id"):
                self.studios[i] = studio_data
                updated = True
                break

        if updated:
            self.save_config()
            self.refresh_studio_logo(studio_data)

    def download_missing_logos(self):
        """Checks for missing logos and downloads them in a thread."""
        missing = []
        for studio in self.studios:
            sid = studio.get("id")
            if not self.get_logo_path(sid):
                missing.append(studio)

        if missing:
            self.download_logos(missing)

    def refresh_logos(self):
        """Force re-download of all logos. Deletes existing cache first."""
        # Clear existing logo files
        if os.path.exists(self.logos_dir):
            for f in os.listdir(self.logos_dir):
                if f.endswith(".png"):
                    try:
                        filepath = os.path.join(self.logos_dir, f)
                        os.remove(filepath)
                    except OSError:
                        pass

        # Emit cleared for all
        for studio in self.studios:
            self.logo_cleared.emit(studio.get("id"))

        self.download_logos(self.studios)

    def refresh_studio_logo(self, studio_data):
        """Refreshes a specific studio logo."""
        sid = studio_data.get("id")
        # Remove existing
        path = self.get_logo_path(sid)
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

        self.logo_cleared.emit(sid)
        self.download_logos([studio_data])

    def download_logos(self, studios_to_download):
        if self.logo_worker and self.logo_worker.isRunning():
            self.logo_worker.stop()
            self.logo_worker.wait()

        self.logo_worker = LogoWorker(studios_to_download, self.logos_dir)
        # Using lambda with *args to safely ignore arguments if signal signature changes,
        # avoiding "TypeError: <lambda>() takes 1 positional argument but 2 were given"
        self.logo_worker.logo_downloaded.connect(self.logo_downloaded.emit)  # Relay specific update
        self.logo_worker.logo_downloaded.connect(lambda sid: self.logos_updated.emit())  # Generic update
        self.logo_worker.start()

    def get_logo_path(self, studio_id):
        # We only look for PNG now as we standardize
        path = os.path.join(self.logos_dir, f"{studio_id}.png")
        if os.path.exists(path):
            return path
        return None

    # --- Job Fetching ---

    def fetch_all_jobs(self):
        self.start_job_worker(self.studios)

    def fetch_studio_jobs(self, studio_data):
        self.start_job_worker([studio_data])

    def start_job_worker(self, studios):
        if self.job_worker and self.job_worker.isRunning():
            # For now, we don't stop previous worker to allow parallel or queueing?
            # Simple approach: one worker at a time.
            self.job_worker.stop()
            self.job_worker.wait()

        self.job_worker = JobWorker(studios, self.scraper)
        self.job_worker.jobs_ready.connect(self._on_jobs_ready)
        self.job_worker.start()

    def _on_jobs_ready(self, studio_id, jobs):
        self.jobs_cache[studio_id] = jobs
        self.jobs_updated.emit(studio_id, jobs)


class JobWorker(QtCore.QThread):
    jobs_ready = QtCore.Signal(str, list)  # studio_id, list of job dicts
    finished = QtCore.Signal()

    def __init__(self, studios, scraper, parent=None):
        super(JobWorker, self).__init__(parent)
        self.studios = studios
        self.scraper = scraper
        self._is_running = True

    def run(self):
        for studio in self.studios:
            if not self._is_running:
                break

            jobs = self.scraper.fetch_jobs(studio)
            self.jobs_ready.emit(studio.get("id"), jobs)

        self.finished.emit()

    def stop(self):
        self._is_running = False
