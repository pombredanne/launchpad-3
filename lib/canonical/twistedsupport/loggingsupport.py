# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Integration between the normal Launchpad logging and Twisted's."""

__metaclass__ = type
__all__ = [
    'OOPSLoggingObserver',
    'set_up_logging_for_script']


from twisted.python import log

from canonical.launchpad.scripts import logger
from canonical.launchpad.webapp import errorlog


class OOPSLoggingObserver(log.PythonLoggingObserver):
    """A version of `PythonLoggingObserver` that logs OOPSes for errors."""

    def emit(self, eventDict):
        """See `PythonLoggingObserver.emit`."""
        if eventDict.get('isError', False) and 'failure' in eventDict:
            try:
                failure = eventDict['failure']
                now = eventDict.get('error_time')
                request = errorlog.ScriptRequest([])
                errorlog.globalErrorUtility.raising(
                    (failure.type, failure.value, failure.getTraceback()),
                    request, now)
                self.logger.info(
                    "Logged OOPS id %s: %s: %s",
                    request.oopsid, failure.type.__name__, failure.value)
            except:
                self.logger.exception("Error reporting OOPS:")
        else:
            log.PythonLoggingObserver.emit(self, eventDict)


def set_up_logging_for_script(options, name):
    """Create a `Logger` object and configure twisted to use it.

    This also configures oops reporting to use the section named
    'name'."""
    logger_object = logger(options, name)
    errorlog.globalErrorUtility.configure(name)
    log.startLoggingWithObserver(OOPSLoggingObserver(loggerName=name).emit)
    return logger_object
