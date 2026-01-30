import json
import os
import urllib.request
import ssl

try:
    from PySide2 import QtCore, QtGui, QtSvg
except ImportError:
    from PySide6 import QtCore, QtGui, QtSvg


class LogoWorker(QtCore.QThread):
    logo_downloaded = QtCore.Signal(str)  # studio_id
    finished = QtCore.Signal()

    def render_svg(self, data):
        """Renders SVG data (bytes) to a QImage."""
        renderer = QtSvg.QSvgRenderer(data)
        if not renderer.isValid():
            return QtGui.QImage()

        # Render to a QImage
        # We can define a default size or use defaultSize()
        size = renderer.defaultSize()
        if size.isEmpty():
            size = QtCore.QSize(200, 200)  # Fallback

        image = QtGui.QImage(size, QtGui.QImage.Format_ARGB32)
        image.fill(0)  # Transparent background

        painter = QtGui.QPainter(image)
        renderer.render(painter)
        painter.end()

        return image

    def __init__(self, studios, logos_dir, parent=None):
        super(LogoWorker, self).__init__(parent)
        self.studios = studios
        self.logos_dir = logos_dir
        self._is_running = True

    def process_logo(self, studio, ctx):
        logo_url = studio.get("logo_url")
        studio_id = studio.get("id")

        if not logo_url or not studio_id:
            return

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
            if logo_url.lower().endswith(".svg"):
                img = self.render_svg(data)
            else:
                img = QtGui.QImage.fromData(data)

            if img.isNull():
                return

            # 1. Make White (preserve alpha)
            image = img.convertToFormat(QtGui.QImage.Format_ARGB32_Premultiplied)
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

    def run(self):
        import concurrent.futures

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        max_workers = min(len(self.studios), 10)
        if max_workers < 1:
            max_workers = 1

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self.process_logo, s, ctx) for s in self.studios]
            for future in concurrent.futures.as_completed(futures):
                if not self._is_running:
                    break
                # results are handled via signals in process_logo

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
    jobs_started = QtCore.Signal(str)  # studio_id
    studio_visibility_changed = QtCore.Signal(str, bool)  # studio_id, enabled
    studios_refreshed = QtCore.Signal()  # Emitted when studios are added/edited/removed

    def __init__(self, parent=None):
        super(ConfigManager, self).__init__(parent)
        # Root dir is up one level from 'core'
        self.root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_path = os.path.join(self.root_dir, "config", "studios.json")
        self.logos_dir = os.path.join(self.root_dir, "resources", "logos")

        if not os.path.exists(self.logos_dir):
            os.makedirs(self.logos_dir)

        # Settings for local preferences (enabled/disabled studios)
        self.settings = QtCore.QSettings("JobUI", "ConfigManager")
        self.disabled_studios = self.settings.value("disabled_studios", []) or []
        # Ensure it's a list (QSettings might return None or other types depending on backend)
        if not isinstance(self.disabled_studios, list):
            self.disabled_studios = []

        self.studios = []
        self.jobs_cache = {}  # {studio_id: [jobs]}

        self.logo_worker = None
        self.job_worker = None

        try:
            from .job_scraper import JobScraper
        except (ImportError, ValueError):
            from core.job_scraper import JobScraper

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
                    raw_studios = json.load(f)
                    # Deduplicate: Keep the last occurrence of each ID
                    studios_map = {}
                    for s in raw_studios:
                        if "id" in s:
                            studios_map[s["id"]] = s
                    self.studios = list(studios_map.values())

                    # If we filtered changes, save back? Maybe not strictly necessary unless requested,
                    # but good for cleanup. User said "remove it first", likely immediately.
                    if len(self.studios) != len(raw_studios):
                        print("Removed duplicate studios from config.")
                        self.save_config()

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

    def is_studio_enabled(self, studio_id):
        return studio_id not in self.disabled_studios

    def set_studio_enabled(self, studio_id, enabled):
        if enabled:
            if studio_id in self.disabled_studios:
                self.disabled_studios.remove(studio_id)
        else:
            if studio_id not in self.disabled_studios:
                self.disabled_studios.append(studio_id)

        self.settings.setValue("disabled_studios", self.disabled_studios)
        self.studio_visibility_changed.emit(studio_id, enabled)

    def add_studio(self, studio_data):
        # Check if exists and remove first
        check_id = studio_data.get("id")
        existing_index = -1
        for i, s in enumerate(self.studios):
            if s.get("id") == check_id:
                existing_index = i
                break

        if existing_index != -1:
            self.studios.pop(existing_index)

        self.studios.append(studio_data)
        self.save_config()
        # Auto download logo for new studio
        self.download_logos([studio_data])
        self.studios_refreshed.emit()

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
            self.studios_refreshed.emit()

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

        # Emit started signal for all involved
        for s in studios:
            self.jobs_started.emit(s.get("id"))

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
        import concurrent.futures

        # Determine max workers based on list size, but cap it (e.g. 10 or 20) to avoid too many threads
        max_workers = min(len(self.studios), 20)
        if max_workers < 1:
            max_workers = 1

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_studio = {
                executor.submit(self.scraper.fetch_jobs, studio): studio for studio in self.studios
            }

            for future in concurrent.futures.as_completed(future_to_studio):
                if not self._is_running:
                    break

                studio = future_to_studio[future]
                try:
                    jobs = future.result()
                    self.jobs_ready.emit(studio.get("id"), jobs)
                except Exception as e:
                    print(f"Error processing jobs for {studio.get('name', 'Unknown')}: {e}")

        self.finished.emit()

    def stop(self):
        self._is_running = False
