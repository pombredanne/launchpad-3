#!/usr/bin/python2.4
# Copyright 2005 Canonical Ltd.  All rights reserved.

import _pythonpath

import pytz
from datetime import datetime, timedelta

from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.interfaces import (
    ILaunchpadCelebrities, ITeamMembershipSet)
from canonical.launchpad.scripts.base import (
    LaunchpadScript, LaunchpadScriptFailure)


class ExpireMemberships(LaunchpadScript):
    def flag_expired_memberships_and_send_warnings(self):
        """Flag expired team memberships and send warnings for members whose
        memberships are going to expire in one week (or less) from now.
        """
        membershipset = getUtility(ITeamMembershipSet)
        self.txn.begin()
        reviewer = getUtility(ILaunchpadCelebrities).team_membership_janitor
        membershipset.handleMembershipsExpiringToday(reviewer)
        self.txn.commit()

        one_week_from_now = datetime.now(
            pytz.timezone('UTC')) + timedelta(days=7)
        self.txn.begin()
        for membership in membershipset.getMembershipsToExpire(
                one_week_from_now):
            membership.sendExpirationWarningEmail()
        self.txn.commit()

    def main(self):
        if self.args:
            raise LaunchpadScriptFailure(
                "Unhandled arguments %s" % repr(self.args))
        self.logger.info("Flagging expired team memberships.")
        self.flag_expired_memberships_and_send_warnings()
        self.logger.info("Finished flagging expired team memberships.")


if __name__ == '__main__':
    script = ExpireMemberships('flag-expired-memberships', 
                dbuser=config.expiredmembershipsflagger.dbuser)
    script.lock_and_run()

