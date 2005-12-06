# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['LaunchpadCelebrities']

from zope.interface import implements
from zope.component import getUtility
from canonical.launchpad.interfaces import (ILaunchpadCelebrities,
    IPersonSet, IDistributionSet, IBugTrackerSet)

class LaunchpadCelebrities:

    implements(ILaunchpadCelebrities)

    @property
    def buttsource(self):
        """See ILaunchpadCelebrities."""
        return getUtility(IPersonSet).getByName('buttsource')

    @property
    def admin(self):
        """See ILaunchpadCelebrities."""
        return getUtility(IPersonSet).getByName('admins')

    @property
    def ubuntu(self):
        """See ILaunchpadCelebrities."""
        return getUtility(IDistributionSet).getByName('ubuntu')

    @property
    def debian(self):
        """See ILaunchpadCelebrities."""
        return getUtility(IDistributionSet).getByName('debian')

    @property
    def rosetta_expert(self):
        """See ILaunchpadCelebrities."""
        return getUtility(IPersonSet).getByName('rosetta-admins')

    @property
    def debbugs(self):
        """See ILaunchpadCelebrities."""
        return getUtility(IBugTrackerSet)['debbugs']

    @property
    def shipit_admin(self):
        """See ILaunchpadCelebrities."""
        return getUtility(IPersonSet).getByName('shipit-admins')

    @property
    def launchpad_developers(self):
        """See ILaunchpadCelebrities."""
        return getUtility(IPersonSet).getByName('launchpad')
