# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Integration between the normal Launchpad logging and Twisted's."""

__metaclass__ = type
__all__ = ['set_up_logging_for_script']


import logging

from twisted.python import log

from canonical.launchpad.scripts import logger
from canonical.launchpad.webapp import errorlog

class SayNoFilter(logging.Filter):
    def filter(self, record):
        return False

class PythonLoggingObserver(log.PythonLoggingObserver):

    def emit(self, eventDict):
        """XXX."""
        if eventDict.get('isError', False) and 'failure' in eventDict:
            try:
                failure = eventDict['failure']
                request = errorlog.ScriptRequest([])
                errorlog.globalErrorUtility.raising(
                    (failure.type, failure.value, failure.getTraceback()),
                    request,)
                self.logger.info(
                    "Logged OOPS id %s: %s: %s",
                    request.oopsid, failure.type.__name__, failure.value)
            except Exception, e:
                self.logger.exception("Error reporting OOPS:")
            return
        log.PythonLoggingObserver.emit(self, eventDict)

def set_up_logging_for_script(options, name):
    logger_object = logger(options, name)
    log.startLoggingWithObserver(PythonLoggingObserver(loggerName=name).emit)
    return logger_object
