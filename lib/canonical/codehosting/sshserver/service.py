# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Provides an SFTP server which Launchpad users can use to host their Bazaar
branches. For more information, see lib/canonical/codehosting/README.
"""

__metaclass__ = type
__all__ = [
    'get_codehosting_logger',
    'log_event',
    'LoggingEvent',
    'SSHService',
    ]


import logging
from logging.handlers import TimedRotatingFileHandler
import os

from twisted.application import service, strports
from twisted.conch.ssh.connection import SSHConnection
from twisted.conch.ssh.factory import SSHFactory
from twisted.conch.ssh.keys import Key
from twisted.web.xmlrpc import Proxy

from canonical.codehosting.sshserver.auth import get_portal, SSHUserAuthServer
from canonical.config import config
from canonical.twistedsupport.loggingsupport import set_up_oops_reporting


class Factory(SSHFactory):
    services = {
        'ssh-userauth': SSHUserAuthServer,
        'ssh-connection': SSHConnection
    }

    def __init__(self, hostPublicKey, hostPrivateKey):
        self.publicKeys = {
            'ssh-rsa': hostPublicKey
        }
        self.privateKeys = {
            'ssh-rsa': hostPrivateKey
        }

    def startFactory(self):
        SSHFactory.startFactory(self)
        os.umask(0022)


class SSHService(service.Service):
    """A Twisted service for the supermirror SFTP server."""

    def __init__(self):
        self.service = self.makeService()

    def makeFactory(self, hostPublicKey, hostPrivateKey):
        """Create and return an SFTP server that uses the given public and
        private keys.
        """
        authentication_proxy = Proxy(
            config.codehosting.authentication_endpoint)
        branchfs_proxy = Proxy(config.codehosting.branchfs_endpoint)
        portal = get_portal(authentication_proxy, branchfs_proxy)
        sftpfactory = Factory(hostPublicKey, hostPrivateKey)
        sftpfactory.portal = portal
        return sftpfactory

    def makeService(self):
        """Return a service that provides an SFTP server. This is called in
        the constructor.
        """
        hostPublicKey, hostPrivateKey = self.makeKeys()
        sftpfactory = self.makeFactory(hostPublicKey, hostPrivateKey)
        return strports.service(config.codehosting.port, sftpfactory)

    def makeKeys(self):
        """Load the public and private host keys from the configured key pair
        path. Returns both keys in a 2-tuple.

        :return: (hostPublicKey, hostPrivateKey)
        """
        keydir = config.codehosting.host_key_pair_path
        hostPublicKey = Key.fromString(
            open(os.path.join(keydir, 'ssh_host_key_rsa.pub'), 'rb').read())
        hostPrivateKey = Key.fromString(
            open(os.path.join(keydir, 'ssh_host_key_rsa'), 'rb').read())
        return hostPublicKey, hostPrivateKey

    def startService(self):
        """Start the SFTP service."""
        set_up_logging(configure_oops_reporting=True)
        service.Service.startService(self)
        self.service.startService()

    def stopService(self):
        """Stop the SFTP service."""
        service.Service.stopService(self)
        return self.service.stopService()


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
    log.setLevel(logging.CRITICAL)
    log.addHandler(
        TimedRotatingFileHandler(
            config.codehosting.access_log,
            when='midnight'))
    if configure_oops_reporting:
        set_up_oops_reporting('codehosting')
    return log


class LoggingEvent:
    """An event that can log itself to a logger.

    :ivar level: The level to log itself as. This should be defined as a
        class variable in subclasses.
    :ivar template: The format string of the message to log. This should be
        defined as a class variable in subclasses.
    """

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
            self.level = level
        if template is not None:
            self.template = template
        self._data = data
        for name, value in data.iteritems():
            setattr(self, name, value)

    def _log(self, logger):
        """Log the event to 'logger'."""
        logger.log(self.level, self.template % self._data)


def log_event(logger, event):
    """Log 'event' to 'logger'.

    All events should be logged through this function, which provides a
    convenient mocking point for tests.
    """
    return event._log(logger)
