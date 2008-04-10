# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Integration between the normal Launchpad logging and Twisted's."""

__metaclass__ = type
__all__ = ['oops_reporting_observer']

import logging

from twisted.python import log

from canonical.launchpad.scripts import logger
from canonical.launchpad.webapp import errorlog

f = open('/home/mwh/foolog.txt', 'w')

def oops_reporting_observer(args):
    """A log observer for twisted's logging system that reports OOPSes."""
    try:
        print >>f, 'oops_reporting_observer', args
        if args.get('isError', False) and 'failure' in args:
            print >>f, 'helllllllllllll'
            log = logging.getLogger('codehosting')
            try:
                failure = args['failure']
                request = errorlog.ScriptRequest([])
                errorlog.globalErrorUtility.raising(
                    (failure.type, failure.value, failure.getTraceback()),
                    request,)
                print >>f, request.oopsid
                log.info("Logged OOPS id %s."%(request.oopsid,))
            except Exception, e:
                print >>f, e
                log.exception("Error reporting OOPS:")
    finally:
        f.flush()

def setup_logging_for_script(options, name):
    logger_object = logger(options, name)
    log.addObserver(oops_reporting_observer)
    observer = log.PythonLoggingObserver(loggerName=name)
    observer.start()
