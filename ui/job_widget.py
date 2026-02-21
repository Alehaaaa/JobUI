from datetime import datetime

try:
    from PySide2 import QtWidgets, QtCore, QtGui
except ImportError:
    from PySide6 import QtWidgets, QtCore, QtGui

from .styles import JOB_WIDGET_STYLE, LOCATION_STYLE, TITLE_STYLE
from .. import resources

MAX_AGE_HIGHLIGHT_DAYS = 10
DAY_SECS = 86400


class JobWidget(QtWidgets.QFrame):
    clicked = QtCore.Signal()

    def __init__(self, job_data, parent=None):
        super(JobWidget, self).__init__(parent)
        self.job_data = job_data

        # 1. Process data (logic)
        self._process_data()

        # 2. Initialize widgets (texts/styles)
        self._init_ui()

        # 3. Assemble layouts
        self._init_layout()

    def _process_data(self):
        """Processes raw job data into usable strings and state."""
        # Location logic
        raw_loc = self.job_data.get("location", "")
        if raw_loc and "," in raw_loc:
            self.clean_loc = raw_loc.split(",")[0].strip()
        elif raw_loc:
            self.clean_loc = raw_loc.strip()
        else:
            self.clean_loc = ""

        # Timestamp logic
        self.first_seen_dt = None
        self.time_text = ""
        self.is_new = False
        self.age_seconds = 9999999  # Default to very old

        first_seen = self.job_data.get("first_seen")
        if first_seen:
            try:
                if isinstance(first_seen, (int, float)):
                    self.first_seen_dt = datetime.fromtimestamp(first_seen)
                elif isinstance(first_seen, str):
                    try:
                        try:
                            self.first_seen_dt = datetime.fromtimestamp(float(first_seen))
                        except ValueError:
                            self.first_seen_dt = datetime.fromisoformat(first_seen)
                    except ValueError:
                        pass

                if self.first_seen_dt:
                    delta = datetime.now() - self.first_seen_dt
                    self.age_seconds = int(delta.total_seconds())
                    if self.age_seconds < 0:
                        self.age_seconds = 0

                    if self.age_seconds < 3600:
                        self.time_text = "New"
                    elif self.age_seconds < DAY_SECS:
                        self.time_text = f"{self.age_seconds // 3600}h ago"
                    elif self.age_seconds < 7 * DAY_SECS:
                        self.time_text = f"{self.age_seconds // DAY_SECS}d ago"
                    else:
                        self.time_text = f"{self.age_seconds // (7 * DAY_SECS)}w ago"

                    if self.age_seconds <= MAX_AGE_HIGHLIGHT_DAYS * DAY_SECS:
                        self.is_new = True
            except Exception:
                pass

    def _init_ui(self):
        """Creates and styles widgets."""
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.setFrameStyle(QtWidgets.QFrame.Box | QtWidgets.QFrame.Plain)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setToolTip("Open Job Link")

        # Title
        self.title_label = QtWidgets.QLabel(self.job_data.get("title", "Unknown"))
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet(TITLE_STYLE)

        # Location
        self.location_label = QtWidgets.QLabel(self.clean_loc)
        self.location_label.setWordWrap(True)
        self.location_label.setStyleSheet(LOCATION_STYLE)
        if not self.clean_loc:
            self.location_label.hide()

        # Time Label
        self.time_label = None
        if self.time_text:
            self.time_label = QtWidgets.QLabel(self.time_text)
            self.time_label.setStyleSheet("color: #888; font-size: 10px; margin-right: 4px;")
            self.time_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            if self.first_seen_dt:
                tooltip_date = self.first_seen_dt.strftime("%d/%m/%Y at %H:%M")
                self.time_label.setToolTip(f"Job added {tooltip_date}")

        # Extra Link Button
        self.extra_link_btn = None
        extra_link = self.job_data.get("extra_link")
        if extra_link:
            self.extra_link_btn = QtWidgets.QPushButton()
            self.extra_link_btn.setIcon(resources.get_icon("info.svg"))
            self.extra_link_btn.setToolTip("Open Job Info Link")
            self.extra_link_btn.setFixedSize(20, 20)
            self.extra_link_btn.setCursor(QtCore.Qt.PointingHandCursor)
            self.extra_link_btn.clicked.connect(
                lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(extra_link))
            )

        # Dynamic Styling
        self.setStyleSheet(JOB_WIDGET_STYLE)

        # Dynamic Highlighting: Green (0%) -> Orange (50%) -> Red (80%) -> Grey (100%)
        max_secs = MAX_AGE_HIGHLIGHT_DAYS * DAY_SECS
        if self.is_new and self.age_seconds <= max_secs:
            # Hue Interpolation Targets (RGB)
            target_green = (76, 175, 80)
            target_orange = (255, 152, 0)
            target_red = (244, 67, 54)
            target_grey = (85, 85, 85)

            if self.age_seconds <= 0.5 * max_secs:
                # Stage 1: Green to Orange
                ratio = self.age_seconds / (0.5 * max_secs)
                c1, c2 = target_green, target_orange
            elif self.age_seconds <= 0.8 * max_secs:
                # Stage 2: Orange to Red
                ratio = (self.age_seconds - 0.5 * max_secs) / (0.3 * max_secs)
                c1, c2 = target_orange, target_red
            else:
                # Stage 3: Red to Grey
                ratio = min(1.0, (self.age_seconds - 0.8 * max_secs) / (0.2 * max_secs))
                c1, c2 = target_red, target_grey

            # Base Interpolated Color
            br = c1[0] + (c2[0] - c1[0]) * ratio
            bg = c1[1] + (c2[1] - c1[1]) * ratio
            bb = c1[2] + (c2[2] - c1[2]) * ratio

            # SATURATION DROP-OFF
            # Only brand new jobs (0h) are at 100% saturation of their target.
            # We fade saturation down to 40% over the first day.
            sat_ratio = min(1.0, self.age_seconds / DAY_SECS)
            vibrancy = 1.0 - (0.6 * sat_ratio)  # 1.0 -> 0.4

            # Blend base color with neutral grey (85, 85, 85) based on vibrancy
            r = int(br * vibrancy + 85 * (1 - vibrancy))
            g = int(bg * vibrancy + 85 * (1 - vibrancy))
            b = int(bb * vibrancy + 85 * (1 - vibrancy))

            border_color = f"rgb({r}, {g}, {b})"
            bg_alpha = 0.1 - (0.07 * (self.age_seconds / max_secs))

            # Text color (Always slightly brighter/closer to white for readability)
            tr = int(min(255, r + 40))
            tg = int(min(255, g + 40))
            tb = int(min(255, b + 40))
            text_color = f"rgb({tr}, {tg}, {tb})"

            highlight_style = f"""
                JobWidget {{
                    border: 1px solid {border_color};
                    background-color: rgba({r}, {g}, {b}, {bg_alpha});
                }}
                JobWidget:hover {{
                    background-color: rgba({r}, {g}, {b}, {bg_alpha + 0.05});
                    border-color: {border_color};
                }}
                QLabel {{
                    color: {text_color};
                }}
            """
            self.setStyleSheet(JOB_WIDGET_STYLE + highlight_style)

        self.clicked.connect(self.open_link)

    def _init_layout(self):
        """Assembles layouts."""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(2)

        main_layout.addWidget(self.title_label)

        bottom_layout = QtWidgets.QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)

        # Add components to bottom row
        bottom_layout.addWidget(self.location_label, 1)
        if not self.clean_loc:
            bottom_layout.addStretch(1)

        if self.time_label:
            bottom_layout.addWidget(self.time_label)

        if self.extra_link_btn:
            bottom_layout.addWidget(self.extra_link_btn)

        main_layout.addLayout(bottom_layout)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and self.rect().contains(event.pos()):
            self.clicked.emit()
            event.accept()
        super(JobWidget, self).mouseReleaseEvent(event)

    def open_link(self):
        link = self.job_data.get("link")
        if link:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl(str(link)))
