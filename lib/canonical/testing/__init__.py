# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Testing helpers"""

__metaclass__ = type

__all__ = [
    'BaseLayer',
    'DatabaseFunctionalLayer',
    'DatabaseLayer',
    'ExperimentalLaunchpadZopelessLayer',
    'FunctionalLayer',
    'LaunchpadFunctionalLayer',
    'LaunchpadLayer',
    'LaunchpadScriptLayer',
    'LaunchpadZopelessLayer',
    'LibrarianLayer',
    'PageTestLayer',
    'reset_logging',
    'TwistedAppServerLayer',
    'TwistedLaunchpadZopelessLayer',
    'TwistedLayer',
    'ZopelessAppServerLayer',
    'ZopelessLayer',
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

# This import registers the 'doctest' Unicode codec.
import canonical.testing.doctestcodec

# Imported here to avoid circular import issues
# pylint: disable-msg=W0401
from canonical.testing.layers import *
from canonical.testing.layers import __all__ as layers_all
__all__.extend(layers_all)
