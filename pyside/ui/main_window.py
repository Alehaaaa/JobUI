from PySide2 import QtWidgets, QtCore, QtGui
import re
import os

from .flow_layout import FlowLayout


class JobWidget(QtWidgets.QFrame):
    def __init__(self, job_data, parent=None):
        super(JobWidget, self).__init__(parent)
        self.job_data = job_data
        self.setFrameStyle(QtWidgets.QFrame.StyledPanel | QtWidgets.QFrame.Raised)
        # No fixed width, expand to container

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)

        # Title
        self.title_label = QtWidgets.QLabel(job_data.get("title", "Unknown"))
        self.title_label.setWordWrap(True)
        font = self.title_label.font()
        font.setBold(True)
        self.title_label.setFont(font)
        layout.addWidget(self.title_label)

        # Location (Cleaned)
        raw_loc = job_data.get("location", "")
        # Filter/Trim location: take first part before comma or newline?
        # User said "filter out the location... where it gets strimmed"
        # Heuristic: Split by ',' and take first.
        if "," in raw_loc:
            clean_loc = raw_loc.split(",")[0].strip()
        else:
            clean_loc = raw_loc.strip()

        self.location_label = QtWidgets.QLabel(clean_loc)
        self.location_label.setWordWrap(True)
        loc_font = self.location_label.font()
        loc_font.setPointSize(loc_font.pointSize() - 2)
        self.location_label.setFont(loc_font)

        palette = self.location_label.palette()
        palette.setColor(QtGui.QPalette.WindowText, palette.color(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText))
        self.location_label.setPalette(palette)

        layout.addWidget(self.location_label)

        layout.addStretch()  # Push content up

        # Link Button Overlay or Layout?
        # Adding to layout
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()

        self.link_btn = QtWidgets.QPushButton()
        self.link_btn.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_ArrowRight))
        self.link_btn.setFlat(True)
        self.link_btn.setToolTip("Open Job Link")
        self.link_btn.clicked.connect(self.open_link)
        self.link_btn.setMaximumWidth(30)
        self.link_btn.setMaximumHeight(20)

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

        self.setObjectName("studio_widget")
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        # Outline / Style
        # Using ID selector to ensure specificity
        self.setStyleSheet("""
            #studio_widget {
                border: 1px solid #444;
                border-radius: 4px;
                background-color: #2d2d2d;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)

        self.setFixedSize(280, 400)  # Fixed Card Size for Grid

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # -- Header: Logo, Name, Refresh --
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setContentsMargins(5, 5, 5, 0)

        # Logo (Centered)
        self.logo_label = QtWidgets.QLabel()
        self.logo_label.setAlignment(QtCore.Qt.AlignCenter)
        self.logo_label.setFixedSize(100, 40)

        # Name (Centered effectively by hiding logo)
        self.name_label = QtWidgets.QLabel(studio_data.get("name", ""))
        self.name_label.setStyleSheet("font-weight: bold; border: none;")
        self.name_label.setAlignment(QtCore.Qt.AlignCenter)
        self.name_label.setWordWrap(True)

        # We want to center the content.
        # If Logo: [Stretch] [Logo] [Stretch] [Refresh]
        # But Refresh is always right.
        # Modified layout: [Stretch] [Stack(Logo, Name)] [Stretch] [Refresh]

        header_layout.addStretch()
        header_layout.addWidget(self.logo_label)
        header_layout.addWidget(self.name_label)
        header_layout.addStretch()

        # Refresh
        self.refresh_btn = QtWidgets.QPushButton()
        self.refresh_btn.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_BrowserReload))
        self.refresh_btn.setFlat(True)
        self.refresh_btn.setFixedSize(25, 25)
        self.refresh_btn.clicked.connect(self.fetch_jobs)
        # Style refresh btn to avoid border from parent style
        self.refresh_btn.setStyleSheet("border: none;")
        header_layout.addWidget(self.refresh_btn)

        layout.addLayout(header_layout)

        # -- Body: Vertical Scroll of Jobs --
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)  # StyledPanel conflict with styleSheet
        self.scroll_area.setStyleSheet("background: transparent; border: none;")

        self.scroll_content = QtWidgets.QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.scroll_layout = QtWidgets.QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(2, 2, 2, 2)
        self.scroll_layout.setSpacing(2)
        self.scroll_layout.addStretch()  # Push items to top

        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area)

        self.load_logo()
        self.update_jobs()

        # Connect signals
        self.config_manager.logo_cleared.connect(self.on_logo_cleared)
        self.config_manager.logo_downloaded.connect(self.on_logo_downloaded)
        self.config_manager.jobs_updated.connect(self.on_jobs_updated)

    def show_context_menu(self, pos):
        menu = QtWidgets.QMenu(self)
        menu.addAction("Refresh Jobs", self.fetch_jobs)

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
        # Could show spinner?
        self.config_manager.fetch_studio_jobs(self.studio_data)

    def on_logo_cleared(self, sid):
        if sid == self.studio_data.get("id"):
            self.load_logo()

    def on_logo_downloaded(self, sid):
        if sid == self.studio_data.get("id"):
            self.load_logo()

    def on_jobs_updated(self, sid, jobs):
        if sid == self.studio_data.get("id"):
            self.update_jobs()

    def update_jobs(self):
        # Clear existing
        # Layouts with addStretch are tricky to clear.
        # Removing all items.
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
            lbl.setStyleSheet("color: gray;")
            self.scroll_layout.addWidget(lbl)
        else:
            for job in jobs:
                w = JobWidget(job)
                self.scroll_layout.addWidget(w)
                self.job_widgets.append(w)

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
        return match_count


try:
    from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
except ImportError:

    class MayaQWidgetDockableMixin(object):
        pass


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

        # Native config
        try:
            from ..core.config_manager import ConfigManager
        except (ImportError, ValueError):
            from core.config_manager import ConfigManager

        self.config_manager = ConfigManager()
        self.studio_widgets = []

        self.setup_ui()
        self.refresh_studios_list()

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
        self.fetch_all_btn.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_BrowserReload))
        self.fetch_all_btn.clicked.connect(self.config_manager.fetch_all_jobs)
        top_bar.addWidget(self.fetch_all_btn)

        main_layout.addLayout(top_bar)

        # -- Main Content (Scroll of Studios) --
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)

        self.studios_container = QtWidgets.QWidget()
        # Use FlowLayout here
        self.studios_layout = FlowLayout(self.studios_container, margin=10)

        self.scroll_area.setWidget(self.studios_container)
        main_layout.addWidget(self.scroll_area)

        # Menu (Keeping menu for manual refresh of cached images if needed)
        self.setup_menu()

    def setup_menu(self):
        menubar = self.menuBar()
        opts = menubar.addMenu("Options")

        act = QtWidgets.QAction("Refresh All Logos (Clear Cache)", self)
        act.triggered.connect(self.config_manager.refresh_logos)
        opts.addAction(act)

        from .add_studio_dialog import AddStudioDialog

        act_add = QtWidgets.QAction("Add Studio...", self)
        act_add.triggered.connect(lambda: AddStudioDialog(self).exec_())
        opts.addAction(act_add)

    def refresh_studios_list(self):
        # Clear existing (FlowLayout handling)
        # FlowLayout.takeAt deletes items? No, logic in del or we do it manually.
        # Helper to clear layout widgets
        while self.studios_layout.count():
            item = self.studios_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.studio_widgets = []
        studios = self.config_manager.get_studios()

        for studio in studios:
            sw = StudioWidget(studio, self.config_manager)
            self.studios_layout.addWidget(sw)
            self.studio_widgets.append(sw)

        print(f"Loaded {len(studios)} studios.")

    def on_search_changed(self, text):
        for sw in self.studio_widgets:
            sw.filter_jobs(text)
