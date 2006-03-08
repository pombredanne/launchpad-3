# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Testing helpers"""

__metaclass__ = type

import logging

def reset_logging():
    """Reset the logging system back to defaults
    
    Currently, defaults means 'the way the Z3 testrunner sets it up'

    XXX: We need isolation enforcement so that an error will be raised and
    the test run stop if a test fails to reset the logging system.
    -- StuartBishop 20060308
    """
    # Remove all handlers from non-root loggers, and remove the loggers too.
    loggerDict = logging.Logger.manager.loggerDict
    for name, logger in list(loggerDict.items()):
        if not isinstance(logger, logging.PlaceHolder):
            for handler in list(logger.handlers):
                logger.removeHandler(handler)
        del loggerDict[name]

    # Remove all handlers from the root logger
    root = logging.getLogger('')
    for handler in root.handlers:
        root.removeHandler(handler)

    # Reset the setup
    import zope.testing.testrunner
    zope.testing.testrunner.configure_logging()
