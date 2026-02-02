import logging
import sys

# Global toggle for logging. If False, only ERROR level logs will be shown.
LOGGING = False

logger = logging.getLogger("JobUI")

# Prevent double logging if the module is reloaded
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False

# Set level based on LOGGING toggle
if LOGGING:
    logger.setLevel(logging.INFO)
else:
    logger.setLevel(logging.ERROR)
