# config/logger.py - logger configuration module
import logging
from config.settings import Settings, Path, sys, Optional


class CustomFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    green = "\x1b[32;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format_str = '%(asctime)s | %(levelname)-8s | %(filename)-30s:%(lineno)-4d | %(message)s'
    FORMATS = {
        logging.DEBUG: grey + format_str + reset,
        logging.INFO: green + format_str + reset,
        logging.WARNING: yellow + format_str + reset,
        logging.ERROR: red + format_str + reset,
        logging.CRITICAL: bold_red + format_str + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


LOG_FORMAT_FILE = '%(asctime)s | %(levelname)-8s | %(filename)-30s:%(lineno)-4d | %(message)s'

_global_logger_config = {
    'log_file': None,
    'log_level': logging.INFO,
    'initialized': False
}


def setup_global_logging(debug: bool = False, log_file: Optional[Path] = None) -> Path:
    """Configure the global logging system"""
    if Settings.Initialize_LOG:
        return _global_logger_config['log_file']

    log_level = logging.DEBUG if debug else logging.INFO
    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Create the log file
    if log_file is None:
        log_file = Settings.LOGS_DIR / Settings.LOG_FILE_NAME

        # Clear existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    console_handler.setFormatter(CustomFormatter())

    # file handler
    file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        LOG_FORMAT_FILE,
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)

    # add handlers to root logger
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    Settings.Initialize_LOG = True
    _global_logger_config.update({
        'log_file': log_file,
        'log_level': log_level,
        'initialized': True
    })

    init_logger = logging.getLogger(__name__)
    init_logger.info("=" * 80)
    init_logger.info("Global logging system initialized complete")
    init_logger.info(f"Log file: {log_file}")
    init_logger.info(f"Log level: {logging.getLevelName(log_level)}")
    init_logger.info("=" * 80)

    return log_file


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name
    All loggers obtained through this function will output to the same log file
    """
    # Ensure the logging system is initialized
    if not Settings.Initialize_LOG:
        setup_global_logging()

    logger = logging.getLogger(name)
    return logger
