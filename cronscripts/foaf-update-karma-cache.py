#!/usr/bin/env python
# Copyright 2005 Canonical Ltd.  All rights reserved.

import _pythonpath

import sys
from optparse import OptionParser

from zope.component import getUtility

from canonical.config import config
from canonical.lp import initZopeless
from canonical.lp.dbschema import KarmaActionCategory
from canonical.launchpad.scripts import (
        execute_zcml_for_scripts, logger_options, logger
        )
from canonical.launchpad.scripts.lockfile import LockFile
from canonical.launchpad.interfaces import IPersonSet
from canonical.launchpad.interfaces import IKarmaCacheSet, IKarmaSet

_default_lock_file = '/var/lock/launchpad-karma-update.lock'


def update_karma_cache():
    """Update the KarmaCache table for all valid Launchpad users.

    For each Launchpad user with a preferred email address, calculate his
    karmavalue for each category of actions we have and update his entry in
    the KarmaCache table. If a user doesn't have an entry for that category in
    KarmaCache a new one will be created.
    """
    ztm = initZopeless(dbuser=config.karmacacheupdater.dbuser,
                       implicitBegin=False)

    cacheset = getUtility(IKarmaCacheSet)
    karmaset = getUtility(IKarmaSet)
    personset = getUtility(IPersonSet)
    ztm.begin()
    person_ids = [p.id for p in personset.getAllValidPersons()]
    ztm.commit()
    for person_id in person_ids:
        ztm.begin()
        person = personset.get(person_id)
        for cat in KarmaActionCategory.items:
            karmavalue = karmaset.getSumByPersonAndCategory(person, cat)
            cache = cacheset.getByPersonAndCategory(person, cat)
            if cache is None:
                cache = cacheset.new(person, cat, karmavalue)
            else:
                cache.karmavalue = karmavalue
        ztm.commit()


if __name__ == '__main__':
    parser = OptionParser()
    logger_options(parser)
    (options, arguments) = parser.parse_args()
    if arguments:
        parser.error("Unhandled arguments %s" % repr(arguments))
    execute_zcml_for_scripts()

    log = logger(options, 'karmacache')
    log.info("Updating the karma cache of Launchpad users.")

    lockfile = LockFile(_default_lock_file, logger=log)
    try:
        lockfile.acquire()
    except OSError:
        log.info("lockfile %s already exists, exiting", _default_lock_file)
        sys.exit(1)

    try:
        update_karma_cache()
    finally:
        lockfile.release()

    log.info("Finished updating the karma cache of Launchpad users.")

