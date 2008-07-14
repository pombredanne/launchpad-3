# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Watch a log file and wait until it has grown in size."""

__metaclass__ = type
__all__ = [
    'LogWatcher',
    ]


import os
import time
import datetime

from Mailman.mm_cfg import LOG_DIR
from canonical.launchpad.mailman.testing.helpers import get_size


LOG_GROWTH_WAIT_INTERVAL = datetime.timedelta(seconds=5)
SECONDS_TO_SNOOZE = 0.1


class LogWatcher:
    """Watch a log file and wait until it has grown in size."""
    def __init__(self, log_file):
        # Import this here since sys.path isn't set up properly when this
        # module is imported.
        # pylint: disable-msg=F0401
        self._log_path = os.path.join(LOG_DIR, log_file)
        self._last_size = get_size(self._log_path)

    def wait(self):
        """Wait for a while, or until the file has grown."""
        until = datetime.datetime.now() + LOG_GROWTH_WAIT_INTERVAL
        while True:
            size = get_size(self._log_path)
            if size > self._last_size:
                # Return None on success for doctest convenience.
                self._last_size = size
                return None
            if datetime.datetime.now() > until:
                return 'Timed out'
            time.sleep(SECONDS_TO_SNOOZE)

    def resync(self):
        """Re-sync the file size so that we can watch it again."""
        self._last_size = get_size(self._log_path)
