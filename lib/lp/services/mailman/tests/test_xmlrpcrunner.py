# Copyright 20011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
"""Test the Launchpad XMLRPC runner."""

__metaclass__ = type
__all__ = []

from contextlib import contextmanager
from datetime import datetime

from Mailman.Logging.Syslog import syslog
from Mailman.Queue.XMLRPCRunner import XMLRPCRunner

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.services.mailman.testing import (
     get_mailing_list_api_test_proxy,
     MailmanTestCase,
     )


@contextmanager
def one_loop_exception(runner):

    def raise_exception():
        raise Exception('Test exception handling.')

    original__check_list_actions = runner._check_list_actions
    runner._check_list_actions = raise_exception
    try:
        yield
    finally:
        runner._check_list_actions= original__check_list_actions


class TestXMLRPCRunnerHeatBeat(MailmanTestCase):
    """Test XMLRPCRunner._hearbeat method."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestXMLRPCRunnerHeatBeat, self).setUp()
        self.mm_list = None
        syslog.write_ex('xmlrpc', 'Ensure the log is open.')
        self.reset_log()
        self.runner = XMLRPCRunner()
        # MailmanTestCase's setup of the test proxy is ignored because
        # the runner had a reference to the true proxy in its __init__.
        self.runner._proxy = get_mailing_list_api_test_proxy()

    def get_mark(self):
        """Return the first mark line found in the log."""
        log_path = syslog._logfiles['xmlrpc']._Logger__filename
        mark = None
        with open(log_path, 'r') as log_file:
            for line in log_file.readlines():
                if '--MARK--' in line:
                    mark = line
                    break
        return mark

    def reset_log(self):
        """Truncate the log."""
        log_path = syslog._logfiles['xmlrpc']._Logger__filename
        syslog._logfiles['xmlrpc'].close()
        with open(log_path, 'w') as log_file:
            log_file.truncate()
        syslog.write_ex('xmlrpc', 'Reset by test.')

    def test_heartbeat_on_start(self):
        # A heartbeat is recorded in the log on start.
        mark = self.get_mark()
        self.assertTrue(mark is not None)

    def test_heatbeat_frequency_no_heartbeat(self):
        # A hartbeat is not recorded when the that last beat less than
        # the heartbeat_frequency.
        self.runner._heartbeat()
        self.reset_log()
        self.runner._heartbeat()
        now = datetime.now()
        last_heartbeat = self.runner.last_heartbeat
        self.assertTrue(
            now - last_heartbeat < self.runner.heartbeat_frequency)
        mark = self.get_mark()
        self.assertTrue(mark is None)

    def test__oneloop_success_heartbeat(self):
        # A heartbeat is recorded when the loop completes successfully.
        self.reset_log()
        self.runner.last_heartbeat = (
            self.runner.last_heartbeat - self.runner.heartbeat_frequency)
        self.runner._oneloop()
        mark = self.get_mark()
        self.assertTrue(mark is not None)

    def test__oneloop_exception_no_heartbeat(self):
        # A heartbeat is not recorded when there is an exception in the loop.
        self.reset_log()
        self.runner.last_heartbeat = (
            self.runner.last_heartbeat - self.runner.heartbeat_frequency)
        # Hack runner to raise an oops.
        with one_loop_exception(self.runner):
            self.runner._oneloop()
        mark = self.get_mark()
        self.assertTrue(mark is None)
