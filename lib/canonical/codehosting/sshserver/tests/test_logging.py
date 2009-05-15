# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for the logging system of the sshserver."""

__metaclass__ = type

import codecs
import logging
from StringIO import StringIO
import unittest
import sys

from bzrlib.tests import TestCase as BzrTestCase

from twisted.python import log as tplog

import zope.component.event
from zope.event import notify

from canonical.codehosting.sshserver.accesslog import (
    _log_event, get_access_logger, get_codehosting_logger, LoggingEvent,
    LoggingManager)
from canonical.config import config
from canonical.launchpad.scripts import WatchedFileHandler
from lp.testing import TestCase
from canonical.testing import reset_logging


class TestLoggingBazaarInteraction(BzrTestCase):

    def setUp(self):
        BzrTestCase.setUp(self)

        # Trap stderr.
        self._real_stderr = sys.stderr
        sys.stderr = codecs.getwriter('utf8')(StringIO())

        # We want to use Bazaar's default logging -- not its test logging --
        # so here we disable the testing logging system (which restores
        # default logging).
        self._finishLogFile()

        # We don't use BaseLayer because we want to keep the amount of
        # pre-configured logging systems to an absolute minimum, in order to
        # make it easier to test this particular logging system.
        self.addCleanup(reset_logging)

    def tearDown(self):
        sys.stderr = self._real_stderr
        BzrTestCase.tearDown(self)

    def test_leaves_bzr_handlers_unchanged(self):
        # Bazaar's log handling is untouched by logging setup.
        root_handlers = logging.getLogger('').handlers
        bzr_handlers = logging.getLogger('bzr').handlers

        manager = LoggingManager()
        manager.setUp()
        self.addCleanup(manager.tearDown)

        self.assertEqual(root_handlers, logging.getLogger('').handlers)
        self.assertEqual(bzr_handlers, logging.getLogger('bzr').handlers)

    def test_codehosting_log_doesnt_go_to_stderr(self):
        # Once logging setup is called, any messages logged to the
        # codehosting logger should *not* be logged to stderr. If they are,
        # they will appear on the user's terminal.
        manager = LoggingManager()
        manager.setUp()
        self.addCleanup(manager.tearDown)

        # Make sure that a logged message does not go to stderr.
        get_codehosting_logger().info('Hello hello')
        self.assertEqual(sys.stderr.getvalue(), '')


class TestLoggingManager(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        # We don't use BaseLayer because we want to keep the amount of
        # pre-configured logging systems to an absolute minimum, in order to
        # make it easier to test this particular logging system.
        self.addCleanup(reset_logging)

    def test_returns_codehosting_logger(self):
        # get_codehosting_logger returns the 'codehosting' logger.
        self.assertIs(
            logging.getLogger('codehosting'), get_codehosting_logger())

    def test_codehosting_handlers(self):
        # There needs to be at least one handler for the codehosting root
        # logger.
        manager = LoggingManager()
        manager.setUp()
        self.addCleanup(manager.tearDown)
        handlers = get_codehosting_logger().handlers
        self.assertNotEqual([], handlers)

    def _get_handlers(self):
        registrations = (
            zope.component.getGlobalSiteManager().registeredHandlers())
        return [
            registration.factory
            for registration in registrations]

    def test_log_event_handler_not_registered(self):
        self.assertNotIn(_log_event, self._get_handlers())

    def test_set_up_registers_event_handler(self):
        manager = LoggingManager()
        manager.setUp()
        self.addCleanup(manager.tearDown)
        self.assertIn(_log_event, self._get_handlers())

    def test_teardown_restores_event_handlers(self):
        handlers = self._get_handlers()
        manager = LoggingManager()
        manager.setUp()
        manager.tearDown()
        self.assertEqual(handlers, self._get_handlers())

    def test_teardown_restores_level(self):
        log = get_codehosting_logger()
        old_level = log.level
        manager = LoggingManager()
        manager.setUp()
        manager.tearDown()
        self.assertEqual(old_level, log.level)

    def test_teardown_restores_handlers(self):
        log = get_codehosting_logger()
        handlers = list(log.handlers)
        manager = LoggingManager()
        manager.setUp()
        manager.tearDown()
        self.assertEqual(handlers, log.handlers)

    def test_teardown_restores_twisted_observers(self):
        observers = list(tplog.theLogPublisher.observers)
        manager = LoggingManager()
        manager.setUp(True)
        manager.tearDown()
        self.assertEqual(observers, list(tplog.theLogPublisher.observers))

    def test_access_handlers(self):
        # The logging setup installs a rotatable log handler that logs output
        # to config.codehosting.access_log.
        manager = LoggingManager()
        manager.setUp()
        self.addCleanup(manager.tearDown)
        [handler] = get_access_logger().handlers
        self.assertIsInstance(handler, WatchedFileHandler)
        self.assertEqual(config.codehosting.access_log, handler.baseFilename)

    def test_teardown_restores_access_handlers(self):
        log = get_access_logger()
        handlers = list(log.handlers)
        manager = LoggingManager()
        manager.setUp()
        manager.tearDown()
        self.assertEqual(handlers, log.handlers)


class ListHandler(logging.Handler):
    """Logging handler that just appends records to a list.

    This handler isn't intended to be used by production code -- memory leak
    city! -- instead it's useful for unit tests that want to make sure the
    right events are being logged.
    """

    def __init__(self, logging_list):
        """Construct a `ListHandler`.

        :param logging_list: A list that will be appended to. The handler
             mutates this list.
        """
        logging.Handler.__init__(self)
        self._list = logging_list

    def emit(self, record):
        """Append 'record' to the list."""
        self._list.append(record)


class TestLoggingEvent(TestCase):

    def assertLogs(self, records, function, *args, **kwargs):
        """Assert 'function' logs 'records' when run with the given args."""
        logged_events = []
        handler = ListHandler(logged_events)
        self.logger.addHandler(handler)
        result = function(*args, **kwargs)
        self.logger.removeHandler(handler)
        self.assertEqual(
            [(record.levelno, record.getMessage())
             for record in logged_events], records)
        return result

    def assertEventLogs(self, record, logging_event):
        self.assertLogs([record], notify, logging_event)

    def setUp(self):
        TestCase.setUp(self)
        zope.component.provideHandler(_log_event)
        self.addCleanup(
            zope.component.getGlobalSiteManager().unregisterHandler,
            _log_event)
        self.logger = get_codehosting_logger()
        self.logger.setLevel(logging.DEBUG)

    def test_level(self):
        event = LoggingEvent(logging.CRITICAL, "foo")
        self.assertEventLogs((logging.CRITICAL, 'foo'), event)

    def test_formatting(self):
        event = LoggingEvent(logging.DEBUG, "foo: %(name)s", name="bar")
        self.assertEventLogs((logging.DEBUG, 'foo: bar'), event)

    def test_subclass(self):
        class SomeEvent(LoggingEvent):
            template = "%(something)s happened."
            level = logging.INFO
        self.assertEventLogs(
            (logging.INFO, 'foo happened.'), SomeEvent(something='foo'))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
