try:
    from core.logger import logger
except (ImportError, ValueError):
    import logging

    logger = logging.getLogger("JobUI")

try:
    import maya.OpenMayaUI as omui

    MAYA_AVAILABLE = True
except ImportError:
    MAYA_AVAILABLE = False

try:
    from PySide2 import QtWidgets
except ImportError:
    from PySide6 import QtWidgets

try:
    from shiboken2 import wrapInstance
except ImportError:
    try:
        from shiboken6 import wrapInstance
    except ImportError:

        def wrapInstance(ptr, base):
            return None


def get_maya_main_window():
    """
    Return the Maya main window as a QWidget instance.
    """
    if not MAYA_AVAILABLE:
        return None

    try:
        ptr = omui.MQtUtil.mainWindow()
        if ptr:
            return wrapInstance(int(ptr), QtWidgets.QWidget)
    except Exception as e:
        logger.error(f"Error getting Maya main window: {e}")

    return None
