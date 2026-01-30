try:
    from PySide2 import QtWidgets, QtCore, QtGui  # noqa: F401
    from PySide2.QtWidgets import QAction  # noqa: F401
except ImportError:
    from PySide6 import QtWidgets, QtCore, QtGui  # noqa: F401
    from PySide6.QtGui import QAction  # noqa: F401
import re
import os

from .flow_layout import FlowLayout
from .widgets import WaitingSpinner, ClickableLabel
from .styles import (
    JOB_WIDGET_STYLE,
    STUDIO_WIDGET_STYLE,
    GLOBAL_STYLE,
    NO_RESULTS_STYLE,
    SCROLL_AREA_STYLE,
    LOCATION_STYLE,
    TITLE_STYLE,
)
import maya.cmds as cmds

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin


try:
    from ..utils.maya_utils import get_maya_main_window
except (ImportError, ValueError):
    from utils.maya_utils import get_maya_main_window


class JobWidget(QtWidgets.QFrame):
    def __init__(self, job_data, parent=None):
        super(JobWidget, self).__init__(parent)
        self.job_data = job_data

        # Min properties to wrap content snugly
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum)

        # Native borders
        self.setFrameStyle(QtWidgets.QFrame.Box | QtWidgets.QFrame.Plain)
        self.setStyleSheet(JOB_WIDGET_STYLE)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Title
        self.title_label = QtWidgets.QLabel(job_data.get("title", "Unknown"))
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet(TITLE_STYLE)
        layout.addWidget(self.title_label)

        # Location (Cleaned)
        raw_loc = job_data.get("location", "")
        if "," in raw_loc:
            clean_loc = raw_loc.split(",")[0].strip()
        else:
            clean_loc = raw_loc.strip()

        self.location_label = QtWidgets.QLabel(clean_loc)
        self.location_label.setWordWrap(True)

        self.location_label.setStyleSheet(LOCATION_STYLE)

        layout.addWidget(self.location_label)

        layout.addStretch()  # Push content up

        # Link Button Overlay or Layout?
        # Adding to layout
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()

        self.link_btn = QtWidgets.QPushButton()
        self.link_btn.setIcon(QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_ArrowRight))
        # No flat button as requested
        self.link_btn.setFlat(False)
        self.link_btn.setToolTip("Open Job Link")
        self.link_btn.clicked.connect(self.open_link)
        self.link_btn.setFixedSize(30, 24)

        btn_layout.addWidget(self.link_btn)
        layout.addLayout(btn_layout)

    def open_link(self):
        link = self.job_data.get("link")
        if link:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl(str(link)))


class StudioWidget(QtWidgets.QFrame):
    def __init__(self, studio_data, config_manager, parent=None):
        super(StudioWidget, self).__init__(parent)
        self.studio_data = studio_data
        self.config_manager = config_manager
        self.job_widgets = []
        self.no_match_label = None

        self.setObjectName("studio_widget")
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        # Outline / Style
        self.setStyleSheet(STUDIO_WIDGET_STYLE)

        self.setFixedSize(280, 400)  # Fixed Card Size for Grid

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # -- Header: Logo, Name, Refresh --
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setContentsMargins(5, 5, 5, 0)

        # Logo (Centered)
        # Use ClickableLabel
        self.logo_label = ClickableLabel()
        self.logo_label.setAlignment(QtCore.Qt.AlignCenter)
        self.logo_label.setFixedSize(100, 40)
        self.logo_label.clicked.connect(self.open_careers_page)
        self.logo_label.setToolTip("Open Careers Page")

        # Name (Centered effectively by hiding logo)
        self.name_label = ClickableLabel()
        self.name_label.setStyleSheet("font-weight: bold; border: none;")
        self.name_label.setAlignment(QtCore.Qt.AlignCenter)
        self.name_label.setWordWrap(True)
        self.name_label.clicked.connect(self.open_careers_page)
        self.name_label.setToolTip("Open Careers Page")

        header_layout.addStretch()
        header_layout.addWidget(self.logo_label)
        header_layout.addWidget(self.name_label)
        header_layout.addStretch()

        # Stack Refresh and Spinner
        self.refresh_btn = QtWidgets.QPushButton()
        self.refresh_btn.setIcon(
            QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_BrowserReload)
        )
        self.refresh_btn.setFlat(True)
        self.refresh_btn.setFixedSize(25, 25)
        self.refresh_btn.clicked.connect(self.fetch_jobs)
        self.refresh_btn.setStyleSheet("border: none;")

        self.spinner = WaitingSpinner()
        self.spinner.hide()

        header_layout.addWidget(self.refresh_btn)
        header_layout.addWidget(self.spinner)

        layout.addLayout(header_layout)

        # -- Body: Vertical Scroll of Jobs --
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        # Removed setStyleSheet to allow native scrollbars (like main window)

        self.scroll_content = QtWidgets.QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.scroll_layout = QtWidgets.QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(2, 2, 2, 2)
        self.scroll_layout.setSpacing(4)

        # Stretch to push items up if few jobs
        self.scroll_layout.addStretch()

        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area)

        self.load_logo()
        self.update_jobs()

        # Connect signals
        self.config_manager.logo_cleared.connect(self.on_logo_cleared)
        self.config_manager.logo_downloaded.connect(self.on_logo_downloaded)
        self.config_manager.jobs_updated.connect(self.on_jobs_updated)
        self.config_manager.jobs_started.connect(self.on_jobs_started)

    def open_careers_page(self):
        url = self.studio_data.get("careers_url") or self.studio_data.get("website")
        if url:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl(str(url)))

    def show_context_menu(self, pos):
        menu = QtWidgets.QMenu(self)
        menu.addAction("Refresh Jobs", self.fetch_jobs)

        act_open_web = menu.addAction("Open Careers Page")
        act_open_web.triggered.connect(self.open_careers_page)

        act_update_logo = menu.addAction("Force Refresh Logo")
        act_update_logo.triggered.connect(lambda: self.config_manager.refresh_studio_logo(self.studio_data))

        menu.addSeparator()

        act_edit = menu.addAction("Edit Studio...")
        act_edit.triggered.connect(self.open_edit_dialog)

        menu.exec_(self.mapToGlobal(pos))

    def open_edit_dialog(self):
        from .edit_studio_dialog import EditStudioDialog

        dialog = EditStudioDialog(self.studio_data, self)
        dialog.studio_edited.connect(self.config_manager.update_studio)
        dialog.exec_()

    def load_logo(self):
        sid = self.studio_data.get("id")
        path = self.config_manager.get_logo_path(sid)

        if path and os.path.exists(path):
            pix = QtGui.QPixmap(path)
            if not pix.isNull():
                self.logo_label.setPixmap(
                    pix.scaled(100, 40, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                )
                self.logo_label.show()
                self.name_label.hide()
                return

        self.logo_label.hide()
        self.name_label.show()

    def fetch_jobs(self):
        self.config_manager.fetch_studio_jobs(self.studio_data)

    def on_logo_cleared(self, sid):
        if sid == self.studio_data.get("id"):
            self.load_logo()

    def on_logo_downloaded(self, sid):
        if sid == self.studio_data.get("id"):
            self.load_logo()

    def on_jobs_started(self, sid):
        if sid == self.studio_data.get("id"):
            self.refresh_btn.hide()
            self.spinner.show()

    def on_jobs_updated(self, sid, jobs):
        if sid == self.studio_data.get("id"):
            self.update_jobs()
            self.spinner.hide()
            self.refresh_btn.show()

    def update_jobs(self):
        # Clear existing
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.spacerItem():
                pass  # Removed

        jobs = self.config_manager.get_studio_jobs(self.studio_data.get("id"))
        self.job_widgets = []

        if not jobs:
            lbl = QtWidgets.QLabel("No jobs found")
            lbl.setAlignment(QtCore.Qt.AlignCenter)
            lbl.setStyleSheet(NO_RESULTS_STYLE)
            self.scroll_layout.addWidget(lbl)
        else:
            for job in jobs:
                w = JobWidget(job)
                self.scroll_layout.addWidget(w)
                self.job_widgets.append(w)

            # Label for search filtering
            self.no_match_label = QtWidgets.QLabel("No matches found")
            self.no_match_label.setAlignment(QtCore.Qt.AlignCenter)
            self.no_match_label.setStyleSheet(NO_RESULTS_STYLE)
            self.no_match_label.hide()
            self.scroll_layout.addWidget(self.no_match_label)

        self.scroll_layout.addStretch()  # Ensure top alignment

    def filter_jobs(self, pattern):
        match_count = 0
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error:
            regex = re.compile(re.escape(pattern), re.IGNORECASE)

        for w in self.job_widgets:
            title = w.job_data.get("title", "")
            if regex.search(title):
                w.show()
                match_count += 1
            else:
                w.hide()

        if self.no_match_label:
            if match_count == 0 and len(self.job_widgets) > 0:
                self.no_match_label.show()
            else:
                self.no_match_label.hide()

        return match_count


class MainWindow(MayaQWidgetDockableMixin, QtWidgets.QMainWindow):
    TOOL_TITLE = "JobUI Manager"
    TOOL_OBJECT_NAME = "JobUIManager"
    WORKSPACE_CONTROL_NAME = "JobUIWorkspaceControl"

    def __init__(self, parent=None):
        try:
            from ..utils.maya_utils import MAYA_AVAILABLE
        except (ImportError, ValueError):
            from utils.maya_utils import MAYA_AVAILABLE

        if MAYA_AVAILABLE:
            pass

        super(MainWindow, self).__init__(parent=parent)
        self.setWindowTitle(self.TOOL_TITLE)
        self.setObjectName(self.TOOL_OBJECT_NAME)
        self.resize(1100, 800)
        self.setStyleSheet(GLOBAL_STYLE)

        # Native config
        try:
            from ..core.config_manager import ConfigManager
        except (ImportError, ValueError):
            from core.config_manager import ConfigManager

        self.config_manager = ConfigManager()
        self.studio_widgets = []

        self.setup_ui()
        self.refresh_studios_list()

        self.config_manager.studio_visibility_changed.connect(self.on_studio_visibility_changed)
        self.config_manager.studios_refreshed.connect(self.refresh_studios_list)
        self.config_manager.jobs_updated.connect(lambda sid, jobs: self._do_search())

        # Debounce timer for search
        self.search_timer = QtCore.QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(250)
        self.search_timer.timeout.connect(self._do_search)

        # Fetch all on startup
        QtCore.QTimer.singleShot(500, self.config_manager.fetch_all_jobs)

    def setup_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_layout = QtWidgets.QVBoxLayout(central)

        # -- Top Bar --
        top_bar = QtWidgets.QHBoxLayout()

        # Search Box
        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("Filter jobs (Text or Regex)...")
        self.search_input.textChanged.connect(self.on_search_changed)
        top_bar.addWidget(self.search_input)

        # Fetch All Button
        self.fetch_all_btn = QtWidgets.QPushButton("Refetch All")
        self.fetch_all_btn.setObjectName("fetch_all_btn")
        self.fetch_all_btn.setIcon(
            QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_BrowserReload)
        )
        self.fetch_all_btn.clicked.connect(self.config_manager.fetch_all_jobs)
        top_bar.addWidget(self.fetch_all_btn)

        main_layout.addLayout(top_bar)

        # -- Main Content (Scroll of Studios) --
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scroll_area.setStyleSheet(SCROLL_AREA_STYLE)

        self.studios_container = QtWidgets.QWidget()
        # Use FlowLayout here
        self.studios_layout = FlowLayout(self.studios_container, margin=10)

        self.scroll_area.setWidget(self.studios_container)
        main_layout.addWidget(self.scroll_area)

        # Menu (Keeping menu for manual refresh of cached images if needed)
        self.setup_menu()

    def setup_menu(self):
        menubar = self.menuBar()

        self.studios_menu = menubar.addMenu("Studios")
        self.studios_menu.aboutToShow.connect(self.populate_studios_menu)

        # Populate immediately so it isn't empty (which might prevent opening)
        self.populate_studios_menu()

        opts = menubar.addMenu("Options")

        act = QAction("Refresh All Logos", self)
        act.triggered.connect(self.config_manager.refresh_logos)
        opts.addAction(act)

        act_add = QAction("Add Studio...", self)
        act_add.triggered.connect(self.open_add_studio_dialog)
        opts.addAction(act_add)

    def populate_studios_menu(self):
        try:
            self.studios_menu.clear()
        except RuntimeError:
            return

        studios = self.config_manager.get_studios()
        # Sort by name for easier navigation
        sorted_studios = sorted(studios, key=lambda s: s.get("name", "").lower())

        for studio in sorted_studios:
            sid = studio.get("id")
            name = studio.get("name", sid)

            act = QAction(name, self)
            act.setCheckable(True)
            is_enabled = self.config_manager.is_studio_enabled(sid)
            act.setChecked(is_enabled)

            # Use closure to capture sid
            def make_handler(s_id):
                return lambda checked: self.config_manager.set_studio_enabled(s_id, checked)

            act.triggered.connect(make_handler(sid))
            self.studios_menu.addAction(act)

    def open_add_studio_dialog(self):
        from .add_studio_dialog import AddStudioDialog

        dialog = AddStudioDialog(self)
        dialog.studio_added.connect(self.on_studio_added)
        dialog.exec_()

    def on_studio_added(self, studio_data):
        self.config_manager.add_studio(studio_data)

    def on_studio_visibility_changed(self, studio_id, enabled):
        for sw in self.studio_widgets:
            if sw.studio_data.get("id") == studio_id:
                sw.setVisible(enabled)
                return

    def refresh_studios_list(self):
        # Helper to clear layout widgets
        while self.studios_layout.count():
            item = self.studios_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.studio_widgets = []
        studios = self.config_manager.get_studios()

        for studio in studios:
            is_enabled = self.config_manager.is_studio_enabled(studio.get("id"))
            sw = StudioWidget(studio, self.config_manager)
            self.studios_layout.addWidget(sw)
            self.studio_widgets.append(sw)
            if not is_enabled:
                sw.hide()

        self._do_search()
        print(f"Loaded {len(studios)} studios.")

    def on_search_changed(self, text):
        self.search_timer.start()

    def _do_search(self):
        text = self.search_input.text()
        for sw in self.studio_widgets:
            sw.filter_jobs(text)

    def set_windowPosition(self):
        settings = QtCore.QSettings("JobUI", "MainWindow")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

    def save_windowPosition(self):
        settings = QtCore.QSettings("JobUI", "MainWindow")
        settings.setValue("geometry", self.saveGeometry())

    def _cleanup(self):
        try:
            if cmds.workspaceControl(self.WORKSPACE_CONTROL_NAME, exists=True):
                cmds.deleteUI(self.WORKSPACE_CONTROL_NAME)
        except Exception:
            pass
        self.setParent(None)
        self.deleteLater()

    def dockCloseEventTriggered(self):
        self.save_windowPosition()
        self._cleanup()

    @classmethod
    def showUI(cls):
        for ui in [cls.WORKSPACE_CONTROL_NAME]:
            try:
                if cmds.workspaceControl(ui, exists=True):
                    cmds.deleteUI(ui)
            except Exception:
                pass

        inst = cls(get_maya_main_window())
        inst.show(dockable=True, retain=False)
        inst.set_windowPosition()
        return inst
