import os
import urllib.request
import ssl
from .logger import logger

try:
    from PySide2 import QtCore, QtGui, QtSvg
except ImportError:
    from PySide6 import QtCore, QtGui, QtSvg


class LogoWorker(QtCore.QThread):
    logo_downloaded = QtCore.Signal(str)  # studio_id
    finished = QtCore.Signal()

    def __init__(self, studios, logos_dir, parent=None):
        super(LogoWorker, self).__init__(parent)
        self.studios = studios
        self.logos_dir = logos_dir
        self._is_running = True

    def render_svg(self, data):
        """Renders SVG data (bytes) to a QImage."""
        renderer = QtSvg.QSvgRenderer(data)
        if not renderer.isValid():
            return QtGui.QImage()

        # Render to a QImage
        size = renderer.defaultSize()
        if size.isEmpty():
            size = QtCore.QSize(200, 200)  # Fallback

        image = QtGui.QImage(size, QtGui.QImage.Format_ARGB32)
        image.fill(0)  # Transparent background

        painter = QtGui.QPainter(image)
        renderer.render(painter)
        painter.end()

        return image

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
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Referer": "https://www.google.com/",
                },
            )
            with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
                data = response.read()

            if not self._is_running:
                return

            # Process Image
            if logo_url.lower().endswith(".svg"):
                img = self.render_svg(data)
            else:
                img = QtGui.QImage.fromData(data)

            if img.isNull() or not self._is_running:
                return

            # 1. Make White (preserve alpha)
            image = img.convertToFormat(QtGui.QImage.Format_ARGB32)
            for y in range(image.height()):
                for x in range(image.width()):
                    pixel = image.pixelColor(x, y)
                    if pixel.alpha() > 0:
                        pixel.setRed(255)
                        pixel.setGreen(255)
                        pixel.setBlue(255)
                        image.setPixelColor(x, y, pixel)

            # 2. Trim Padding
            if not self._is_running:
                return
            image = self.trim_image(image)

            # Save
            if self._is_running:
                image.save(filepath, "PNG")
                self.logo_downloaded.emit(studio_id)

        except Exception as e:
            if self._is_running:
                logger.error(f"Failed to process logo for {studio_id}: {e}")

    def run(self):
        import concurrent.futures

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        max_workers = min(len(self.studios), 10)
        if max_workers < 1:
            max_workers = 1

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        future_to_studio = {executor.submit(self.process_logo, s, ctx): s for s in self.studios}
        pending = set(future_to_studio.keys())

        while pending and self._is_running:
            try:
                done, _ = concurrent.futures.wait(
                    pending, timeout=0.2, return_when=concurrent.futures.FIRST_COMPLETED
                )

                for future in done:
                    pending.remove(future)
                    try:
                        future.result()
                    except Exception as e:
                        if self._is_running:
                            s = future_to_studio[future]
                            logger.error(f"Error processing logo for {s.get('id', 'Unknown')}: {e}")
            except Exception:
                pass

        if not self._is_running:
            for f in pending:
                f.cancel()

        executor.shutdown(wait=False)

        if self._is_running:
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

        # Check alpha channel for content boundaries
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
