# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Standard and custom log levels from the standard logging package.

Custom log levels are registered in lp_sitecustomize.py.
"""

__metaclass__ = type
__all__ = [
    'CRITICAL',
    'DEBUG',
    'DEBUG1',
    'DEBUG2',
    'DEBUG3',
    'DEBUG4',
    'DEBUG5',
    'DEBUG6',
    'DEBUG7',
    'DEBUG8',
    'DEBUG9',
    'ERROR',
    'FATAL',
    'INFO',
    'LaunchpadLogger',
    'WARNING',
    ]


import logging


# Reexport standard log levels.
DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL
FATAL = logging.FATAL


# Custom log levels.
DEBUG1 = DEBUG
DEBUG2 = DEBUG - 1
DEBUG3 = DEBUG - 2
DEBUG4 = DEBUG - 3
DEBUG5 = DEBUG - 4
DEBUG6 = DEBUG - 5
DEBUG7 = DEBUG - 6
DEBUG8 = DEBUG - 7
DEBUG9 = DEBUG - 8


class LaunchpadLogger(logging.Logger):
    """Logger that support our custom levels."""

    def debug1(self, msg, *args, **kwargs):
        if self.isEnabledFor(DEBUG1):
            self._log(DEBUG1, msg, args, **kwargs)

    def debug2(self, msg, *args, **kwargs):
        if self.isEnabledFor(DEBUG2):
            self._log(DEBUG2, msg, args, **kwargs)

    def debug3(self, msg, *args, **kwargs):
        if self.isEnabledFor(DEBUG3):
            self._log(DEBUG3, msg, args, **kwargs)

    def debug4(self, msg, *args, **kwargs):
        if self.isEnabledFor(DEBUG4):
            self._log(DEBUG4, msg, args, **kwargs)

    def debug5(self, msg, *args, **kwargs):
        if self.isEnabledFor(DEBUG5):
            self._log(DEBUG5, msg, args, **kwargs)

    def debug6(self, msg, *args, **kwargs):
        if self.isEnabledFor(DEBUG6):
            self._log(DEBUG6, msg, args, **kwargs)

    def debug7(self, msg, *args, **kwargs):
        if self.isEnabledFor(DEBUG7):
            self._log(DEBUG7, msg, args, **kwargs)

    def debug8(self, msg, *args, **kwargs):
        if self.isEnabledFor(DEBUG8):
            self._log(DEBUG8, msg, args, **kwargs)

    def debug9(self, msg, *args, **kwargs):
        if self.isEnabledFor(DEBUG9):
            self._log(DEBUG9, msg, args, **kwargs)
