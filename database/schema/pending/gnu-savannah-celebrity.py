#!/usr/bin/python -S
#
# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Creates the GNU Savannah bugtracker celebrity.

This script should only need to be run once on production or staging. It
creates the records needed for the savannah_tracker LaunchpadCelebrity.
"""

import _pythonpath

from zope.component import getUtility


from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.lp import initZopeless
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.bugs.interfaces.bugtracker import (
    BugTrackerType,
    IBugTrackerAliasSet,
    IBugTrackerSet,
    )
from lp.bugs.model.bugtracker import BugTrackerAlias


execute_zcml_for_scripts()
ztm = initZopeless(implicitBegin=False)
ztm.begin()

bugtracker_set = getUtility(IBugTrackerSet)
admin_team = getUtility(ILaunchpadCelebrities).admin
savannah = bugtracker_set.getByName('savannah')
if savannah is None:
    savannah = bugtracker_set.ensureBugTracker(
        'http://savannah.gnu.org/', admin_team, BugTrackerType.SAVANNAH,
        "GNU Savannah Bug Tracker", "Savannah is an open source software "
        "development hosting service based on SourceForge.",
        name='savannah')
    print "Created Savannah bug tracker."
else:
    print "Savannah bug tracker already exists."

bugtrackeralias_set = getUtility(IBugTrackerAliasSet)
if not bugtrackeralias_set.queryByBugTracker(savannah):
    savannah_alias = BugTrackerAlias(bugtracker=savannah,
        base_url='http://savannah.nognu.org/')
    print "Created NoGNU alias for Savannah tracker."
else:
    print "NoGNU alias for Savannah already exists."

ztm.commit()
