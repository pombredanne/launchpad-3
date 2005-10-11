# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['BugProductInfestationSetNavigation']

from canonical.launchpad.webapp import GetitemNavigation
from canonical.launchpad.interfaces import IBugProductInfestationSet


class BugProductInfestationSetNavigation(GetitemNavigation):

    usedfor = IBugProductInfestationSet

