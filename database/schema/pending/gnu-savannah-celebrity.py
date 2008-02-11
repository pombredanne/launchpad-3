#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.

# Creates the GNU Savannah bugtracker celebrity

import _pythonpath

from zope.component import getUtility


from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.lp import initZopeless
from canonical.launchpad.database import BugTrackerAlias
from canonical.launchpad.interfaces import (
    BugTrackerType, ILaunchpadCelebrities, IBugTrackerAliasSet,
    IBugTrackerSet, IPersonSet)


execute_zcml_for_scripts()
ztm = initZopeless(implicitBegin=False)
ztm.begin()

bugtracker_set = getUtility(IBugTrackerSet)
admin_team = getUtility(ILaunchpadCelebrities).admin
savannah = bugtracker_set.getByName('savannah')
if savannah is None:
    savannah = bugtracker_set.ensureBugTracker(
        'http://savannah.gnu.org/bugs/', admin_team, BugTrackerType.SAVANNAH,
        "GNU Savannah Bug Tracker", "Savannah is an open source software "
        "development hosting service based on SourceForge.",
        name='savannah')
    print "Created Savannah bug tracker."
else:
    print "Savannah bug tracker already exists."

bugtrackeralias_set = getUtility(IBugTrackerAliasSet)
if not bugtrackeralias_set.queryByBugTracker(savannah):
    # This looks messy but BugTracker.aliases is a tuple and there isn't
    # a nicer way to do it.
    savannah_alias = BugTrackerAlias(bugtracker=savannah,
        base_url='http://savannah.nognu.org/bugs/')
    print "Created NoGNU alias for Savannah tracker."
else:
    print "NoGNU alias for Savannah already exists."

ztm.commit()
