#!/usr/bin/python2.4
# Copyright 2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=C0103,W0403

"""Flag expired team memberships and warn about impending expiration."""

import _pythonpath

import pytz
from datetime import datetime, timedelta

from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.interfaces import (
    DAYS_BEFORE_EXPIRATION_WARNING_IS_SENT, ILaunchpadCelebrities,
    ITeamMembershipSet)
from canonical.launchpad.scripts.base import (
    LaunchpadCronScript, LaunchpadScriptFailure)


class ExpireMemberships(LaunchpadCronScript):
    """A script for expired team memberships."""

    def flag_expired_memberships_and_send_warnings(self):
        """Flag expired team memberships and warn about impending expiration.

        Flag expired team memberships and send warnings for members whose
        memberships are going to expire in one week (or less) from now.
        """
        membershipset = getUtility(ITeamMembershipSet)
        self.txn.begin()
        reviewer = getUtility(ILaunchpadCelebrities).janitor
        membershipset.handleMembershipsExpiringToday(reviewer)
        self.txn.commit()

        min_date_for_warning = datetime.now(pytz.timezone('UTC')) + timedelta(
            days=DAYS_BEFORE_EXPIRATION_WARNING_IS_SENT)
        self.txn.begin()
        for membership in membershipset.getMembershipsToExpire(
                min_date_for_warning):
            membership.sendExpirationWarningEmail()
        self.txn.commit()

    def main(self):
        """Flag expired team memberships."""
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

