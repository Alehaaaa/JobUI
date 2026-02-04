try:
    from PySide2 import QtWidgets, QtCore, QtGui
except ImportError:
    from PySide6 import QtWidgets, QtCore, QtGui

from .. import resources


class WaitingSpinner(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(WaitingSpinner, self).__init__(parent)
        self.setFixedSize(25, 25)
        self._angle = 0
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self._timer.start(50)

    def _rotate(self):
        self._angle = (self._angle + 30) % 360
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.translate(self.width() / 2, self.height() / 2)
        painter.rotate(self._angle)
        painter.setPen(QtGui.QPen(QtGui.QColor("#bdbdbd"), 2))
        # Draw arc
        painter.drawArc(-6, -6, 12, 12, 0, 270 * 16)
        painter.end()


class ClickableLabel(QtWidgets.QLabel):
    clicked = QtCore.Signal()

    def __init__(self, parent=None):
        super(ClickableLabel, self).__init__(parent)
        self.setCursor(QtCore.Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit()
        super(ClickableLabel, self).mousePressEvent(event)


class OpenMenu(QtWidgets.QMenu):
    def __init__(self, title=None, parent=None):
        super(OpenMenu, self).__init__(title, parent) if title else super(OpenMenu, self).__init__(parent)
        self.setSeparatorsCollapsible(False)
        if parent and hasattr(parent, "destroyed"):
            parent.destroyed.connect(self.close)
        self.triggered.connect(self._on_action_triggered)

    def _on_action_triggered(self, action):
        if isinstance(action, QtWidgets.QWidgetAction):
            return

    def showEvent(self, event):
        self._show_time = QtCore.QDateTime.currentMSecsSinceEpoch()
        self._show_pos = QtGui.QCursor.pos()
        super(OpenMenu, self).showEvent(event)

    def mouseReleaseEvent(self, e):
        # Prevent accidental trigger if menu was just opened via QPushButton click
        # Ignoring release if it's within 200ms and mouse hasn't moved much
        if hasattr(self, "_show_time"):
            time_diff = QtCore.QDateTime.currentMSecsSinceEpoch() - self._show_time
            pos_diff = (QtGui.QCursor.pos() - self._show_pos).manhattanLength()
            if time_diff < 200 and pos_diff < 5:
                return

        action = self.actionAt(e.pos())
        if action and action.isEnabled():
            action.setEnabled(False)
            super(OpenMenu, self).mouseReleaseEvent(e)
            action.setEnabled(True)
            action.trigger()
        else:
            super(OpenMenu, self).mouseReleaseEvent(e)


class EmptyStateWidget(QtWidgets.QWidget):
    """A pretty and professional empty state overlay for the grid."""

    actionRequested = QtCore.Signal()

    def __init__(self, parent=None):
        super(EmptyStateWidget, self).__init__(parent)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setObjectName("EmptyStateWidget")
        self.setStyleSheet("#EmptyStateWidget { background-color: transparent; }")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setAlignment(QtCore.Qt.AlignCenter)
        layout.setSpacing(12)

        # Main Icon
        self.icon_lbl = QtWidgets.QLabel()
        self.icon_lbl.setAlignment(QtCore.Qt.AlignCenter)
        self.icon_lbl.setFixedSize(140, 140)
        self.icon_lbl.setStyleSheet("color: #444; background: transparent;")
        layout.addWidget(self.icon_lbl, 0, QtCore.Qt.AlignCenter)

        # Title
        self.title_lbl = QtWidgets.QLabel()
        self.title_lbl.setStyleSheet("font-size: 20pt; font-weight: bold; color: #fff;")
        self.title_lbl.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.title_lbl)

        # Description
        self.desc_lbl = QtWidgets.QLabel()
        self.desc_lbl.setStyleSheet("font-size: 11pt; color: #999;")
        self.desc_lbl.setAlignment(QtCore.Qt.AlignCenter)
        self.desc_lbl.setWordWrap(True)
        self.desc_lbl.setFixedWidth(450)
        layout.addWidget(self.desc_lbl, 0, QtCore.Qt.AlignCenter)

        # Spacer
        layout.addSpacing(15)

        # Action Button
        self.btn = QtWidgets.QPushButton()
        self.btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn.setFixedHeight(36)
        self.btn.setFixedWidth(200)
        self.btn.setStyleSheet("""
            QPushButton {
                background-color: #444;
                color: #eee;
                font-weight: bold;
                border: 1px solid #555;
                border-radius: 6px;
                padding: 0 20px;
            }
            QPushButton:hover {
                background-color: #555;
                border-color: #777;
                color: #fff;
            }
            QPushButton:pressed {
                background-color: #333;
            }
        """)
        self.btn.clicked.connect(self.actionRequested.emit)
        layout.addWidget(self.btn, 0, QtCore.Qt.AlignCenter)

    def set_no_results(self, search_text=""):
        """Configure for 'no search results found'."""
        self.icon_lbl.setPixmap(resources.get_icon("search.svg").pixmap(100, 100))
        self.title_lbl.setText("No matches found")
        if search_text:
            self.desc_lbl.setText(f'We couldn\'t find any jobs matching "{search_text}".')
        else:
            self.desc_lbl.setText("We couldn't find any jobs matching your current filters or search query.")
        self.btn.setText("Clear Search")
        self.btn.setIcon(resources.get_icon("trash.svg"))
        self.btn.setVisible(True)

    def set_no_studios(self):
        """Configure for 'no studios added'."""
        self.icon_lbl.setPixmap(resources.get_icon("info.svg").pixmap(100, 100))
        self.title_lbl.setText("No studios setup")
        self.desc_lbl.setText("It looks like you haven't added any studios yet. Add some to start tracking jobs!")
        self.btn.setText("Add New Studio")
        self.btn.setIcon(resources.get_icon("add.svg"))
        self.btn.setVisible(True)

    def set_no_enabled_studios(self):
        """Configure for 'no studios enabled'."""
        self.icon_lbl.setPixmap(resources.get_icon("eye_off.svg").pixmap(100, 100))
        self.title_lbl.setText("No studios enabled")
        self.desc_lbl.setText("You have studios added, but none are enabled. Enable them in the Studios menu.")
        self.btn.setText("Manage Studios")
        self.btn.setIcon(resources.get_icon("eye.svg"))
        # Button action could be to open the menu, but for now we'll just keep it visible
        self.btn.setVisible(True)

    def set_no_jobs_found(self):
        """Configure for 'no jobs found in enabled studios'."""
        self.icon_lbl.setPixmap(resources.get_icon("empty.svg").pixmap(100, 100))
        self.title_lbl.setText("No jobs found")
        self.desc_lbl.setText("None of your enabled studios have any active jobs listed at the moment.")
        self.btn.setText("Refresh All")
        self.btn.setIcon(resources.get_icon("refresh.svg"))
        self.btn.setVisible(True)

    def set_loading(self):
        """Configure for initial loading state."""
        self.icon_lbl.setPixmap(resources.get_icon("refresh.svg").pixmap(100, 100))
        self.title_lbl.setText("Checking for jobs...")
        self.desc_lbl.setText("We're reaching out to studio career pages to find the latest opportunities for you.")
        self.btn.setVisible(False)
