# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Logging for the SSH server."""

__metaclass__ = type
__all__ = [
    'BazaarSSHClosed',
    'BazaarSSHStarted',
    'get_codehosting_logger',
    'LoggingEvent',
    'ServerStarting',
    'ServerStopped',
    'SFTPClosed',
    'SFTPStarted',
    'UserConnected',
    'UserDisconnected',
    'UserLoggedIn',
    'UserLoggedOut',
    ]

import logging
from logging.handlers import TimedRotatingFileHandler

# This non-standard import is necessary to hook up the event system.
import zope.component.event
from zope.interface import Attribute, implements, Interface

from canonical.config import config
from canonical.twistedsupport.loggingsupport import set_up_oops_reporting


def get_codehosting_logger():
    """Return the codehosting logger."""
    # This is its own function to avoid spreading the string 'codehosting'
    # everywhere and to avoid duplicating information about how log objects
    # are acquired.
    return logging.getLogger('codehosting')


def set_up_logging(configure_oops_reporting=False):
    """Set up logging for the smart server.

    This sets up a debugging handler on the 'codehosting' logger, makes sure
    that things logged there won't go to stderr (necessary because of
    bzrlib.trace shenanigans) and then returns the 'codehosting' logger.

    In addition, if configure_oops_reporting is True, install a Twisted log
    observer that ensures unhandled exceptions get reported as OOPSes.
    """
    # XXX: JonathanLange 2008-12-23: Why isn't configure_oops_reporting True
    # all the time? Part of the answer is that when I set it to True, the
    # test_logging tests don't restore stderr properly, resulting in broken
    # testrunner output.
    log = get_codehosting_logger()
    log.setLevel(logging.INFO)
    handler = TimedRotatingFileHandler(
        config.codehosting.access_log, when='midnight')
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(handler)
    if configure_oops_reporting:
        set_up_oops_reporting('codehosting')
    # Make sure that our logging event handler is there, ready to receive
    # logging events.
    zope.component.provideHandler(_log_event)
    return log


class ILoggingEvent(Interface):

    level = Attribute("The level to log the event at.")
    message = Attribute("The message to log.")


class LoggingEvent:
    """An event that can log itself to a logger.

    :ivar level: The level to log itself as. This should be defined as a
        class variable in subclasses.
    :ivar template: The format string of the message to log. This should be
        defined as a class variable in subclasses.
    """

    implements(ILoggingEvent)

    def __init__(self, level=None, template=None, **data):
        """Construct a logging event.

        :param level: The level to log the event as. If specified, overrides
            the 'level' class variable.
        :param template: The format string of the message to log. If
            specified, overrides the 'template' class variable.
        :param **data: Information to be logged. Entries will be substituted
            into the template and stored as attributes.
        """
        if level is not None:
            self._level = level
        if template is not None:
            self.template = template
        self._data = data
        for name, value in data.iteritems():
            setattr(self, name, value)

    @property
    def level(self):
        """See `ILoggingEvent`."""
        return self._level

    @property
    def message(self):
        """See `ILoggingEvent`."""
        return self.template % self._data


class ServerStarting(LoggingEvent):

    level = logging.INFO
    template = '---- Server started ----'


class ServerStopped(LoggingEvent):

    level = logging.INFO
    template = '---- Server stopped ----'


class UserConnected(LoggingEvent):

    level = logging.INFO
    template = '[%(session_id)s] %(address)s connected.'

    def __init__(self, transport, address):
        LoggingEvent.__init__(
            self, session_id=id(transport), address=address)


class UserDisconnected(LoggingEvent):

    level = logging.INFO
    template = '[%(session_id)s] disconnected.'

    def __init__(self, transport):
        LoggingEvent.__init__(self, session_id=id(transport))


class AvatarEvent(LoggingEvent):
    """Base avatar event."""

    level = logging.INFO

    def __init__(self, avatar):
        self.avatar = avatar
        LoggingEvent.__init__(
            self, session_id=id(avatar.transport), username=avatar.username)


class UserLoggedIn(AvatarEvent):

    template = '[%(session_id)s] %(username)s logged in.'


class UserLoggedOut(AvatarEvent):

    template = '[%(session_id)s] %(username)s disconnected.'


class SFTPStarted(AvatarEvent):

    template = '[%(session_id)s] %(username)s started SFTP session.'


class SFTPClosed(AvatarEvent):

    template = '[%(session_id)s] %(username)s closed SFTP session.'


class BazaarSSHStarted(AvatarEvent):

    template = '[%(session_id)s] %(username)s started bzr+ssh session.'


class BazaarSSHClosed(AvatarEvent):

    template = '[%(session_id)s] %(username)s closed bzr+ssh session.'


@zope.component.adapter(ILoggingEvent)
def _log_event(event):
    """Log 'event' to the codehosting logger.

    All events should be logged through this function, which provides a
    convenient mocking point for tests.
    """
    get_codehosting_logger().log(event.level, event.message)
