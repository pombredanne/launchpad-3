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


LOG_GROWTH_WAIT_INTERVAL = datetime.timedelta(seconds=5)
SECONDS_TO_SNOOZE = 0.1


class LogWatcher:
    """Watch logs/xmlrpc and wait until a pattern has been seen."""
    def __init__(self, filename='xmlrpc'):
        # Import this here since sys.path isn't set up properly when this
        # module is imported.
        # pylint: disable-msg=F0401
        self._log_path = os.path.join(LOG_DIR, filename)
        self._log_file = open(self._log_path)

    def _wait_for_string(self, landmark):
        """Wait until the landmark string has been seen.

        'landmark' must appear on a single line.  Comparison is done with 'in'
        on each line of the file.
        """
        until = datetime.datetime.now() + LOG_GROWTH_WAIT_INTERVAL
        while True:
            line = self._log_file.readline()
            if landmark in line:
                # Return None on success for doctest convenience.
                return None
            if datetime.datetime.now() > until:
                return 'Timed out'
            time.sleep(SECONDS_TO_SNOOZE)

    def wait_for_create(self, team_name):
        """Wait for the list creation message."""
        self._wait_for_string('[%s] create/reactivate: success' % team_name)

    def wait_for_resynchronization(self, team_name):
        self._wait_for_string('[%s] resynchronize: success' % team_name)
