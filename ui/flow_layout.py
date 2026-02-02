try:
    from PySide2 import QtCore, QtWidgets
except ImportError:
    from PySide6 import QtCore, QtWidgets


class FlowLayout(QtWidgets.QLayout):
    def __init__(self, parent=None, margin=-1, hSpacing=-1, vSpacing=-1):
        super(FlowLayout, self).__init__(parent)
        self._hSpace = hSpacing
        self._vSpace = vSpacing
        self._itemList = []
        self.setContentsMargins(margin, margin, margin, margin)

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self._itemList.append(item)

    def horizontalSpacing(self):
        if self._hSpace >= 0:
            return self._hSpace
        else:
            return self.smartSpacing(QtWidgets.QStyle.PM_LayoutHorizontalSpacing)

    def verticalSpacing(self):
        if self._vSpace >= 0:
            return self._vSpace
        else:
            return self.smartSpacing(QtWidgets.QStyle.PM_LayoutVerticalSpacing)

    def count(self):
        return len(self._itemList)

    def itemAt(self, index):
        if 0 <= index < len(self._itemList):
            return self._itemList[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._itemList):
            return self._itemList.pop(index)
        return None

    def expandingDirections(self):
        return QtCore.Qt.Orientations(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self.doLayout(QtCore.QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super(FlowLayout, self).setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QtCore.QSize()
        for item in self._itemList:
            size = size.expandedTo(item.minimumSize())
        size += QtCore.QSize(2 * self.contentsMargins().top(), 2 * self.contentsMargins().top())
        return size

    def doLayout(self, rect, testOnly):
        left, top, right, bottom = self.getContentsMargins()
        effectiveRect = rect.adjusted(+left, +top, -right, -bottom)
        x = effectiveRect.x()
        y = effectiveRect.y()
        lineHeight = 0

        for item in self._itemList:
            wid = item.widget()
            if wid and not wid.isVisible():
                continue

            spaceX = self.horizontalSpacing()
            if spaceX == -1:
                spaceX = QtWidgets.QApplication.style().layoutSpacing(
                    QtWidgets.QSizePolicy.PushButton, QtWidgets.QSizePolicy.PushButton, QtCore.Qt.Horizontal
                )
            spaceY = self.verticalSpacing()
            if spaceY == -1:
                spaceY = QtWidgets.QApplication.style().layoutSpacing(
                    QtWidgets.QSizePolicy.PushButton, QtWidgets.QSizePolicy.PushButton, QtCore.Qt.Vertical
                )

            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > effectiveRect.right() and lineHeight > 0:
                x = effectiveRect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QtCore.QRect(QtCore.QPoint(x, y), item.sizeHint()))

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y() + bottom

    def smartSpacing(self, pm):
        parent = self.parent()
        if not parent:
            return -1
        elif parent.isWidgetType():
            # Use safe global style to avoid QProxyStyle deleted errors
            return QtWidgets.QApplication.style().pixelMetric(pm, None, parent)
        else:
            return parent.spacing()
