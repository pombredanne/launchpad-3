# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the logging system of the sshserver."""

__metaclass__ = type

import codecs
import logging
from StringIO import StringIO
import unittest
import sys

from bzrlib.tests import TestCase as BzrTestCase

import zope.component.event
from zope.event import notify

from canonical.config import config
from canonical.launchpad.scripts import WatchedFileHandler
from lp.codehosting.sshserver.accesslog import (
    get_access_logger, get_codehosting_logger, LoggingManager)
from lp.codehosting.sshserver.events import ILoggingEvent, LoggingEvent
from lp.testing import TestCase


class LoggingManagerMixin:

    def installLoggingManager(self):
        manager = LoggingManager()
        manager.setUp()
        self.addCleanup(manager.tearDown)
        return manager


class TestLoggingBazaarInteraction(BzrTestCase, LoggingManagerMixin):

    def setUp(self):
        BzrTestCase.setUp(self)

        # Trap stderr.
        self._real_stderr = sys.stderr
        sys.stderr = codecs.getwriter('utf8')(StringIO())

    def tearDown(self):
        sys.stderr = self._real_stderr
        BzrTestCase.tearDown(self)

    def test_leaves_bzr_handlers_unchanged(self):
        # Bazaar's log handling is untouched by logging setup.
        root_handlers = logging.getLogger('').handlers
        bzr_handlers = logging.getLogger('bzr').handlers

        self.installLoggingManager()

        self.assertEqual(root_handlers, logging.getLogger('').handlers)
        self.assertEqual(bzr_handlers, logging.getLogger('bzr').handlers)

    def test_codehosting_log_doesnt_go_to_stderr(self):
        # Once logging setup is called, any messages logged to the
        # codehosting logger should *not* be logged to stderr. If they are,
        # they will appear on the user's terminal.
        self.installLoggingManager()

        # Make sure that a logged message does not go to stderr.
        get_codehosting_logger().info('Hello hello')
        self.assertEqual(sys.stderr.getvalue(), '')


class TestLoggingManager(TestCase, LoggingManagerMixin):

    def test_returns_codehosting_logger(self):
        # get_codehosting_logger returns the 'codehosting' logger.
        self.assertIs(
            logging.getLogger('codehosting'), get_codehosting_logger())

    def test_codehosting_handlers(self):
        # There needs to be at least one handler for the codehosting root
        # logger.
        self.installLoggingManager()

        handlers = get_codehosting_logger().handlers
        self.assertNotEqual([], handlers)

    def _get_handlers(self):
        registrations = (
            zope.component.getGlobalSiteManager().registeredHandlers())
        return [
            registration.factory
            for registration in registrations]

    def test_set_up_registers_event_handler(self):
        manager = self.installLoggingManager()
        self.assertIn(manager._log_event, self._get_handlers())

    def test_teardown_restores_event_handlers(self):
        handlers = self._get_handlers()
        manager = self.installLoggingManager()
        manager.tearDown()
        self.assertEqual(handlers, self._get_handlers())

    def test_teardown_restores_level(self):
        log = get_codehosting_logger()
        old_level = log.level
        manager = self.installLoggingManager()
        manager.tearDown()
        self.assertEqual(old_level, log.level)

    def test_teardown_restores_handlers(self):
        log = get_codehosting_logger()
        handlers = list(log.handlers)
        manager = self.installLoggingManager()
        manager.tearDown()
        self.assertEqual(handlers, log.handlers)

    def test_access_handlers(self):
        # The logging setup installs a rotatable log handler that logs output
        # to config.codehosting.access_log.
        self.installLoggingManager()
        [handler] = get_access_logger().handlers
        self.assertIsInstance(handler, WatchedFileHandler)
        self.assertEqual(config.codehosting.access_log, handler.baseFilename)

    def test_teardown_restores_access_handlers(self):
        log = get_access_logger()
        handlers = list(log.handlers)
        manager = self.installLoggingManager()
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
        logger = logging.getLogger(self.factory.getUniqueString())
        logger.setLevel(logging.DEBUG)
        self.logger = logger

        @zope.component.adapter(ILoggingEvent)
        def _log_event(event):
            logger.log(event.level, event.message)

        zope.component.provideHandler(_log_event)
        self.addCleanup(
            zope.component.getGlobalSiteManager().unregisterHandler,
            _log_event)

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
