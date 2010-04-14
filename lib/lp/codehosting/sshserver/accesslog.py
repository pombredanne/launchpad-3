# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Logging for the SSH server."""

__metaclass__ = type
__all__ = [
    'LoggingManager',
    ]

import logging

from twisted.python import log as tplog

# This non-standard import is necessary to hook up the event system.
import zope.component.event

from canonical.config import config
from canonical.launchpad.scripts import WatchedFileHandler
from lp.codehosting.sshserver.events import ILoggingEvent
from lp.services.utils import synchronize
from lp.services.twistedsupport.loggingsupport import set_up_oops_reporting


class LoggingManager:
    """Class for managing codehosting logging."""

    def setUp(self, configure_oops_reporting=False):
        """Set up logging for the smart server.

        This sets up a debugging handler on the 'codehosting' logger, makes
        sure that things logged there won't go to stderr (necessary because of
        bzrlib.trace shenanigans) and then returns the 'codehosting' logger.

        :param configure_oops_reporting: If True, install a Twisted log
            observer that ensures unhandled exceptions get reported as OOPSes.
        """
        log = get_codehosting_logger()
        self._orig_level = log.level
        self._orig_handlers = list(log.handlers)
        self._orig_observers = list(tplog.theLogPublisher.observers)
        log.setLevel(logging.INFO)
        log.addHandler(_NullHandler())
        access_log = get_access_logger()
        handler = WatchedFileHandler(config.codehosting.access_log)
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        access_log.addHandler(handler)
        if configure_oops_reporting:
            set_up_oops_reporting('codehosting')
        # Make sure that our logging event handler is there, ready to receive
        # logging events.
        zope.component.provideHandler(_log_event)

    def tearDown(self):
        log = get_codehosting_logger()
        log.level = self._orig_level
        synchronize(
            log.handlers, self._orig_handlers, log.addHandler,
            log.removeHandler)
        access_log = get_access_logger()
        synchronize(
            access_log.handlers, self._orig_handlers, access_log.addHandler,
            access_log.removeHandler)
        synchronize(
            tplog.theLogPublisher.observers, self._orig_observers,
            tplog.addObserver, tplog.removeObserver)
        zope.component.getGlobalSiteManager().unregisterHandler(_log_event)


def get_codehosting_logger():
    """Return the codehosting logger."""
    # This is its own function to avoid spreading the string 'codehosting'
    # everywhere and to avoid duplicating information about how log objects
    # are acquired.
    return logging.getLogger('codehosting')


def get_access_logger():
    return logging.getLogger('codehosting.access')


class _NullHandler(logging.Handler):
    """Logging handler that does nothing with messages.

    At the moment, we don't want to do anything with the Twisted log messages
    that go to the 'codehosting' logger, and we also don't want warnings about
    there being no handlers. Hence, we use this do-nothing handler.
    """

    def emit(self, record):
        pass


@zope.component.adapter(ILoggingEvent)
def _log_event(event):
    """Log 'event' to the codehosting logger."""
    get_access_logger().log(event.level, event.message)
