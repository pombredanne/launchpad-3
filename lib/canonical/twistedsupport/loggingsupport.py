# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0702

"""Integration between the normal Launchpad logging and Twisted's."""

__metaclass__ = type
__all__ = [
    'LaunchpadLogFile',
    'OOPSLoggingObserver',
    'log_oops_from_failure',
    'set_up_logging_for_script',
    'set_up_oops_reporting',
    ]


import bz2
import glob
import os

from twisted.python import log
from twisted.python.logfile import DailyLogFile

from canonical.launchpad.scripts import logger
from canonical.launchpad.webapp import errorlog
from canonical.librarian.utils import copy_and_close


class OOPSLoggingObserver(log.PythonLoggingObserver):
    """A version of `PythonLoggingObserver` that logs OOPSes for errors."""

    # XXX: JonathanLange 2008-12-23 bug=314959: As best as I can tell, this
    # ought to be a log *handler*, not a feature of the bridge from
    # Twisted->Python logging. Ask Michael about this.

    def emit(self, eventDict):
        """See `PythonLoggingObserver.emit`."""
        if eventDict.get('isError', False) and 'failure' in eventDict:
            try:
                failure = eventDict['failure']
                now = eventDict.get('error_time')
                request = log_oops_from_failure(failure, now=now)
                self.logger.info(
                    "Logged OOPS id %s: %s: %s",
                    request.oopsid, failure.type.__name__, failure.value)
            except:
                self.logger.exception("Error reporting OOPS:")
        else:
            log.PythonLoggingObserver.emit(self, eventDict)


def log_oops_from_failure(failure, now=None, URL=None, **args):
    request = errorlog.ScriptRequest(args.items(), URL=URL)
    errorlog.globalErrorUtility.raising(
        (failure.type, failure.value, failure.getTraceback()),
        request, now)
    return request


def set_up_logging_for_script(options, name):
    """Create a `Logger` object and configure twisted to use it.

    This also configures oops reporting to use the section named
    'name'."""
    logger_object = logger(options, name)
    set_up_oops_reporting(name, mangle_stdout=True)
    return logger_object


def set_up_oops_reporting(name, mangle_stdout=False):
    """Set up OOPS reporting by starting the Twisted logger with an observer.

    :param name: The name of the logger and config section to use for oops
        reporting.
    :param mangle_stdout: If True, send stdout and stderr to the logger.
        Defaults to False.
    """
    errorlog.globalErrorUtility.configure(name)
    log.startLoggingWithObserver(
        OOPSLoggingObserver(loggerName=name).emit, mangle_stdout)


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

