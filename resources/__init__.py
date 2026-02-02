import os

try:
    from PySide6 import QtGui
except ImportError:
    from PySide2 import QtGui

from ..core.logger import logger


# -------------------- Constants --------------------
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
ICONS_DIR = os.path.join(MODULE_DIR, "_icons")


def get_icon(file_name):
    """
    Returns a QIcon from the _icons directory.
    """
    if file_name:
        path = os.path.join(ICONS_DIR, file_name)
        if os.path.exists(path):
            return QtGui.QIcon(path)
    logger.warning("Icon not found: {}".format(file_name))
    return QtGui.QIcon()
