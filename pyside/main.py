import sys
import os

# Ensure the package is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    from .ui.main_window import MainWindow
    from .utils.maya_utils import get_maya_main_window
except (ImportError, ValueError):
    from ui.main_window import MainWindow
    from utils.maya_utils import get_maya_main_window


def run():
    parent = get_maya_main_window()
    global jobui_window
    jobui_window = MainWindow(parent)
    jobui_window.show()
    return jobui_window


if __name__ == "__main__":
    run()
