# pylint: disable=invalid-name
"""
Common types and enumerations which are used by everything.
"""
from enum import Enum


class BaseCommand(Enum):
    """
    Base class for Command enumerations

    Tuples, in the form of:
        (command_class, command_id, data_length)
    """
