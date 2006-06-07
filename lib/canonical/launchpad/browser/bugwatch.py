# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""IBugWatch-related browser views."""

__metaclass__ = type
__all__ = ['BugWatchSetNavigation']

from canonical.launchpad.interfaces import IBugWatchSet
from canonical.launchpad.webapp import GetitemNavigation


class BugWatchSetNavigation(GetitemNavigation):

    usedfor = IBugWatchSet

