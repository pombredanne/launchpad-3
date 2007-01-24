#!/usr/bin/env python
# Copyright 2005 Canonical Ltd.  All rights reserved.

import _pythonpath

import sys
from optparse import OptionParser

from zope.component import getUtility

from contrib.glock import GlobalLock, LockAlreadyAcquired

from canonical.config import config
from canonical.lp import initZopeless
from canonical.lp.dbschema import TeamMembershipStatus
from canonical.launchpad.scripts import (
        execute_zcml_for_scripts, logger_options, logger)
from canonical.launchpad.interfaces import (
    ILaunchpadCelebrities, ITeamMembershipSet)

_default_lock_file = '/var/lock/launchpad-flag-expired-memberships.lock'


def flag_expired_memberships():
    ztm = initZopeless(
        dbuser=config.expiredmembershipsflagger.dbuser, implicitBegin=False)

    ztm.begin()
    reviewer = getUtility(ILaunchpadCelebrities).team_membership_janitor
    for membership in getUtility(ITeamMembershipSet).getMembershipsToExpire():
        membership.setStatus(TeamMembershipStatus.EXPIRED, reviewer)
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

    lockfile = GlobalLock(_default_lock_file, logger=log)
    try:
        lockfile.acquire()
    except LockAlreadyAcquired:
        log.error("lockfile %s already exists, exiting", _default_lock_file)
        sys.exit(1)

    try:
        flag_expired_memberships()
    finally:
        lockfile.release()

    log.info("Finished flagging expired team memberships.")

