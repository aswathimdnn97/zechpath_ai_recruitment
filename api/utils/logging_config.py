import logging
from pathlib import Path


# ============================================================
# PATH CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

LOG_DIR = BASE_DIR / "logs"

LOG_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

LOG_FILE = LOG_DIR / "ats_api.log"


# ============================================================
# LOG FORMAT
# ============================================================

LOG_FORMAT = (
    "%(asctime)s | "
    "%(levelname)s | "
    "%(name)s | "
    "%(message)s"
)


# ============================================================
# CONFIGURE LOGGER
# ============================================================

def configure_logging() -> None:
    """
    Configure centralized ATS application logging.

    Logs are written to:
        logs/ats_api.log

    and also displayed in the console.
    """

    root_logger = logging.getLogger()

    # Prevent duplicate handlers when the application
    # is reloaded by the development server.
    if root_logger.handlers:
        return

    root_logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        LOG_FORMAT
    )

    # --------------------------------------------------------
    # Console Handler
    # --------------------------------------------------------

    console_handler = logging.StreamHandler()

    console_handler.setLevel(
        logging.INFO
    )

    console_handler.setFormatter(
        formatter
    )

    # --------------------------------------------------------
    # File Handler
    # --------------------------------------------------------

    file_handler = logging.FileHandler(
        LOG_FILE,
        encoding="utf-8",
    )

    file_handler.setLevel(
        logging.INFO
    )

    file_handler.setFormatter(
        formatter
    )

    # --------------------------------------------------------
    # Register handlers
    # --------------------------------------------------------

    root_logger.addHandler(
        console_handler
    )

    root_logger.addHandler(
        file_handler
    )