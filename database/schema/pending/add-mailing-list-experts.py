#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# Creates the Mailing List Experts celebrity team.

import _pythonpath

from zope.component import getUtility

from canonical.lp import initZopeless
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.registry.interfaces.person import (
    IPersonSet,
    TeamSubscriptionPolicy,
    )
from lp.services.scripts import execute_zcml_for_scripts


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
    print "mailing-list-experts team already exists."
    ztm.commit()
