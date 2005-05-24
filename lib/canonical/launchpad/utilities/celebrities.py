# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['LaunchpadCelebrities']

from zope.interface import implements
from zope.component import getUtility
from canonical.launchpad.interfaces import ILaunchpadCelebrities
from canonical.launchpad.interfaces import IPersonSet
from canonical.launchpad.interfaces import IDistributionSet

class LaunchpadCelebrities:

    implements(ILaunchpadCelebrities)

    def buttsource(self):
        return getUtility(IPersonSet).getByName('buttsource')
    buttsource = property(buttsource)

    def admin(self):
        return getUtility(IPersonSet).getByName('admins')
    admin = property(admin)

    def ubuntu(self):
        return getUtility(IDistributionSet).getByName('ubuntu')
    ubuntu = property(ubuntu)


