# Copyright 20011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
"""Test the Launchpad XMLRPC runner."""

__metaclass__ = type
__all__ = []

from contextlib import contextmanager
from datetime import datetime
import socket

from Mailman import Errors
from Mailman.Logging.Syslog import syslog
from Mailman import mm_cfg
from Mailman.Queue.XMLRPCRunner import (
    handle_proxy_error,
    XMLRPCRunner,
    )

from canonical.config import config
from canonical.testing.layers import (
    BaseLayer,
    DatabaseFunctionalLayer,
    )
from lp.services.mailman.monkeypatches.xmlrpcrunner import (
    get_mailing_list_api_proxy,
    )
from lp.services.mailman.testing import (
     get_mailing_list_api_test_proxy,
     MailmanTestCase,
     )
from lp.services.xmlrpc import Transport
from lp.testing import TestCase


@contextmanager
def one_loop_exception(runner):
    """Raise an error during th execution of _oneloop.

    This function replaces _check_list_actions() with a function that
    raises an error. _oneloop() handles the exception.
    """

    def raise_exception():
        raise Exception('Test exception handling.')

    original__check_list_actions = runner._check_list_actions
    runner._check_list_actions = raise_exception
    try:
        yield
    finally:
        runner._check_list_actions = original__check_list_actions


class TestXMLRPCRunnerTimeout(TestCase):
    """Make sure that we set a timeout on our xmlrpc connections."""

    layer = BaseLayer

    def test_timeout_used(self):
        proxy = get_mailing_list_api_proxy()
        # We don't want to trigger the proxy if we misspell something, so we
        # look in the dict.
        transport = proxy.__dict__['_ServerProxy__transport']
        self.assertTrue(isinstance(transport, Transport))
        self.assertEqual(mm_cfg.XMLRPC_TIMEOUT, transport.timeout)
        # This is a bit rickety--if the mailman config was built under a
        # different instance that has a different timeout value, this will
        # fail.  Removing this next assertion would probably be OK then, but
        # I think it is nice to have.
        self.assertEqual(config.mailman.xmlrpc_timeout, mm_cfg.XMLRPC_TIMEOUT)


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

    def test_heartbeat_on_start(self):
        # A heartbeat is recorded in the log on start.
        mark = self.get_mark()
        self.assertTrue(mark is not None)

    def test_heatbeat_frequency_no_heartbeat(self):
        # A heartbeat is not recorded when the that last beat less than
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


class TestHandleProxyError(MailmanTestCase):
    """Test XMLRPCRunner.handle_proxy_error function."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestHandleProxyError, self).setUp()
        self.team, self.mailing_list = self.factory.makeTeamAndMailingList(
            'team-1', 'team-1-owner')
        self.mm_list = self.makeMailmanList(self.mailing_list)
        syslog.write_ex('xmlrpc', 'Ensure the log is open.')
        self.reset_log()

    def test_communication_log_entry(self):
        # Connection errors are reported in the log.
        error = socket.error('Testing socket error.')
        handle_proxy_error(error)
        mark = self.get_log_entry('Cannot talk to Launchpad:')
        self.assertTrue(mark is not None)

    def test_fault_log_entry(self):
        # Fault errors are reported in the log.
        error = Exception('Testing generic error.')
        handle_proxy_error(error)
        mark = self.get_log_entry('Launchpad exception:')
        self.assertTrue(mark is not None)

    def test_message_raises_discard_message_error(self):
        # When message is passed to the function, DiscardMessage is raised
        # and the message is re-enqueued in the incoming queue.
        error = Exception('Testing generic error.')
        msg = self.makeMailmanMessage(
            self.mm_list, 'lost@noplace.dom', 'subject', 'any content.')
        msg_data = {}
        self.assertRaises(
            Errors.DiscardMessage, handle_proxy_error, error, msg, msg_data)
        self.assertIsEnqueued(msg)
