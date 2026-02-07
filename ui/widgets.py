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

    actionRequested = QtCore.Signal(bool)

    def __init__(self, parent=None):
        super(EmptyStateWidget, self).__init__(parent)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setObjectName("EmptyStateWidget")
        self.setStyleSheet("""
            #EmptyStateWidget {
                background-color: transparent;
            }
            QPushButton {
                background-color: #4d4d4d;
                color: #ddd;
                font-weight: bold;
                border: 1px solid #666;
                border-radius: 6px;
                padding: 0 20px;
            }
            QPushButton:hover {
                background-color: #555;
                border-color: #777;
                color: #fff;
            }
            QPushButton:pressed {
                background-color: #444;
                border-color: #5d5d5d;
            }
        """)

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

        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.setAlignment(QtCore.Qt.AlignCenter)
        buttons_layout.setSpacing(12)

        # Action Button
        self.btn = QtWidgets.QPushButton()
        self.btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn.setFixedHeight(36)
        self.btn.setFixedWidth(200)
        self.btn.clicked.connect(lambda: self.actionRequested.emit(True))
        buttons_layout.addWidget(self.btn)

        # Secondary Action Button
        self.secondary_btn = QtWidgets.QPushButton()
        self.secondary_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.secondary_btn.setFixedHeight(36)
        self.secondary_btn.setFixedWidth(40)
        self.secondary_btn.setVisible(False)
        self.secondary_btn.clicked.connect(lambda: self.actionRequested.emit(False))
        buttons_layout.addWidget(self.secondary_btn)

        layout.addLayout(buttons_layout)

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
        self.secondary_btn.setVisible(False)

    def set_no_studios(self):
        """Configure for 'no studios added'."""
        self.icon_lbl.setPixmap(resources.get_icon("info.svg").pixmap(100, 100))
        self.title_lbl.setText("No studios setup")
        self.desc_lbl.setText("It looks like you haven't added any studios yet. Add some to start tracking jobs!")
        self.btn.setText("Add New Studio")
        self.btn.setIcon(resources.get_icon("add.svg"))
        self.btn.setVisible(True)
        self.secondary_btn.setVisible(False)

    def set_no_enabled_studios(self):
        """Configure for 'no studios enabled'."""
        self.icon_lbl.setPixmap(resources.get_icon("eye_off.svg").pixmap(100, 100))
        self.title_lbl.setText("No studios enabled")
        self.desc_lbl.setText(
            "You have studios added, but none are enabled.\nEnable All or Manage which ones are active."
        )
        self.btn.setText("Enable All")
        self.btn.setToolTip("Enable All Studios")
        self.btn.setStatusTip("Enable All Studios")
        self.btn.setIcon(resources.get_icon("eye.svg"))
        # Button action could be to open the menu, but for now we'll just keep it visible
        self.btn.setVisible(True)

        self.secondary_btn.setToolTip("Manage Studios")
        self.secondary_btn.setStatusTip("Manage Studios")
        self.secondary_btn.setIcon(resources.get_icon("edit.svg"))
        self.secondary_btn.setVisible(True)

    def set_no_jobs_found(self):
        """Configure for 'no jobs found in enabled studios'."""
        self.icon_lbl.setPixmap(resources.get_icon("empty.svg").pixmap(100, 100))
        self.title_lbl.setText("No jobs found")
        self.desc_lbl.setText("None of your enabled studios have any active jobs listed at the moment.")
        self.btn.setText("Refresh All")
        self.btn.setToolTip("Refresh All Studios")
        self.btn.setStatusTip("Refresh All Studios")
        self.btn.setIcon(resources.get_icon("refresh.svg"))
        self.btn.setVisible(True)
        self.secondary_btn.setVisible(False)

    def set_loading(self):
        """Configure for initial loading state."""
        self.icon_lbl.setPixmap(resources.get_icon("refresh.svg").pixmap(100, 100))
        self.title_lbl.setText("Checking for jobs...")
        self.desc_lbl.setText("We're reaching out to studio career pages to find the latest opportunities for you.")
        self.btn.setVisible(False)
        self.secondary_btn.setVisible(False)


# -------------------- Scrollable Menu --------------------


class ScrollArrowButton(QtWidgets.QWidget):
    """Custom button for hover-based scrolling in ScrollableMenu."""

    def __init__(self, arrow_type, menu):
        super(ScrollArrowButton, self).__init__(menu)
        self.arrow_type = arrow_type
        self.menu = menu
        self.setFixedHeight(16)
        self.setMouseTracking(True)
        self.hovered = False
        self.pressed = False
        self.hide()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        if self.pressed:
            bg_color = QtGui.QColor(35, 35, 35, 230)
        elif self.hovered:
            bg_color = QtGui.QColor(65, 65, 65, 230)
        else:
            bg_color = QtGui.QColor(40, 40, 40, 180)
        painter.fillRect(self.rect(), bg_color)

        painter.setPen(
            QtGui.QPen(
                QtGui.QColor(180, 180, 180),
                2.0,
                QtCore.Qt.SolidLine,
                QtCore.Qt.RoundCap,
                QtCore.Qt.RoundJoin,
            )
        )

        cx = self.width() / 2.0
        cy = self.height() / 2.0
        size = 3.5

        path = QtGui.QPainterPath()
        if self.arrow_type == QtCore.Qt.UpArrow:
            path.moveTo(cx - size, cy + size * 0.35)
            path.lineTo(cx, cy - size * 0.35)
            path.lineTo(cx + size, cy + size * 0.35)
        else:
            path.moveTo(cx - size, cy - size * 0.35)
            path.lineTo(cx, cy + size * 0.35)
            path.lineTo(cx + size, cy - size * 0.35)

        painter.drawPath(path)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.pressed = True
            self.update()
        super(ScrollArrowButton, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.pressed = False
            self.update()
            vbar = self.menu._scroll_area.verticalScrollBar()
            if self.arrow_type == QtCore.Qt.UpArrow:
                vbar.setValue(0)
            else:
                vbar.setValue(vbar.maximum())
            self.menu._update_arrows()
            return
        super(ScrollArrowButton, self).mouseReleaseEvent(event)

    def enterEvent(self, event):
        self.hovered = True
        self.menu._start_scroll(-1 if self.arrow_type == QtCore.Qt.UpArrow else 1)
        self.update()

    def leaveEvent(self, event):
        self.hovered = False
        self.menu._stop_scroll()
        self.update()


class ScrollContainer(QtWidgets.QWidget):
    """Container that positions scroll arrows as overlays."""

    def __init__(self, scroll_area, up_btn, down_btn):
        super(ScrollContainer, self).__init__()
        self.scroll_area = scroll_area
        self.up_btn = up_btn
        self.down_btn = down_btn

        self.up_btn.setParent(self)
        self.down_btn.setParent(self)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.scroll_area)

    def resizeEvent(self, event):
        super(ScrollContainer, self).resizeEvent(event)
        w = self.width()
        h = self.height()
        self.up_btn.setGeometry(0, 0, w, 16)
        self.down_btn.setGeometry(0, h - 16, w, 16)
        self.up_btn.raise_()
        self.down_btn.raise_()


class MenuItemWidget(QtWidgets.QWidget):
    """Custom widget representing a single checkable menu item."""

    WIDGET_HEIGHT = 20
    CHECKBOX_SIZE = 12
    CONTENT_PADDING = 6
    EXTRA_LEFT_MARGIN = 1

    def __init__(self, action, menu):
        super(MenuItemWidget, self).__init__()
        self.action = action
        self.menu = menu
        self._hovered = False
        self.setFixedHeight(self.WIDGET_HEIGHT)
        self.setMouseTracking(True)

        if self.action:
            self.action.changed.connect(self.update)
            self.action.toggled.connect(lambda _: self.update())

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        h = float(self.WIDGET_HEIGHT)
        cs = float(self.CHECKBOX_SIZE)
        margin_y = (h - cs) / 2.0
        margin_x = margin_y + self.EXTRA_LEFT_MARGIN
        column_w = int(h) + self.EXTRA_LEFT_MARGIN

        checkbox_bg_rect = self.rect()
        checkbox_bg_rect.setWidth(column_w)
        text_bg_rect = self.rect().adjusted(column_w, 0, 0, 0)

        # Draw Checkbox Column Background
        painter.fillRect(checkbox_bg_rect, QtGui.QColor(64, 64, 64))

        # Draw Text Area Background
        if self._hovered:
            painter.fillRect(text_bg_rect, QtGui.QColor(82, 133, 166))
        else:
            painter.fillRect(text_bg_rect, QtGui.QColor(82, 82, 82))

        # Checkbox
        if self.action and self.action.isCheckable():
            check_rect = QtCore.QRectF(margin_x, margin_y, cs, cs)
            painter.fillRect(check_rect, QtGui.QColor(43, 43, 43))

            if self.action.isChecked():
                painter.setPen(QtGui.QPen(QtGui.QColor(200, 200, 200), 1.8))
                lx = check_rect.x() + cs * 0.22
                ly = check_rect.y() + cs * 0.5
                mx = check_rect.x() + cs * 0.43
                my = check_rect.y() + cs * 0.72
                rx = check_rect.x() + cs * 0.78
                ry = check_rect.y() + cs * 0.28
                painter.drawLine(QtCore.QPointF(lx, ly), QtCore.QPointF(mx, my))
                painter.drawLine(QtCore.QPointF(mx, my), QtCore.QPointF(rx, ry))

        text_offset = column_w + self.CONTENT_PADDING
        icon = self.action.icon() if self.action else QtGui.QIcon()
        if not icon.isNull():
            icon_size = 16
            icon_y = (h - icon_size) / 2.0
            icon.paint(painter, QtCore.QRect(int(text_offset), int(icon_y), icon_size, icon_size))
            text_offset += 24

        painter.setPen(QtGui.QColor(238, 238, 238))
        font = (self.action.font() if self.action else self.font()) or self.font()
        painter.setFont(font)

        text_rect = self.rect().adjusted(int(text_offset), 0, -10, 0)
        painter.drawText(text_rect, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, self.get_text())

    def get_text(self):
        return self.action.text() if self.action else ""

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()

    def mouseReleaseEvent(self, event):
        if not self.action:
            return
        self.action.trigger()

    def sizeHint(self):
        fm = self.fontMetrics()
        txt = self.get_text()
        text_w = fm.horizontalAdvance(txt) if hasattr(fm, "horizontalAdvance") else fm.width(txt)
        offset = self.WIDGET_HEIGHT + 1 + self.CONTENT_PADDING
        icon = self.action.icon() if self.action else QtGui.QIcon()
        if not icon.isNull():
            offset += 24
        return QtCore.QSize(text_w + int(offset) + 20, self.WIDGET_HEIGHT)


class ManageItemWidget(MenuItemWidget):
    """Custom widget for ScrollableMenu that mimics MenuItemWidget but adds a remove button."""

    def __init__(self, text, remove_callback, menu):
        super(ManageItemWidget, self).__init__(None, menu)
        self._text = text

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 4, 0)
        layout.addStretch()

        self.btn = QtWidgets.QPushButton()
        self.btn.setIcon(resources.get_icon("trash.svg"))
        self.btn.setIconSize(QtCore.QSize(10, 10))
        self.btn.setFixedSize(16, 16)
        self.btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn.setToolTip("Remove this instance")
        self.btn.setStyleSheet(
            "QPushButton { border: none; background: rgba(0, 0, 0, 0.2); border-radius: 8px; } QPushButton:hover { background: rgba(255, 255, 255, 0.1); }"
        )
        self.btn.clicked.connect(remove_callback)
        layout.addWidget(self.btn)

    def get_text(self):
        return self._text


class SearchLineEdit(QtWidgets.QLineEdit):
    """A QLineEdit that enforces IBeam cursor within a QMenu."""

    def __init__(self, *args, **kwargs):
        super(SearchLineEdit, self).__init__(*args, **kwargs)
        self.setCursor(QtCore.Qt.IBeamCursor)

    def mouseMoveEvent(self, event):
        # Force the cursor again just in case the parent menu tries to reset it
        if self.cursor().shape() != QtCore.Qt.IBeamCursor:
            self.setCursor(QtCore.Qt.IBeamCursor)
        super(SearchLineEdit, self).mouseMoveEvent(event)


class ScrollableMenu(OpenMenu):
    """
    A QMenu that embeds a QScrollArea.
    Includes a Search Box and Alpha Separators support.
    """

    def __init__(self, title=None, parent=None, max_height=400):
        super(ScrollableMenu, self).__init__(title, parent)
        self._added_actions = []

        self.setStyleSheet("QMenu { background: #404040; padding: 0px; }")
        self.setContentsMargins(0, 0, 0, 0)

        # Search Box
        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("Search for studios...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._on_search_changed)

        search_container = QtWidgets.QWidget()
        search_layout = QtWidgets.QVBoxLayout(search_container)
        search_layout.setContentsMargins(4, 4, 4, 4)
        search_layout.addWidget(self.search_input)

        self._search_action = QtWidgets.QWidgetAction(self)
        self._search_action.setDefaultWidget(search_container)
        super(ScrollableMenu, self).addAction(self._search_action)

        # Scroll Area
        self._scroll_area = QtWidgets.QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        self._scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self._scroll_area.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        self._scroll_area.setMaximumHeight(max_height)

        self._scroll_area.verticalScrollBar().valueChanged.connect(lambda _: self._update_arrows())

        self._content_widget = QtWidgets.QWidget()
        self._content_layout = QtWidgets.QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)
        self._scroll_area.setWidget(self._content_widget)

        self._up_btn = ScrollArrowButton(QtCore.Qt.UpArrow, self)
        self._down_btn = ScrollArrowButton(QtCore.Qt.DownArrow, self)
        self._container = ScrollContainer(self._scroll_area, self._up_btn, self._down_btn)

        self._main_action = QtWidgets.QWidgetAction(self)
        self._main_action.setDefaultWidget(self._container)
        super(ScrollableMenu, self).addAction(self._main_action)

        self._scroll_timer = QtCore.QTimer(self)
        self._scroll_timer.timeout.connect(self._do_scroll)
        self._scroll_speed = 0

    def clear(self):
        for action in self.actions():
            if action not in [self._search_action, self._main_action]:
                self.removeAction(action)

        self._added_actions = []
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._scroll_area.verticalScrollBar().setValue(0)
        self._update_arrows()
        self.search_input.clear()

    def _start_scroll(self, direction):
        self._scroll_speed = direction * 10
        self._scroll_timer.start(16)

    def _stop_scroll(self):
        self._scroll_timer.stop()

    def _do_scroll(self):
        vbar = self._scroll_area.verticalScrollBar()
        vbar.setValue(vbar.value() + self._scroll_speed)
        self._update_arrows()

    def _update_arrows(self):
        vbar = self._scroll_area.verticalScrollBar()
        self._up_btn.setVisible(vbar.value() > 0)
        self._down_btn.setVisible(vbar.value() < vbar.maximum())

    def addAction(self, action):
        if isinstance(action, str):
            action = QtWidgets.QAction(action, self)

        if not isinstance(action, QtWidgets.QWidgetAction):
            self._added_actions.append(action)
            wid = MenuItemWidget(action, self)
            self._content_layout.addWidget(wid)
            QtCore.QTimer.singleShot(0, self._update_arrows)
            return action
        return super(ScrollableMenu, self).addAction(action)

    def addSection(self, text):
        lbl = QtWidgets.QLabel(text)
        lbl.setFixedHeight(MenuItemWidget.WIDGET_HEIGHT)
        lbl.setStyleSheet(
            "font-weight: bold; font-size: 10px; background-color: #353535; color: #9f9f9f; padding-left: 10px;"
        )
        self._content_layout.addWidget(lbl)
        return lbl

    def actions(self):
        return super(ScrollableMenu, self).actions()

    def _calculate_content_size(self):
        """Calculates the needed size for the custom scrollable widgets."""
        # Optimization: Calculate height/width by iterating items to avoid full layout pass
        total_height = 0
        max_width = 150

        for i in range(self._content_layout.count()):
            item = self._content_layout.itemAt(i)
            w = item.widget()
            if w and w.isVisible():
                total_height += w.sizeHint().height()
                max_width = max(max_width, w.sizeHint().width())

        # Limit height of the scrollable area
        scroll_h = min(total_height, self._scroll_area.maximumHeight())

        w = max_width + 10
        return w, scroll_h

    def showEvent(self, event):
        w, scroll_h = self._calculate_content_size()

        # Resize the container action to fit content
        self._container.setFixedHeight(scroll_h)
        self._container.setFixedWidth(w)

        # Also ensure search box matches this width
        self._search_action.defaultWidget().setFixedWidth(w)

        # We typically don't set self.setFixedSize on the QMenu itself
        # if we want it to autosize for other actions (Enable All).
        # However, we should ensure minimum width so truncation doesn't happen.
        self.setMinimumWidth(w)

        super(ScrollableMenu, self).showEvent(event)

        # Force menu to resize to fit the new container size
        self.adjustSize()

        QtCore.QTimer.singleShot(0, self._update_arrows)

    def _on_search_changed(self, text):
        text = text.lower()
        current_header = None

        # Optimize rendering by disabling updates during bulk visibility changes
        self._content_widget.setUpdatesEnabled(False)
        try:
            for i in range(self._content_layout.count()):
                item = self._content_layout.itemAt(i)
                w = item.widget()

                if isinstance(w, QtWidgets.QLabel):
                    current_header = w
                    # If searching, hide initially until we find a match in filter
                    w.setVisible(not text)

                elif isinstance(w, MenuItemWidget):
                    txt = w.get_text().lower()
                    is_match = text in txt
                    w.setVisible(is_match)

                    # If we have a match, show the header for this section
                    if is_match and current_header and text:
                        current_header.setVisible(True)
        finally:
            self._content_widget.setUpdatesEnabled(True)

        QtCore.QTimer.singleShot(0, self._resize_after_filter)

    def _resize_after_filter(self):
        w, scroll_h = self._calculate_content_size()
        self._container.setFixedHeight(scroll_h)
        self.adjustSize()
        self._update_arrows()
