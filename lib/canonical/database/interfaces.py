# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

from zope.interface.common.interfaces import IRuntimeError

class IRequestExpired(IRuntimeError):
    """A RequestExpired exception is raised if the current request has
    timed out.
    """
