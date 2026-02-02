import sys
import os

# Add this directory to sys.path so 'core', 'ui', and 'utils' are importable as top-level modules.
# This fixes ModuleNotFoundError when the package is installed in a subdirectory (like Maya's scripts folder).
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Also ensure parent dir is available so the package itself remains importable
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from core.logger import LOGGING, logger  # noqa: E402

try:
    import importlib
except ImportError:
    importlib = None

__all__ = ["LOGGING", "logger", "show", "VERSION", "TOOL_TITLE"]

TOOL_TITLE = "Job Fetcher"
MOD_NAME = __name__


# Expose version
try:
    _v_path = os.path.join(current_dir, "VERSION")
    with open(_v_path, "r", encoding="utf-8") as _f:
        VERSION = _f.read().strip()
except Exception:
    VERSION = "0.0.0"


def show(mod_name=MOD_NAME, force_reload=True):
    if force_reload:
        # Recursive reload for submodules in this package
        for name in list(sys.modules.keys()):
            if name == mod_name or name.startswith(mod_name + "."):
                del sys.modules[name]

    if importlib and hasattr(importlib, "invalidate_caches"):
        importlib.invalidate_caches()

    try:
        # Re-import this package
        if mod_name not in sys.modules:
            importlib.import_module(mod_name)

        main_mod = importlib.import_module(mod_name + ".main")
        return main_mod.runner()
    except Exception as e:
        logger.error(f"Error launching {mod_name}: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    show()
