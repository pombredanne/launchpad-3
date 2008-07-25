# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Watch a log file and wait until it has grown in size."""

__metaclass__ = type
__all__ = [
    'LogWatcher',
    'MHonArcWatcher',
    'SMTPDWatcher',
    'VetteWatcher',
    'XMLRPCWatcher',
    ]


import os
import time
import errno
import datetime

from Mailman.mm_cfg import LOG_DIR

try:
    # Python 2.5
    SEEK_END = os.SEEK_END
except AttributeError:
    # Python 2.4
    SEEK_END = 2


LOG_GROWTH_WAIT_INTERVAL = datetime.timedelta(seconds=5)
SECONDS_TO_SNOOZE = 0.1


class LogWatcher:
    """Watch logs/xmlrpc and wait until a pattern has been seen.

    You MUST open the LogWatcher before any data you're interested in could
    get written to the log.
    """
    FILENAME = None

    def __init__(self):
        # Import this here since sys.path isn't set up properly when this
        # module is imported.
        # pylint: disable-msg=F0401
        self._log_path = os.path.join(LOG_DIR, self.FILENAME)
        log_file = open(self._log_path, 'a+')
        try:
            print >> log_file, 'Watching'
        finally:
            log_file.close()
        self._log_file = open(self._log_path)
        self._log_file.seek(0, SEEK_END)

    def _wait(self, landmark):
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

    def close(self):
        self._log_file.close()


class XMLRPCWatcher(LogWatcher):
    """Watch logs/xmlrpc."""

    FILENAME = 'xmlrpc'

    def wait_for_create(self, team_name):
        """Wait for the list creation message."""
        return self._wait('[%s] create/reactivate: success' % team_name)

    def wait_for_resynchronization(self, team_name):
        return self._wait('[%s] resynchronize: success' % team_name)

    def wait_for_deactivation(self, team_name):
        return self._wait('[%s] deactivate: success' % team_name)

    def wait_for_reactivation(self, team_name):
        return self._wait('[%s] reactivate: success' % team_name)

    def wait_for_modification(self, team_name):
        return self._wait('[%s] modify: success' % team_name)

    def wait_for_discard(self, message_id):
        return self._wait('Discarded: <%s>' % message_id)

    def wait_for_reject(self, message_id):
        return self._wait('Rejected: <%s>' % message_id)

    def wait_for_approval(self, message_id):
        return self._wait('Approved: <%s>' % message_id)


class SMTPDWatcher(LogWatcher):
    """Watch logs/smtpd."""

    FILENAME = 'smtpd'

    def wait_for_mbox_delivery(self, message_id):
        return self._wait('msgid: <%s>' % message_id)

    def wait_for_list_traffic(self, team_name):
        return self._wait('to: %s@lists.launchpad.dev' % team_name)

    def wait_for_personal_traffic(self, address):
        return self._wait('to: ' + address)


class MHonArcWatcher(LogWatcher):
    """Watch logs/mhonarc."""

    FILENAME = 'mhonarc'

    def wait_for_message_number(self, n):
        return self._wait('%s total' % n)


class VetteWatcher(LogWatcher):
    """Watch logs/vette."""

    FILENAME = 'vette'

    def wait_for_discard(self, message_id):
        return self._wait('Message discarded, msgid: <%s>' % message_id)

    def wait_for_hold(self, message_id):
        return self._wait(
            'Holding message for LP approval: <%s>' % message_id)
