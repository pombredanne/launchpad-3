# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=W0702

"""Integration between the normal Launchpad logging and Twisted's."""

__metaclass__ = type
__all__ = [
    'LaunchpadLogFile',
    'log_oops_from_failure',
    'set_up_logging_for_script',
    'set_up_oops_reporting',
    'set_up_tacfile_logging',
    ]


import bz2
import glob
import logging
import os
import signal
import sys

from oops_twisted import OOPSObserver
from twisted.python import (
    log,
    logfile,
    )
from twisted.python.logfile import DailyLogFile
from twisted.web import xmlrpc
from zope.interface import implements

from canonical.launchpad.scripts import logger
from canonical.launchpad.webapp import errorlog
from canonical.librarian.utils import copy_and_close


def log_oops_from_failure(failure, URL=None, **args):
    request = errorlog.ScriptRequest(args.items(), URL=URL)
    errorlog.globalErrorUtility.raising(
        (failure.type, failure.value, failure.getTraceback()),
        request)
    return request


def set_up_logging_for_script(options, name):
    """Create a `Logger` object and configure twisted to use it.

    This also configures oops reporting to use the section named
    'name'."""
    logger_object = logger(options, name)
    set_up_oops_reporting(name, name, mangle_stdout=True)
    return logger_object


def set_up_tacfile_logging(name, level):
    """Create a `Logger` object for use in tac files.

    This is preferable to use over `set_up_logging_for_script` for .tac
    files since there's no options to pass through.  The logger object
    is connected to Twisted's log and returned.

    :param name: The logger instance name.
    :param level: The log level to use, eg. logging.INFO or logging.DEBUG
    """
    logger = logging.getLogger(name)
    channel = logging.StreamHandler(log.StdioOnnaStick())
    channel.setLevel(level)
    channel.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(channel)
    logger.setLevel(level)
    return logger


def set_up_oops_reporting(name, configuration=None, mangle_stdout=True):
    """Set up OOPS reporting by starting the Twisted logger with an observer.

    :param name: The name of the logger to use for oops reporting.
    :param configuration: The name of the config section to use for oops
        reporting. If None or not supplied then the existing oops configuration
        is used.
    :param mangle_stdout: If True, send stdout and stderr to the logger.
        Defaults to False.
    """
    if configuration is not None:
        errorlog.globalErrorUtility.configure(configuration)
    oops_observer = OOPSObserver(errorlog.globalErrorUtility._oops_config)
        config, log.PythonLoggingObserver(loggerName=name).emit)
    log.startLoggingWithObserver(oops_observer.emit, mangle_stdout)


class LaunchpadLogFile(DailyLogFile):
    """Extending `DailyLogFile` to serve Launchpad purposes.

    Additionally to the original daily log file rotation it also allows
    call sites to control the number of rotated logfiles kept around and
    when to start compressing them.
    """
    maxRotatedFiles = 5
    compressLast = 3

    def __init__(self, name, directory, defaultMode=None,
                 maxRotatedFiles=None, compressLast=None):
        DailyLogFile.__init__(self, name, directory, defaultMode)
        if maxRotatedFiles is not None:
            self.maxRotatedFiles = int(maxRotatedFiles)
        if compressLast is not None:
            self.compressLast = int(compressLast)

        assert self.compressLast <= self.maxRotatedFiles, (
            "Only %d rotate files are kept, cannot compress %d"
            % (self.maxRotatedFiles, self.compressLast))

    def _compressFile(self, path):
        """Compress the file in the given path using bzip2.

        The compressed file will be in the same path and old file
        will be removed.

        :return: the path to the compressed file.
        """
        bz2_path = '%s.bz2' % path
        copy_and_close(open(path), bz2.BZ2File(bz2_path, mode='w'))
        os.remove(path)
        return bz2_path

    def rotate(self):
        """Rotate the current logfile.

        Also remove extra entries and compress the last ones.
        """
        # Rotate the log daily.
        DailyLogFile.rotate(self)

        # Remove 'extra' rotated log files.
        logs = self.listLogs()
        for log_path in logs[self.maxRotatedFiles:]:
            os.remove(log_path)

        # Refresh the list of existing rotated logs
        logs = self.listLogs()

        # Skip compressing if there are no files to be compressed.
        if len(logs) <= self.compressLast:
            return

        # Compress last log files.
        for log_path in logs[-self.compressLast:]:
            # Skip already compressed files.
            if log_path.endswith('bz2'):
                continue
            self._compressFile(log_path)

    def listLogs(self):
        """Return the list of rotate log files, newest first."""
        return sorted(glob.glob("%s.*" % self.path), reverse=True)


class _QuietQueryFactory(xmlrpc._QueryFactory):
    """Override noisy to false to avoid useless log spam."""
    noisy = False


class LoggingProxy(xmlrpc.Proxy):
    """A proxy that logs requests and the corresponding responses."""

    queryFactory = _QuietQueryFactory

    def __init__(self, url, logger, level=logging.INFO):
        """Contstruct a `LoggingProxy`.

        :param url: The URL to which to post method calls.
        :param logger: The logger to log requests and responses to.
        :param level: The log level at which to log requests and responses.
        """
        xmlrpc.Proxy.__init__(self, url)
        self.logger = logger
        self.level = level
        self.request_count = 0

    def callRemote(self, method, *args):
        """See `xmlrpc.Proxy.callRemote`.

        In addition to the superclass' behavior, we log the call and its
        result.
        """
        request = self.request_count
        self.request_count += 1
        self.logger.log(
            self.level, 'Sending request [%d]: %s%s', request, method, args)

        def _logResult(result):
            self.logger.log(
                self.level, 'Reply to request [%d]: %s', request, result)
            return result
        deferred = xmlrpc.Proxy.callRemote(self, method, *args)
        return deferred.addBoth(_logResult)


class RotatableFileLogObserver:
    """A log observer that uses a log file and reopens it on SIGUSR1."""

    implements(log.ILogObserver)

    def __init__(self, logfilepath):
        """Set up the logfile and possible signal handler.

        Installs the signal handler for SIGUSR1 to make the process re-open
        the log file.

        :param logfilepath: The path to the logfile. If None, stdout is used
            for logging and no signal handler will be installed.
        """
        if logfilepath is None:
            logFile = sys.stdout
        else:
            logFile = logfile.LogFile.fromFullPath(
                logfilepath, rotateLength=None)
            # Override if signal is set to None or SIG_DFL (0)
            if not signal.getsignal(signal.SIGUSR1):
                def signalHandler(signal, frame):
                    from twisted.internet import reactor
                    reactor.callFromThread(logFile.reopen)
                signal.signal(signal.SIGUSR1, signalHandler)
        self.observer = log.FileLogObserver(logFile)

    def __call__(self, eventDict):
        self.observer.emit(eventDict)
