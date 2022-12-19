import sys
import logging

LOGGER_NAME = "krak_app"


def _configure_logger(logger_name: str, file_name: str) -> logging.Logger:
    _logger = logging.getLogger(logger_name)
    _logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(formatter)
    _logger.handlers.clear()
    _logger.addHandler(sh)

    fh = logging.FileHandler(file_name, mode='w')
    fh.setFormatter(formatter)
    _logger.addHandler(fh)
    return _logger


logger = _configure_logger(LOGGER_NAME, "krak_app.log")


def get_logger(module_name: str):
    return logging.getLogger(LOGGER_NAME).getChild(module_name)
