# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Integration between the normal Launchpad logging and Twisted's."""

__metaclass__ = type
__all__ = ['set_up_logging_for_script']


from twisted.python import log

from canonical.config import config
from canonical.launchpad.scripts import logger
from canonical.launchpad.webapp import errorlog

class OOPSLoggingObserver(log.PythonLoggingObserver):
    """A version of `PythonLoggingObserver` that logs OOPSes for errors."""

    def emit(self, eventDict):
        """See `PythonLoggingObserver.emit`."""
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
            except:
                self.logger.exception("Error reporting OOPS:")
        else:
            log.PythonLoggingObserver.emit(self, eventDict)

def set_up_logging_for_script(options, name):
    logger_object = logger(options, name)
    config_section = getattr(config, name).errorreports
    for attr in 'oops_prefix', 'errordir', 'copy_to_zlog':
        value = getattr(config_section, attr)
        setattr(config.launchpad.errorreports, attr, value)
    log.startLoggingWithObserver(OOPSLoggingObserver(loggerName=name).emit)
    return logger_object
