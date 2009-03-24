#!/usr/bin/python2.4
# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Database garbage collector.

Remove or archive unwanted data. Detect, warn and possibly repair data
corruption.
"""

__metaclass__ = type
__all__ = []

import _pythonpath
from canonical.launchpad.scripts.garbo import DailyDatabaseGarbageCollector

if __name__ == '__main__':
    script = DailyDatabaseGarbageCollector()
    script.lock_and_run()

