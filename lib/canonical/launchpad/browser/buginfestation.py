# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['BugProductInfestationSetNavigation']

from canonical.launchpad.webapp import Navigation
from canonical.launchpad.interfaces import IBugProductInfestationSet


class BugProductInfestationSetNavigation(Navigation):

    usedfor = IBugProductInfestationSet

    def traverse(self, name):
        return self.context[name]

