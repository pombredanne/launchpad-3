# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['PathLookupError',
           'PathStepRequiredError',
           'PathStepNotFoundError']

from zope.interface import implements

from canonical.launchpad.interfaces import (
    IPathLookupError, IPathStepRequiredError, IPathStepNotFoundError)


class PathLookupError(Exception):
    """See IPathLookupError."""
    implements(IPathLookupError)
        

class PathStepRequiredError(PathLookupError):
    """See IPathStepRequiredError."""
    implements(IPathStepRequiredError)

    def __init__(self, msg, *missing_types):
        PathLookupError.__init__(self, msg)
        self.missing_types = missing_types


class PathStepNotFoundError(PathLookupError):
    """See IPathStepNotFoundError."""
    implements(IPathStepNotFoundError)

    def __init__(self, msg, step, *notfound_types): 
        PathLookupError.__init__(self, msg)
        self.step = step
        self.notfound_types = notfound_types
