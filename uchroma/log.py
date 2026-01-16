#
# Copyright (C) 2026 UChroma Developers — LGPL-3.0-or-later
#
import logging
from typing import ClassVar

import colorlog
from wrapt import synchronized

# Trace log levels
LOG_TRACE = 5
LOG_PROTOCOL_TRACE = 4


class Log:
    """
    Logging module

    Call get() to get a cached instance of a specific logger.
    Colored output can optionally be enabled.
    """

    _LOGGERS: ClassVar[dict] = {}
    _use_color = False

    @synchronized
    @classmethod
    def get(cls, tag):
        """
        Get the global logger instance for the given tag

        :param tag: the log tag
        :return: the logger instance
        """
        if tag not in cls._LOGGERS:
            if cls._use_color:
                handler = colorlog.StreamHandler()
                handler.setFormatter(
                    colorlog.ColoredFormatter(
                        " %(log_color)s%(name)s/%(levelname)-8s%(reset)s |"
                        " %(log_color)s%(message)s%(reset)s"
                    )
                )
            else:
                handler = logging.StreamHandler()
                handler.setFormatter(logging.Formatter(" %(name)s/%(levelname)-8s | %(message)s"))

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
