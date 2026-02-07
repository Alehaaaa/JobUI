import re
import os
import maya.cmds as cmds

try:
    from base64 import decodebytes
except ImportError:
    from base64 import decodestring as decodebytes


try:
    from PySide2 import QtWidgets, QtCore, QtGui  # noqa: F401
    from PySide2.QtWidgets import QAction  # noqa: F401
except ImportError:
    from PySide6 import QtWidgets, QtCore, QtGui  # noqa: F401
    from PySide6.QtGui import QAction  # noqa: F401

try:
    from shiboken6 import wrapInstance, isValid  # type: ignore
except ImportError:
    from shiboken2 import wrapInstance, isValid  # type: ignore


from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from maya.OpenMayaUI import MQtUtil  # type: ignore

from .flow_layout import FlowLayout
from .widgets import WaitingSpinner, ClickableLabel, EmptyStateWidget, ScrollableMenu
from .styles import (
    JOB_WIDGET_STYLE,
    STUDIO_WIDGET_STYLE,
    GLOBAL_STYLE,
    NO_RESULTS_STYLE,
    SCROLL_AREA_STYLE,
    LOCATION_STYLE,
    TITLE_STYLE,
)

from ..core.logger import logger
from ..utils.maya_utils import get_maya_main_window
from ..utils.updater import check_remote_version, format_relative_time
from .. import resources

from .. import VERSION, TOOL_TITLE


class JobWidget(QtWidgets.QFrame):
    clicked = QtCore.Signal()

    def __init__(self, job_data, parent=None):
        super(JobWidget, self).__init__(parent)
        self.job_data = job_data

        # Min properties to wrap content snugly
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)

        # Native borders
        self.setFrameStyle(QtWidgets.QFrame.Box | QtWidgets.QFrame.Plain)
        self.setStyleSheet(JOB_WIDGET_STYLE)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(2)

        # Title
        self.title_label = QtWidgets.QLabel(job_data.get("title", "Unknown"))
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet(TITLE_STYLE)
        layout.addWidget(self.title_label)

        # Location (Cleaned)
        raw_loc = job_data.get("location", "")
        if raw_loc and "," in raw_loc:
            clean_loc = raw_loc.split(",")[0].strip()
        elif raw_loc:
            clean_loc = raw_loc.strip()
        else:
            clean_loc = ""

        self.location_label = QtWidgets.QLabel(clean_loc)
        self.location_label.setWordWrap(True)
        self.location_label.setStyleSheet(LOCATION_STYLE)

        # Bottom row: Location (left) + Extra Buttons (right)
        bottom_layout = QtWidgets.QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)

        # Location takes all space possible (stretch=1)
        bottom_layout.addWidget(self.location_label, 1)
        # If location is hidden, we still need a stretch to push buttons to the right
        if not clean_loc:
            bottom_layout.addStretch(1)

        # Extra Link Button (e.g. PDF)
        extra_link = job_data.get("extra_link")
        if extra_link:
            self.extra_link_btn = QtWidgets.QPushButton()
            self.extra_link_btn.setIcon(resources.get_icon("info.svg"))
            self.extra_link_btn.setToolTip("Open Job Info Link")
            self.extra_link_btn.setFixedSize(20, 20)
            self.extra_link_btn.setCursor(QtCore.Qt.PointingHandCursor)
            self.extra_link_btn.clicked.connect(
                lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(extra_link))
            )
            bottom_layout.addWidget(self.extra_link_btn)

        self.clicked.connect(self.open_link)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setToolTip("Open Job Link")

        layout.addLayout(bottom_layout)

        if not clean_loc:
            self.location_label.hide()

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and self.rect().contains(event.pos()):
            self.clicked.emit()
            event.accept()
        super(JobWidget, self).mouseReleaseEvent(event)

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

        # Outline / Style
        self.setStyleSheet(STUDIO_WIDGET_STYLE)

        self.setFixedWidth(260)  # Fixed width for grid, dynamic height
        self.setMinimumHeight(220)
        self.setMaximumHeight(220)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # -- Header: Centered Logo/Name with balanced spacing --
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setContentsMargins(5, 5, 5, 0)
        header_layout.setSpacing(0)

        # Balancing spacer on the left (matches controls width)
        header_layout.addSpacing(30)
        header_layout.addStretch()

        # Logo/Name (Centered)
        self.logo_label = ClickableLabel()
        self.logo_label.setStyleSheet("font-weight: bold; border: none;")
        self.logo_label.setAlignment(QtCore.Qt.AlignCenter)
        self.logo_label.setFixedSize(120, 35)
        self.logo_label.setWordWrap(True)
        self.logo_label.clicked.connect(self.open_careers_page)
        self.logo_label.setToolTip("Open %s Careers Page" % studio_data.get("name"))
        self.logo_label.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.logo_label.customContextMenuRequested.connect(self.show_context_menu)

        header_layout.addWidget(self.logo_label)
        header_layout.addStretch()

        # Controls container (Refresh/Spinner)
        self.controls_container = QtWidgets.QWidget()
        self.controls_container.setFixedSize(30, 30)
        controls_layout = QtWidgets.QStackedLayout(self.controls_container)
        controls_layout.setStackingMode(QtWidgets.QStackedLayout.StackAll)

        self.refresh_btn = QtWidgets.QPushButton()
        self.refresh_btn.setIcon(resources.get_icon("refresh.svg"))
        self.refresh_btn.setIconSize(QtCore.QSize(20, 20))
        self.refresh_btn.setFlat(True)
        self.refresh_btn.setFixedSize(25, 25)
        self.refresh_btn.clicked.connect(self.fetch_jobs)
        self.refresh_btn.setStyleSheet("border: none; margin: 0; padding: 0;")
        self.refresh_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.refresh_btn.setToolTip("Refresh Jobs")

        self.spinner = WaitingSpinner()
        self.spinner.setFixedSize(25, 25)
        self.spinner.hide()

        controls_layout.addWidget(self.refresh_btn)
        controls_layout.addWidget(self.spinner)

        header_layout.addWidget(self.controls_container)
        layout.addLayout(header_layout)

        # -- Body: Vertical Scroll of Jobs --
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)

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
        self.config_manager.jobs_failed.connect(self.on_jobs_failed)
        self.config_manager.jobs_started.connect(self.on_jobs_started)

    def open_careers_page(self):
        url = self.studio_data.get("website") or self.studio_data.get("careers_url")
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

        menu.exec_(self.logo_label.mapToGlobal(pos))

    def open_edit_dialog(self):
        from .studio_dialog import StudioDialog

        dialog = StudioDialog(self.studio_data, self)
        if dialog.exec_():
            # Delay update to avoid hard crash in Maya when parent widget is destroyed from child dialog signal
            QtCore.QTimer.singleShot(10, lambda: self.config_manager.update_studio(dialog.studio_data))

    def load_logo(self):
        sid = self.studio_data.get("id")
        path = self.config_manager.get_logo_path(sid)

        if path and os.path.exists(path):
            pix = QtGui.QPixmap(path)
            if not pix.isNull():
                self.logo_label.setPixmap(
                    pix.scaled(110, 30, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                )
                return

        # Fallback to name text
        self.logo_label.setText(self.studio_data.get("name") or self.studio_data.get("id"))

    def fetch_jobs(self):
        self.refresh_btn.setToolTip("Refreshing...")
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
            self.scroll_area.setEnabled(False)

    def on_jobs_updated(self, sid, jobs):
        if sid == self.studio_data.get("id"):
            self.update_jobs()
            self.spinner.hide()

            # Use different icon if no jobs found
            icon_name = "success.svg" if jobs else "empty.svg"
            self.refresh_btn.setIcon(resources.get_icon(icon_name))

            self.refresh_btn.setToolTip(
                f"Found {len(jobs)} job{'' if len(jobs) == 1 else 's'} for {self.studio_data['name']}"
            )
            self.refresh_btn.show()
            self.scroll_area.setEnabled(True)

    def on_jobs_failed(self, sid, error_message):
        if sid == self.studio_data.get("id"):
            self.spinner.hide()
            self.refresh_btn.setIcon(resources.get_icon("error.svg"))

            # Clean up complex requests/urllib3 error messages
            # e.g. "Max retries exceeded... (Caused by NameResolutionError(...: Failed to resolve '...'))"
            # Extract the part after the last colon if it's a "Caused by" error
            cleaned_msg = error_message
            if "Caused by" in error_message:
                # Try to find the most specific error message inside the nested exception
                match = re.search(r"[:]\s*([^:]+)\s*['\"]?\)\s*\)\s*$", error_message)
                if match:
                    cleaned_msg = match.group(1).strip()
                else:
                    parts = error_message.split(":")
                    if len(parts) > 1:
                        cleaned_msg = parts[-1].strip().strip("')\" ")

            self.refresh_btn.setToolTip(f"Error: {cleaned_msg}")
            self.refresh_btn.show()
            self.scroll_area.setEnabled(True)

    def update_jobs(self):
        # Clear existing
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

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

    def filter_jobs(self, pattern_or_regex):
        """
        Filters job widgets based on a string pattern or pre-compiled regex.
        Returns the number of matching jobs.
        """
        match_count = 0
        if isinstance(pattern_or_regex, str):
            try:
                regex = re.compile(pattern_or_regex, re.IGNORECASE)
            except re.error:
                regex = re.compile(re.escape(pattern_or_regex), re.IGNORECASE)
        else:
            regex = pattern_or_regex

        for w in self.job_widgets:
            title = w.job_data.get("title", "")
            if regex.search(title):
                w.show()
                match_count += 1
            else:
                w.hide()

        if self.no_match_label:
            if match_count == 0 and len(self.job_widgets) > 0:
                # Use pattern string for label if available
                display_text = (
                    pattern_or_regex.pattern if not isinstance(pattern_or_regex, str) else pattern_or_regex
                )
                self.no_match_label.setText(f'No jobs matching "{display_text}"')
                self.no_match_label.show()
            else:
                self.no_match_label.hide()

        return match_count


class MainWindow(MayaQWidgetDockableMixin, QtWidgets.QMainWindow):
    TOOL_OBJECT_NAME = TOOL_TITLE.replace(" ", "")
    WINDOW_TITLE = "{} v{}".format(TOOL_TITLE, VERSION)
    WORKSPACE_CONTROL_NAME = "{}WorkspaceControl".format(TOOL_OBJECT_NAME)

    def __init__(self, parent=None):
        from ..utils.maya_utils import MAYA_AVAILABLE

        if MAYA_AVAILABLE:
            pass

        super(MainWindow, self).__init__(parent=parent)
        self.setWindowTitle(self.WINDOW_TITLE)
        self.setObjectName(self.TOOL_OBJECT_NAME)
        self.resize(1100, 800)
        self.setStyleSheet(GLOBAL_STYLE)

        # Native config
        from ..core.config_manager import ConfigManager

        self.settings = QtCore.QSettings("JobUI", "MainWindow")

        # Load settings
        self.config_manager = ConfigManager()
        self.studio_widgets = []
        self.menu_studio_actions = {}

        # Filter: On by default
        val = self.settings.value("only_show_with_jobs")
        if val is None:
            self._only_show_with_jobs = True
        else:
            self._only_show_with_jobs = val if isinstance(val, bool) else (str(val).lower() == "true")

        # Auto-refresh timer
        self.auto_refresh_timer = QtCore.QTimer(self)
        self.auto_refresh_timer.timeout.connect(self.config_manager.fetch_all_jobs)
        self.refresh_intervals = [
            ("Never", None),
            ("10 sec", 10 * 1000),
            ("30 sec", 30 * 1000),
            ("1 min", 60 * 1000),
            ("5 min", 5 * 60 * 1000),
            ("10 min", 10 * 60 * 1000),
            ("1 hour", 60 * 60 * 1000),
            ("6 hours", 6 * 60 * 60 * 1000),
        ]

        self.setup_ui()

        # Restore search text
        last_search = self.settings.value("last_search", "")
        if last_search:
            self.search_input.setText(last_search)

        # Restore refresh interval
        last_interval = self.settings.value("refresh_interval_index", 0)
        try:
            self.refresh_combo.setCurrentIndex(int(last_interval))
        except (ValueError, TypeError):
            self.refresh_combo.setCurrentIndex(0)

        self.refresh_studios_list()

        self.config_manager.studio_visibility_changed.connect(self.on_studio_visibility_changed)
        self.config_manager.studios_visibility_changed.connect(self._do_search)
        self.config_manager.studios_refreshed.connect(self.refresh_studios_list)
        self.config_manager.jobs_updated.connect(self._on_jobs_updated_signal)

        # Debounce timer for search
        self.search_timer = QtCore.QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(250)
        self.search_timer.timeout.connect(self._do_search)

        # Debounce timer for saving search settings
        self.save_search_timer = QtCore.QTimer()
        self.save_search_timer.setSingleShot(True)
        self.save_search_timer.setInterval(1000)
        self.save_search_timer.timeout.connect(self._save_search_text)

        # Fetch all on startup
        QtCore.QTimer.singleShot(500, self.config_manager.fetch_all_jobs)

    def setup_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_layout = QtWidgets.QVBoxLayout(central)

        # -- Top Bar --
        top_bar = QtWidgets.QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        top_bar.setSpacing(8)

        # Search Box
        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setPlaceholderText("Filter jobs (Text or Regex)...")
        self.search_input.textChanged.connect(self.on_search_changed)
        top_bar.addWidget(self.search_input, 1)  # Stretch factor 1

        # Hide Empty Checkbox
        self.hide_empty_cb = QtWidgets.QCheckBox("Hide Empty")
        self.hide_empty_cb.setChecked(self._only_show_with_jobs)
        self.hide_empty_cb.toggled.connect(self.toggle_only_show_with_jobs)
        top_bar.addWidget(self.hide_empty_cb)

        # Auto-refresh
        refresh_label = QtWidgets.QLabel("Auto-Refresh")
        top_bar.addWidget(refresh_label)

        self.refresh_combo = QtWidgets.QComboBox()
        for label, _ in self.refresh_intervals:
            self.refresh_combo.addItem(label)
        self.refresh_combo.currentIndexChanged.connect(self.on_refresh_interval_changed)
        top_bar.addWidget(self.refresh_combo)

        # Separator
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.VLine)
        top_bar.addWidget(sep)

        # Fetch All Button
        self.fetch_all_btn = QtWidgets.QPushButton("Refetch All")
        self.fetch_all_btn.setObjectName("fetch_all_btn")
        self.fetch_all_btn.setIcon(resources.get_icon("refresh.svg"))
        self.fetch_all_btn.clicked.connect(self.config_manager.fetch_all_jobs)
        top_bar.addWidget(self.fetch_all_btn)

        main_layout.addLayout(top_bar)

        # -- Main Content (Scroll of Studios) --
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scroll_area.setStyleSheet(SCROLL_AREA_STYLE)

        # Use a StackedWidget to switch between Grid and Placeholder
        self.content_stack = QtWidgets.QStackedWidget()

        self.studios_container = QtWidgets.QWidget()
        self.studios_layout = FlowLayout(self.studios_container, margin=10)
        self.content_stack.addWidget(self.studios_container)

        self.empty_state_widget = EmptyStateWidget()
        self.empty_state_widget.actionRequested.connect(self._on_empty_state_action)
        self.empty_state_widget.set_loading()
        self.content_stack.addWidget(self.empty_state_widget)

        self.content_stack.setCurrentWidget(self.empty_state_widget)
        self.scroll_area.setWidget(self.content_stack)
        main_layout.addWidget(self.scroll_area)

        # Menu (Keeping menu for manual refresh of cached images if needed)
        self.setup_menu()

    def setup_menu(self):
        menubar = self.menuBar()

        self.studios_menu = ScrollableMenu("Studios", self)
        self.studios_menu.aboutToShow.connect(self.populate_studios_menu)
        menubar.addMenu(self.studios_menu)

        # Populate immediately so it isn't empty (which might prevent opening)
        self.populate_studios_menu()

        opts = menubar.addMenu("Options")

        act_add = QAction("Add Studio...", self)
        act_add.triggered.connect(self.open_add_studio_dialog)
        act_add.setIcon(resources.get_icon("add.svg"))
        opts.addAction(act_add)

        opts.addSeparator()

        act = QAction("Refresh All Logos", self)
        act.triggered.connect(self.confirm_refresh_logos)
        opts.addAction(act)

        # Help Menu
        help_menu = menubar.addMenu("Help")

        act_updates = help_menu.addAction("Check for Updates")
        act_updates.triggered.connect(self.check_for_updates)
        act_updates.setIcon(resources.get_icon("refresh.svg"))

        help_menu.addSeparator()

        act_about = help_menu.addAction("About")
        act_about.triggered.connect(self.show_coffee)
        act_about.setIcon(resources.get_icon("info.svg"))

    def populate_studios_menu(self):
        try:
            self.studios_menu.clear()
            self.menu_studio_actions = {}
        except RuntimeError:
            return

        studios = self.config_manager.get_studios()
        # Sort by name for easier navigation
        sorted_studios = sorted(studios, key=lambda s: s.get("name", "").lower())

        current_letter = None

        for studio in sorted_studios:
            sid = studio.get("id")
            name = studio.get("name", sid)

            # Alpha Separator
            if name:
                first = name[0].upper()
                if not first.isalpha():
                    first = "#"

                if first != current_letter:
                    current_letter = first
                    self.studios_menu.addSection(current_letter)

            # Escape ampersands for Qt menu mnemonics
            display_name = name.replace("&", "&&")
            act = QAction(display_name, self)
            act.setCheckable(True)
            is_enabled = self.config_manager.is_studio_enabled(sid)
            act.setChecked(is_enabled)

            # Use closure to capture sid
            def make_handler(s_id):
                return lambda checked: self.config_manager.set_studio_enabled(s_id, checked)

            act.triggered.connect(make_handler(sid))

            # ScrollableMenu.addAction puts it inside the scroll area
            self.studios_menu.addAction(act)
            self.menu_studio_actions[sid] = act

        if sorted_studios:
            # Add separators and global actions outside the scroll area using QtWidgets.QMenu directly
            QtWidgets.QMenu.addSeparator(self.studios_menu)

            enable_all = QAction("Enable All", self.studios_menu)
            enable_all.triggered.connect(self.config_manager.enable_all_studios)
            enable_all.setIcon(resources.get_icon("dot.svg"))
            QtWidgets.QMenu.addAction(self.studios_menu, enable_all)

            disable_all = QAction("Disable All", self.studios_menu)
            disable_all.triggered.connect(self.config_manager.disable_all_studios)
            disable_all.setIcon(resources.get_icon("dot.svg"))
            QtWidgets.QMenu.addAction(self.studios_menu, disable_all)

            self.studios_menu.search_input.setPlaceholderText("Search %s studios..." % len(sorted_studios))

        else:
            self.studios_menu.setEnabled(False)
            self.studios_menu.setToolTip("Add studios to enable this menu")

    def update_studios_menu_checks(self):
        """Updates the checked state of studio actions in the menu."""
        for sid, act in self.menu_studio_actions.items():
            if isValid(act):
                act.setChecked(self.config_manager.is_studio_enabled(sid))

    def toggle_only_show_with_jobs(self, checked):
        self._only_show_with_jobs = checked
        if hasattr(self, "hide_empty_cb") and self.hide_empty_cb.isChecked() != checked:
            self.hide_empty_cb.setChecked(checked)
        self.settings.setValue("only_show_with_jobs", checked)
        self._do_search()

    def on_refresh_interval_changed(self, index):
        label, ms = self.refresh_intervals[index]
        self.auto_refresh_timer.stop()
        if ms is not None:
            self.auto_refresh_timer.start(ms)
            logger.info(f"Auto-refresh set to {label}")
        else:
            logger.info("Auto-refresh disabled")

        self.settings.setValue("refresh_interval_index", index)

    def confirm_refresh_logos(self):
        """Shows a warning before deleting all cached logos."""
        res = QtWidgets.QMessageBox.warning(
            self,
            "Refresh All Logos",
            "This will delete all cached studio logos and re-download them.\n\nAre you sure you want to proceed?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        if res == QtWidgets.QMessageBox.Yes:
            self.config_manager.refresh_logos()

    def open_add_studio_dialog(self):
        from .studio_dialog import StudioDialog

        dialog = StudioDialog(parent=self)
        if dialog.exec_():
            QtCore.QTimer.singleShot(10, lambda: self.config_manager.add_studio(dialog.studio_data))

    def on_studio_added(self, studio_data):
        self.config_manager.add_studio(studio_data)

    def on_studio_visibility_changed(self, studio_id, enabled):
        for sw in self.studio_widgets:
            if sw.studio_data.get("id") == studio_id:
                sw.setVisible(enabled)
                self._do_search()
                return

    def _update_placeholders(self, visible_count=0, enabled_count=0, search_text=""):
        """Updates the visibility and state of the empty state widget."""
        studios = self.config_manager.get_studios()
        num_studios = len(studios)
        has_enabled = any(self.config_manager.is_studio_enabled(s.get("id")) for s in studios)

        if num_studios == 0:
            self.empty_state_widget.set_no_studios()
            self.content_stack.setCurrentWidget(self.empty_state_widget)
        elif not has_enabled:
            self.empty_state_widget.set_no_enabled_studios()
            self.content_stack.setCurrentWidget(self.empty_state_widget)
        elif visible_count == 0:
            # Check if we have ANY jobs cached at all in enabled studios.
            # This helps distinguish between 'Just started' and 'Found nothing'.
            total_jobs_cached = sum(
                len(self.config_manager.get_studio_jobs(s.get("id")) or [])
                for s in studios
                if self.config_manager.is_studio_enabled(s.get("id"))
            )

            if search_text.strip():
                self.empty_state_widget.set_no_results(search_text)
            elif total_jobs_cached == 0:
                # If we have enabled studios but haven't seen a single job yet,
                # keep showing the loading state (unless it's a search)
                self.empty_state_widget.set_loading()
            else:
                self.empty_state_widget.set_no_jobs_found()

            self.content_stack.setCurrentWidget(self.empty_state_widget)
        else:
            # At least one studio is visible in the flow layout
            self.content_stack.setCurrentWidget(self.studios_container)

    def _on_empty_state_action(self, primary=True):
        """Unified handler for actions from the empty state widget."""
        studios = self.config_manager.get_studios()
        num_studios = len(studios)
        has_enabled = any(self.config_manager.is_studio_enabled(s.get("id")) for s in studios)
        search_text = self.search_input.text().strip()

        if num_studios == 0:
            self.open_add_studio_dialog()
        elif not has_enabled:
            if primary:
                # Enable all studios
                self.config_manager.enable_all_studios()
            else:
                # Open studios menu
                self.studios_menu.exec_(QtGui.QCursor.pos())
        elif search_text:
            self.search_input.clear()
        else:
            self.config_manager.fetch_all_jobs()

    def refresh_studios_list(self):
        # Helper to clear layout widgets
        # We want to preserve our placeholder widget instead of deleting it
        while self.studios_layout.count():
            item = self.studios_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self.studio_widgets = []
        studios = self.config_manager.get_studios()
        # Sort by name to match the menu and provide consistent UI
        sorted_studios = sorted(studios, key=lambda s: s.get("name", "").lower())

        for studio in sorted_studios:
            is_enabled = self.config_manager.is_studio_enabled(studio.get("id"))
            sw = StudioWidget(studio, self.config_manager)
            self.studios_layout.addWidget(sw)
            self.studio_widgets.append(sw)
            if not is_enabled:
                sw.hide()

        self._do_search()
        self._update_placeholders()

        logger.info(f"Loaded {len(studios)} studios.")

    def on_search_changed(self, text):
        if not isValid(self):
            return
        if hasattr(self, "search_timer") and self.search_timer:
            self.search_timer.start()
        if hasattr(self, "save_search_timer") and self.save_search_timer:
            self.save_search_timer.start()

    def _save_search_text(self):
        if not isValid(self) or not isValid(self.search_input):
            return
        self.settings.setValue("last_search", self.search_input.text())
        logger.info("Search text saved to settings.")

    def _on_jobs_updated_signal(self, sid, jobs):
        """Signal handler for jobs being ready."""
        if isValid(self):
            self._do_search()

    def _do_search(self):
        if not isValid(self) or not isValid(self.search_input):
            return

        text = self.search_input.text()
        visible_count = 0
        enabled_count = 0

        # Pre-compile regex once for all studios
        try:
            regex = re.compile(text, re.IGNORECASE)
        except re.error:
            regex = re.compile(re.escape(text), re.IGNORECASE)

        for sw in self.studio_widgets:
            match_count = sw.filter_jobs(regex)

            # Check primary enabled state
            sid = sw.studio_data.get("id")
            is_enabled = self.config_manager.is_studio_enabled(sid)

            if is_enabled:
                enabled_count += 1
                if self._only_show_with_jobs and match_count == 0:
                    sw.hide()
                else:
                    sw.show()
                    visible_count += 1
            else:
                sw.hide()

        self._update_placeholders(visible_count, enabled_count, text)
        self.update_studios_menu_checks()

        self.studios_layout.invalidate()
        self.studios_layout.activate()

    def show_coffee(self):
        credits_dialog = QtWidgets.QMessageBox(self)
        # credits_dialog.setWindowFlags(self.windowFlags() & Qt.FramelessWindowHint)

        base64Data = "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"
        image_64_decode = decodebytes(base64Data.encode("utf-8"))
        image = QtGui.QImage()
        image.loadFromData(image_64_decode, "JPG")
        pixmap = QtGui.QPixmap(image).scaledToHeight(56, QtCore.Qt.SmoothTransformation)
        credits_dialog.setIconPixmap(pixmap)
        credits_dialog.setWindowTitle("About")
        credits_dialog.setText(
            "Created by @Alehaaaa<br>"
            'Website - <a href=https://alehaaaa.github.io><font color="white">alehaaaa.github.io</a><br>'
            '<a href=https://www.linkedin.com/in/alejandro-martin-407527215><font color="white">Linkedin</a> - <a href=https://www.instagram.com/alejandro_anim><font color="white">Instagram</a>'
            "<br><br>"
            "If you liked this tool,<br>"
            "you can send me some love!"
        )
        credits_dialog.setFixedSize(400, 300)
        exec_fn = getattr(credits_dialog, "exec", None) or getattr(credits_dialog, "exec_", None)
        exec_fn()

    def check_for_updates(self):
        remote_ver, remote_date = check_remote_version()
        rel_time = format_relative_time(remote_date)
        date_info = " ({})".format(rel_time) if rel_time else ""

        if remote_ver and VERSION < remote_ver:
            QtWidgets.QMessageBox.information(
                self,
                "Update Available",
                "A new version ({}) is available! released {}.\nYou are currently using v{}.\n\nPlease check the repository.".format(
                    remote_ver, rel_time or "recently", VERSION
                ),
            )
        elif remote_ver and VERSION > remote_ver:
            QtWidgets.QMessageBox.information(
                self,
                "Unreleased Version",
                "You are using an unreleased version v{}\nThe last release was v{}{}.".format(
                    VERSION, remote_ver, date_info
                ),
            )
        elif remote_ver and VERSION == remote_ver:
            QtWidgets.QMessageBox.information(
                self,
                "Up to Date",
                "You are using the latest version v{}{}".format(VERSION, date_info),
            )
        else:
            QtWidgets.QMessageBox.warning(
                self,
                "Check Failed",
                "Could not retrieve update information.\nPlease check your internet connection.",
            )

    def set_windowPosition(self):
        """
        Restores or initializes the dock/floating position of the workspace control.
        """
        settings = QtCore.QSettings("JobUI", "MainWindow")

        # Helper for bool setting
        val = settings.value("floating")
        floating = val if isinstance(val, bool) else (str(val).lower() == "true")

        logger.info("Restoring floating = {}".format(floating))
        position = settings.value("position")
        size = settings.value("size")

        kwargs = {
            "e": True,
            "label": self.WINDOW_TITLE,
            "minimumWidth": 370,
            "retain": False,
        }

        # If floating, restore previous floating geometry
        if floating:
            kwargs["floating"] = True

        else:
            # Try to dock next to a known panel
            dock_target = None
            for ctl in ("ChannelBoxLayerEditor", "AttributeEditor"):
                if cmds.workspaceControl(ctl, exists=True):
                    dock_target = ctl
                    break

            if dock_target:
                kwargs["tabToControl"] = [dock_target, -1]
                logger.info("Docking to: {}".format(dock_target))
            else:
                logger.info("No valid dock target found; defaulting to floating.")
                kwargs["floating"] = True

        try:
            cmds.workspaceControl(self.WORKSPACE_CONTROL_NAME, **kwargs)
        except Exception as e:
            logger.error("Error positioning workspace control: {}".format(e))

        try:
            if floating and position and size:
                ptr = MQtUtil.findControl(self.WORKSPACE_CONTROL_NAME)
                qt_control = wrapInstance(int(ptr), QtWidgets.QWidget).window()

                logger.info("Setting workspace control position: {}".format(position))
                logger.info("Setting workspace control size: {}".format(size))
                qt_control.setGeometry(
                    QtCore.QRect(int(position[0]), int(position[1]), int(size[0]), int(size[1]))
                )
        except Exception as e:
            logger.error("Error setting workspace control geometry: {}".format(e))

    def save_windowPosition(self):
        """
        Saves the current window state (floating or docked), position, and size.
        """
        settings = QtCore.QSettings("JobUI", "MainWindow")

        # Save Search and Filter state
        settings.setValue("last_search", self.search_input.text())
        settings.setValue("only_show_with_jobs", self._only_show_with_jobs)

        try:
            if not cmds.workspaceControl(self.WORKSPACE_CONTROL_NAME, exists=True):
                logger.warning("No workspace control found to save position.")
                return

            # Check if the workspace control is floating or docked
            floating = cmds.workspaceControl(self.WORKSPACE_CONTROL_NAME, q=True, floating=True)
            logger.info("Workspace control is {}".format("floating" if floating else "docked"))

            if floating:
                ptr = MQtUtil.findControl(self.WORKSPACE_CONTROL_NAME)
                qt_control = wrapInstance(int(ptr), QtWidgets.QWidget)
                geo = qt_control.geometry()
                top_left_global = qt_control.mapToGlobal(geo.topLeft())

                position = (top_left_global.x(), top_left_global.y())
                size = (geo.width(), geo.height())

                settings.setValue("position", position)
                settings.setValue("size", size)

                settings.setValue("floating", True)
                logger.info("Saved floating = {} position {} size {}".format(True, position, size))
            else:
                settings.setValue("floating", False)
                logger.info("Saved floating = {}".format(False))

            settings.sync()  # Force settings to write immediately
            logger.info("Window position saved successfully.")

        except Exception as e:
            logger.error("Error saving window position: {}".format(e))

    def _cleanup(self):
        # Stop timers
        if hasattr(self, "search_timer") and self.search_timer.isActive():
            self.search_timer.stop()
        if hasattr(self, "save_search_timer") and self.save_search_timer.isActive():
            self.save_search_timer.stop()

        if self.config_manager:
            # Disconnect signals to prevent callbacks to a deleted UI
            try:
                self.config_manager.studio_visibility_changed.disconnect(self.on_studio_visibility_changed)
                self.config_manager.studios_refreshed.disconnect(self.refresh_studios_list)
                self.config_manager.jobs_updated.disconnect(self._on_jobs_updated_signal)
            except (RuntimeError, TypeError):
                pass

            self.config_manager.cleanup()

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
