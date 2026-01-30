import sys
import os
import io

try:
    import importlib
except ImportError:
    importlib = None

TOOL_TITLE = "JobUI"
MOD_NAME = __name__

# Expose version
try:
    _v_path = os.path.join(os.path.dirname(__file__), "VERSION")
    with io.open(_v_path, "rb") as _f:
        _content = _f.read()
        try:
            VERSION = _content.decode("utf-8").strip()
        except UnicodeDecodeError:
            VERSION = _content.decode("utf-16").strip()
except Exception:
    VERSION = "0.0.0"


def show(mod_name=MOD_NAME):
    # Determine the top-level package name to reload
    # code might be imported as "pyside" or "JobsUI"
    pass

    # Reloading logic
    # We want to remove submodules from sys.modules to force reload
    for name in list(sys.modules.keys()):
        if name == mod_name or name.startswith(mod_name + "."):
            sys.modules.pop(name, None)

    if importlib and hasattr(importlib, "invalidate_caches"):
        importlib.invalidate_caches()
        # Import the package again
        importlib.import_module(mod_name)
        # Import main
        main_mod = importlib.import_module(mod_name + ".main")
    else:
        __import__(mod_name)
        main_mod = __import__(mod_name + ".main", fromlist=["main"])

    # Run the app
    if hasattr(main_mod, "run"):
        return main_mod.run()
    else:
        print(f"Error: {mod_name}.main has no 'run' function")


if __name__ == "__main__":
    show()
