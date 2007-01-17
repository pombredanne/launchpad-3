#!/usr/bin/env python
# Copyright 2005 Canonical Ltd.  All rights reserved.

import _pythonpath

from datetime import datetime, timedelta
import pytz
from optparse import OptionParser
import sys

from zope.component import getUtility

from canonical.config import config
from canonical.lp import initZopeless
from canonical.lp.dbschema import TeamMembershipStatus
from canonical.launchpad.scripts import (
        execute_zcml_for_scripts, logger_options, logger)
from canonical.launchpad.scripts.lockfile import LockFile
from canonical.launchpad.interfaces import (
    ILaunchpadCelebrities, ITeamMembershipSet)

_default_lock_file = '/var/lock/launchpad-flag-expired-memberships.lock'


def flag_expired_memberships_and_send_warnings():
    """Flag expired team memberships and send warnings for members whose
    memberships are going to expire in one week (or less) from now.
    """
    ztm = initZopeless(
        dbuser=config.expiredmembershipsflagger.dbuser, implicitBegin=False)

    membershipset = getUtility(ITeamMembershipSet)
    ztm.begin()
    reviewer = getUtility(ILaunchpadCelebrities).team_membership_janitor
    for membership in membershipset.getMembershipsToExpire():
        membership.setStatus(TeamMembershipStatus.EXPIRED, reviewer)
    ztm.commit()

    one_week_from_now = datetime.now(pytz.timezone('UTC')) + timedelta(days=7)
    ztm.begin()
    for membership in membershipset.getMembershipsToExpire(one_week_from_now):
        membership.sendExpirationWarningEmail()
    ztm.commit()


if __name__ == '__main__':
    parser = OptionParser()
    logger_options(parser)
    (options, arguments) = parser.parse_args()
    if arguments:
        parser.error("Unhandled arguments %s" % repr(arguments))
    execute_zcml_for_scripts()

    log = logger(options, 'membershipupdater')
    log.info("Flagging expired team memberships.")

    lockfile = LockFile(_default_lock_file, logger=log)
    try:
        lockfile.acquire()
    except OSError:
        log.info("lockfile %s already exists, exiting", _default_lock_file)
        sys.exit(1)

    try:
        flag_expired_memberships_and_send_warnings()
    finally:
        lockfile.release()

    log.info("Finished flagging expired team memberships.")

