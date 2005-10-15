# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['BugPackageInfestationSetNavigation']

from canonical.launchpad.webapp import GetitemNavigation
from canonical.launchpad.interfaces import IBugPackageInfestationSet


class BugPackageInfestationSetNavigation(GetitemNavigation):

    usedfor = IBugPackageInfestationSet

