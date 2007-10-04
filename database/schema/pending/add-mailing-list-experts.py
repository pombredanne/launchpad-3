#!/usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.

# Creates the Mailing List Expers celebrity team.

import _pythonpath

from zope.component import getUtility

from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.lp import initZopeless
from canonical.launchpad.interfaces import (
    ILaunchpadCelebrities, IPersonSet, TeamSubscriptionPolicy)


execute_zcml_for_scripts()
ztm = initZopeless(implicitBegin=False)
ztm.begin()

personset = getUtility(IPersonSet)
if personset.getByName('mailing-list-experts') is None:
    admin_team = getUtility(ILaunchpadCelebrities).admin
    personset.newTeam(
        admin_team, 'mailing-list-experts', "Mailing List Experts",
        "This team is responsible for the management of Launchpad-hosted "
        "mailing lists.",
        subscriptionpolicy=TeamSubscriptionPolicy.RESTRICTED)
    ztm.commit()
    print "Created mailing-list-experts team."
else:
    print "mailing-list-experts team already created."
    ztm.commit()
    