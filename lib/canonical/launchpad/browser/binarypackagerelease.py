# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['BinaryPackageReleaseNavigation']

from canonical.launchpad.webapp import Navigation
from canonical.launchpad.interfaces import IBinaryPackageRelease


class BinaryPackageReleaseNavigation(Navigation):

    usedfor = IBinaryPackageRelease

    def traverse(self, name):
        return self.context[name]

