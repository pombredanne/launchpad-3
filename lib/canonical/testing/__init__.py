# Copyright 2006-2008 Canonical Ltd.  All rights reserved.

"""Testing helpers"""

__metaclass__ = type

__all__ = [
    'reset_logging',
    'BaseLayer', 'DatabaseLayer', 'LibrarianLayer', 'FunctionalLayer',
    'LaunchpadLayer', 'ZopelessLayer', 'LaunchpadFunctionalLayer',
    'LaunchpadZopelessLayer', 'PageTestLayer', 'TwistedLayer',
    'LaunchpadScriptLayer', 'ExperimentalLaunchpadZopelessLayer',
    'TwistedLaunchpadZopelessLayer'
    ]

import logging

def reset_logging():
    """Reset the logging system back to defaults

    Currently, defaults means 'the way the Z3 testrunner sets it up'

    XXX: StuartBishop 2006-03-08 bug=39877:
    We need isolation enforcement so that an error will be raised and
    the test run stop if a test fails to reset the logging system.
    """
    # Remove all handlers from non-root loggers, and remove the loggers too.
    loggerDict = logging.Logger.manager.loggerDict
    for name, logger in list(loggerDict.items()):
        if name == 'pagetests-access':
            # Don't reset the hit logger used by the test infrastructure.
            continue
        if not isinstance(logger, logging.PlaceHolder):
            for handler in list(logger.handlers):
                logger.removeHandler(handler)
        del loggerDict[name]

    # Remove all handlers from the root logger
    root = logging.getLogger('')
    for handler in root.handlers:
        root.removeHandler(handler)

    # Clean out the guts of the logging module. We don't want handlers that
    # have already been closed hanging around for the atexit handler to barf
    # on, for example.
    del logging._handlerList[:]
    logging._handlers.clear()

    # Reset the setup
    import zope.testing.testrunner
    zope.testing.testrunner.configure_logging()


# Imported here to avoid circular import issues
from canonical.testing.layers import (
    ExperimentalLaunchpadZopelessLayer, BaseLayer, DatabaseLayer,
    LibrarianLayer, FunctionalLayer, GoogleServiceLayer,
    LaunchpadLayer, ZopelessLayer, LaunchpadFunctionalLayer,
    LaunchpadZopelessLayer, PageTestLayer, TwistedLayer,
    LaunchpadScriptLayer, TwistedLaunchpadZopelessLayer)
