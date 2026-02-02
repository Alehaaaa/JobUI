try:
    from PySide2 import QtWidgets, QtCore, QtGui
except ImportError:
    from PySide6 import QtWidgets, QtCore, QtGui


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
        painter.setPen(QtGui.QPen(QtGui.QColor("#00bcd4"), 3))
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
