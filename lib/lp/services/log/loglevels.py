# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Standard and custom log levels from the standard logging package.

Custom log levels are registered in lp_sitecustomize.py.
"""

__metaclass__ = type
__all__ = [
    'CRITICAL',
    'DEBUG',
    'DEBUG2',
    'DEBUG3',
    'DEBUG4',
    'DEBUG5',
    'DEBUG6',
    'DEBUG7',
    'DEBUG8',
    'DEBUG9',
    'INFO',
    'ERROR',
    'WARNING',
    ]

# Standard log levels.
from logging import (
    CRITICAL,
    DEBUG,
    INFO,
    ERROR,
    WARNING,
    )

# Custom log levels.
DEBUG2 = DEBUG - 1
DEBUG3 = DEBUG - 2
DEBUG4 = DEBUG - 3
DEBUG5 = DEBUG - 4
DEBUG6 = DEBUG - 5
DEBUG7 = DEBUG - 6
DEBUG8 = DEBUG - 7
DEBUG9 = DEBUG - 8
