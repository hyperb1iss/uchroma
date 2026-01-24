#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
import logging
import threading
from typing import ClassVar

# Trace log levels
LOG_TRACE = 5
LOG_PROTOCOL_TRACE = 4

# ─────────────────────────────────────────────────────────────────────────────
# SilkCircuit Neon Palette — ANSI RGB
# ─────────────────────────────────────────────────────────────────────────────
_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"

# Log level colors
_LEVEL_COLORS = {
    logging.DEBUG: "\033[38;2;128;255;234m",  # Neon Cyan
    logging.INFO: "\033[38;2;80;250;123m",  # Success Green
    logging.WARNING: "\033[38;2;241;250;140m",  # Electric Yellow
    logging.ERROR: "\033[38;2;255;99;99m",  # Error Red
    logging.CRITICAL: "\033[38;2;225;53;255m",  # Electric Purple
    LOG_TRACE: "\033[38;2;128;255;234m",  # Neon Cyan (dim)
    LOG_PROTOCOL_TRACE: "\033[38;2;106;193;255m",  # Coral-ish
}


class SilkCircuitFormatter(logging.Formatter):
    """Log formatter using SilkCircuit Neon color palette."""

    def format(self, record: logging.LogRecord) -> str:
        color = _LEVEL_COLORS.get(record.levelno, _RESET)
        levelname = record.levelname.ljust(8)

        return f" {color}{record.name}/{levelname}{_RESET} | {color}{record.getMessage()}{_RESET}"


class PlainFormatter(logging.Formatter):
    """Plain log formatter without colors."""

    def format(self, record: logging.LogRecord) -> str:
        levelname = record.levelname.ljust(8)
        return f" {record.name}/{levelname} | {record.getMessage()}"


class Log:
    """
    Logging module

    Call get() to get a cached instance of a specific logger.
    Colored output can optionally be enabled.
    """

    _LOGGERS: ClassVar[dict] = {}
    _use_color = False
    _lock = threading.Lock()

    @classmethod
    def get(cls, tag):
        """
        Get the global logger instance for the given tag

        :param tag: the log tag
        :return: the logger instance
        """
        with cls._lock:
            if tag not in cls._LOGGERS:
                if cls._use_color:
                    handler = logging.StreamHandler()
                    handler.setFormatter(SilkCircuitFormatter())
                else:
                    handler = logging.StreamHandler()
                    handler.setFormatter(PlainFormatter())

                logger = logging.getLogger(tag)
                logger.addHandler(handler)

                cls._LOGGERS[tag] = logger

            return cls._LOGGERS[tag]

    @classmethod
    def enable_color(cls, enable):
        """
        Enable colored output for loggers. Must be called before
        any loggers are initialized with get()
        """
        cls._use_color = enable
