# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['BugPackageInfestationSetNavigation']

from canonical.launchpad.webapp import Navigation
from canonical.launchpad.interfaces import IBugPackageInfestationSet


class BugPackageInfestationSetNavigation(Navigation):

    usedfor = IBugPackageInfestationSet

    def traverse(self, name):
        return self.context[name]

