try:
    from PySide2 import QtCore, QtWidgets, QtGui, QtWebEngineWidgets, QtSvg
    WEB_AVAILABLE = True
except ImportError:
    try:
        from PySide6 import QtCore, QtWidgets, QtGui, QtWebEngineWidgets, QtSvg
        WEB_AVAILABLE = True
    except ImportError:
        WEB_AVAILABLE = False

import os
import tempfile
import urllib.request as urllib2

class MockBrowser(QtWidgets.QDialog):
    """
    A minimalist web previewer to verify URLs and Logos without leaving the app.
    """
    def __init__(self, url, parent=None):
        super(MockBrowser, self).__init__(parent)
        self.setWindowTitle("Preview: " + str(url))
        self.resize(1000, 700)
        
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        toolbar = QtWidgets.QWidget()
        toolbar.setFixedHeight(40)
        toolbar.setStyleSheet("background: #2b2b2b; border-bottom: 1px solid #3d3d3d;")
        toolbar_layout = QtWidgets.QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(10, 0, 10, 0)

        address_bar = QtWidgets.QLineEdit(url)
        address_bar.setReadOnly(True)
        address_bar.setStyleSheet("background: #1e1e1e; border: 1px solid #444; color: #aaa; border-radius: 4px; padding: 4px 8px;")
        
        btn_open_external = QtWidgets.QPushButton("🌐 Open in browser")
        btn_open_external.setStyleSheet("background: #444; border: none; padding: 4px 10px; border-radius: 4px;")
        btn_open_external.clicked.connect(lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(url)))

        toolbar_layout.addWidget(address_bar)
        toolbar_layout.addWidget(btn_open_external)
        main_layout.addWidget(toolbar)

        if WEB_AVAILABLE:
            self.web_view = QtWebEngineWidgets.QWebEngineView()
            self.web_view.setUrl(QtCore.QUrl(url))
            main_layout.addWidget(self.web_view)
        else:
            fallback_message = QtWidgets.QLabel("Previewing:\n" + str(url) + "\n\n(WebEngine not available. Using system browser fallback...)")
            fallback_message.setAlignment(QtCore.Qt.AlignCenter)
            fallback_message.setStyleSheet("color: #888; font-size: 14px;")
            main_layout.addWidget(fallback_message)
            QtCore.QTimer.singleShot(1500, lambda: [QtGui.QDesktopServices.openUrl(QtCore.QUrl(url)), self.close()])


class TestWorker(QtCore.QThread):
    finished = QtCore.Signal(dict)
    error = QtCore.Signal(str)

    def __init__(self, cfg):
        super(TestWorker, self).__init__()
        self.cfg = cfg
        self.logo_path = None
        self.jobs = []

    def run(self):
        try:
            # 1. Process Logo (Whitening + Cropping)
            l_url = self.cfg.get("logo_url")
            if l_url and l_url.startswith("http"):
                try:
                    td = tempfile.gettempdir()
                    tp = os.path.join(td, "jobui_t_" + str(self.cfg["id"]) + ".png")
                    req = urllib2.Request(l_url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib2.urlopen(req, timeout=10) as r:
                         data = r.read()
                    
                    if l_url.lower().endswith(".svg"):
                        renderer = QtSvg.QSvgRenderer(data)
                        if renderer.isValid():
                            size = renderer.defaultSize()
                            if size.isEmpty(): size = QtCore.QSize(400, 400)
                            img = QtGui.QImage(size, QtGui.QImage.Format_ARGB32)
                            img.fill(0)
                            p = QtGui.QPainter(img)
                            renderer.render(p)
                            p.end()
                        else: img = QtGui.QImage()
                    else: img = QtGui.QImage.fromData(data)

                    if not img.isNull():
                        img = img.convertToFormat(QtGui.QImage.Format_ARGB32)
                        for y in range(img.height()):
                            for x in range(img.width()):
                                c = img.pixelColor(x, y)
                                if c.alpha() > 0:
                                    c.setRed(255)
                                    c.setGreen(255)
                                    c.setBlue(255)
                                    img.setPixelColor(x, y, c)
                        
                        w, h = img.width(), img.height()
                        min_x, min_y, max_x, max_y = w, h, 0, 0
                        found = False
                        for y in range(h):
                            for x in range(w):
                                pixel = img.pixel(x, y)
                                alpha = (pixel >> 24) & 0xFF
                                if alpha > 0:
                                    found = True
                                    if x < min_x: min_x = x
                                    if x > max_x: max_x = x
                                    if y < min_y: min_y = y
                                    if y > max_y: max_y = y
                        if found:
                            rect = QtCore.QRect(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)
                            img = img.copy(rect)
                        img.save(tp, "PNG")
                        self.logo_path = tp
                except: pass

            # 2. Fetch Jobs
            from ..core.job_scraper import JobScraper
            self.jobs = JobScraper().fetch_jobs(self.cfg)
            self.finished.emit({"jobs": self.jobs, "logo_path": self.logo_path})
        except Exception as e:
            self.error.emit(str(e))


class TestPreviewDialog(QtWidgets.QDialog):
    """
    Floating preview that displays how the studio and its jobs will look.
    """
    def __init__(self, studio_data, jobs, logo_path=None, parent_dialog=None):
        super(TestPreviewDialog, self).__init__(parent_dialog)
        self.parent_dialog = parent_dialog
        self.studio_id = studio_data.get("id", "preview_id")
        
        self.setWindowTitle("Live Preview: " + str(studio_data.get('name')))
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)
        
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        
        try:
            from .main_window import StudioWidget
            
            class MockConfigManager:
                def __init__(self, m_jobs, m_logo_path, m_parent_dialog):
                    self.m_jobs = m_jobs
                    self.m_logo_path = m_logo_path
                    self.m_parent_dialog = m_parent_dialog
                    
                class Signal:
                    def connect(self, slot): pass
                
                logo_cleared = Signal()
                logo_downloaded = Signal()
                jobs_updated = Signal()
                jobs_failed = Signal()
                jobs_started = Signal()
                
                def get_logo_path(self, sid):
                    return self.m_logo_path or ""
                def get_studio_jobs(self, sid):
                    return self.m_jobs
                def is_studio_enabled(self, sid):
                    return True
                def get_studios(self):
                    return []
                def fetch_studio_jobs(self, studio_data):
                    pass
            
            self.preview_widget = StudioWidget(studio_data, MockConfigManager(jobs, logo_path, self.parent_dialog), self)
            self.preview_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
            self.preview_widget.refresh_btn.setToolTip("Click 'Test' in editor to refresh preview")
            self.layout.addWidget(self.preview_widget, 1)
            
            hint = QtWidgets.QLabel("<i>Card preview based on current configuration.</i>")
            hint.setStyleSheet("color: #777; font-size: 11px;")
            hint.setAlignment(QtCore.Qt.AlignCenter)
            self.layout.addWidget(hint, 0)
            
        except Exception as e:
            msg = "<b>" + str(studio_data.get('name')) + "</b> (" + str(len(jobs)) + " jobs found)"
            label = QtWidgets.QLabel(msg)
            self.layout.addWidget(label)
            
            scroll = QtWidgets.QScrollArea()
            scroll.setWidgetResizable(True)
            content = QtWidgets.QWidget()
            vbox = QtWidgets.QVBoxLayout(content)
            for job in jobs[:20]:
                item_text = "• " + str(job.get('title')) + "\n  <span style='color:#888;'>" + str(job.get('location')) + "</span>"
                item = QtWidgets.QLabel(item_text)
                item.setWordWrap(True)
                vbox.addWidget(item)
            vbox.addStretch()
            scroll.setWidget(content)
            self.layout.addWidget(scroll)
        
        btn_close = QtWidgets.QPushButton("Close Preview")
        btn_close.clicked.connect(self.accept)
        btn_close.setFixedHeight(30)
        self.layout.addWidget(btn_close)
