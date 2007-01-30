#!/usr/bin/env python

# This script runs through the set of Debbugs watches, and tries to
# syncronise each of those to the malone bug which is watching it.

import os
import sys
import email
import logging
import _pythonpath
from optparse import OptionParser

# zope bits
from zope.component import getUtility

from contrib.glock import GlobalLock, LockAlreadyAcquired

# canonical launchpad modules
from canonical.lp import initZopeless
from canonical.launchpad.scripts import (execute_zcml_for_scripts,
    logger_options, logger as logger_from_options)
    
from canonical.launchpad.interfaces import (IBugSet,
    ILaunchpadCelebrities, InvalidEmailMessage, IBugTaskSet,
    IBugWatchSet, IMessageSet, ISourcePackageSet, ICveSet,
    BugTaskSearchParams)
from canonical.database.constants import UTC_NOW

# debsync-specific modules
import debbugs

# setup core values and defaults
debbugs_location_default = '/srv/bugs-mirror.debian.org/'

def sync(ztm, logger, max_syncs, debbugs_location):

    changedcounter = 0

    debbugs_db = debbugs.Database(debbugs_location)

    logger.info('Finding existing debbugs watches...')
    debbugs_tracker = getUtility(ILaunchpadCelebrities).debbugs
    debwatches = debbugs_tracker.watches

    previousimportset = set([b.remotebug for b in debwatches])
    logger.info('%d debbugs previously imported.' % len(previousimportset))

    target_watches = [watch for watch in debwatches if watch.needscheck]
    logger.info('%d debbugs watches to syncronise.' % len(target_watches))

    logger.info('Sorting bug watches...')
    target_watches.sort(key=lambda a: a.remotebug)

    logger.info('Syncing bug watches...')
    for watch in target_watches:
        waschanged = sync_watch(watch, ztm, logger, debbugs_db)
        if waschanged:
            changedcounter += 1
            ztm.commit()
        if max_syncs:
            if changedcounter >= max_syncs:
                logger.info('Synchronised %d bugs!' % changedcounter)
                break


def sync_watch(watch, ztm, logger, debbugs_db):
    # keep track of whether or not something changed
    waschanged = False
    # find the bug in malone
    malone_bug = watch.bug
    # find the bug in debbugs
    debian_bug = debbugs_db[int(watch.remotebug)]
    bugset = getUtility(IBugSet)
    bugtaskset = getUtility(IBugTaskSet)
    bugwatchset = getUtility(IBugWatchSet)
    messageset = getUtility(IMessageSet)
    debian = getUtility(ILaunchpadCelebrities).debian
    debbugs_tracker = getUtility(ILaunchpadCelebrities).debbugs
    srcpkgset = getUtility(ISourcePackageSet)

    # make sure we have tasks for all the debian package linkages, and also
    # make sure we have updated their status and severity appropriately
    for packagename in debian_bug.packagelist():
        try:
            srcpkgname, binpkgname = srcpkgset.getPackageNames(packagename)
        except ValueError:
            logger.error(sys.exc_value)
            continue
        search_params = BugTaskSearchParams(user=None, bug=malone_bug,
            sourcepackagename=srcpkgname)
        search_params.setDistribution(debian)
        bugtasks = bugtaskset.search(search_params)
        if len(bugtasks) == 0:
            # we need a new task to link the bug to the debian package
            logger.info('Linking %d and debian %s/%s' % (
                malone_bug.id, srcpkgname.name, binpkgname.name))
            # XXX: this code is completely untested and broken XXX
            bugtask = malone_bug.addTask(
                owner=malone_bug.owner, distribution=debian,
                sourcepackagename=srcpkgname)
            bugtask.bugwatch = watch
            waschanged = True
        else:
            assert len(bugtasks) == 1, 'Should only find a single task'
            bugtask = bugtasks[0]
        status = bugtask.status
        if status <> bugtask.setStatusFromDebbugs(debian_bug.status):
            waschanged = True
        severity = bugtask.severity
        if severity <> bugtask.setSeverityFromDebbugs(debian_bug.severity):
            waschanged = True

    known_msg_ids = set([msg.rfc822msgid for msg in malone_bug.messages])

    for raw_msg in debian_bug.comments:

        # parse it so we can extract the message id easily
        message = email.message_from_string(raw_msg)

        # see if we already have imported a message with this id for this
        # bug
        message_id = message['message-id']
        if message_id in known_msg_ids:
            # Skipping msg that is already imported
            continue

        # make sure this message is in the db
        msg = None
        try:
            msg = messageset.fromEmail(raw_msg, parsed_message=message,
                create_missing_persons=True)
        except InvalidEmailMessage:
            logger.error('Invalid email: %s' % sys.exc_value)
        if msg is None:
            continue

        # create the link between the bug and this message
        bugmsg = malone_bug.linkMessage(msg)

        # ok, this is a new message for this bug, so in effect something has
        # changed
        waschanged = True

        # now we need to analyse the message for useful data
        watches = bugwatchset.fromMessage(msg, malone_bug)
        for watch in watches:
            logger.info('New watch for #%s on %s' % (watch.bug.id, watch.url))
            waschanged = True

        # and also for CVE ref clues
        prior_cves = set(malone_bug.cves)
        cveset = getUtility(ICveSet)
        cves = cveset.inMessage(msg)
        for cve in cves:
            malone_bug.linkCVE(cve)
            if cve not in prior_cves:
                logger.info('CVE-%s (%s) found for Malone #%s' % (
                    cve.sequence, cve.status.name, malone_bug.id))

        # now we know about this message for this bug
        known_msg_ids.add(message_id)

        # and best we commit, so that we can see the email that the
        # librarian has created in the db
        ztm.commit()

    # Mark all merged bugs as duplicates of the lowest-numbered bug
    if (len(debian_bug.mergedwith) > 0 and
        min(debian_bug.mergedwith) > debian_bug.id):
        for merged_id in debian_bug.mergedwith:
            merged_bug = bugset.queryByRemoteBug(debbugs_tracker, merged_id)
            if merged_bug is not None:
                # Bug has been imported already
                if merged_bug.duplicateof == malone_bug:
                    # we already know about this
                    continue
                elif merged_bug.duplicateof is not None:
                    # Interesting, we think it's a dup of something else
                    logger.warning('Debbugs thinks #%d is a dup of #%d' % (
                        merged_bug.id, merged_bug.duplicateof))
                    continue
                # Go ahead and merge it
                logger.info("Malone #%d is a duplicate of Malone #%d" % (
                    merged_bug.id, malone_bug.id))
                merged_bug.duplicateof = malone_bug.id

                # the dup status has changed
                waschanged = True

    # make a note of the remote watch status, if it has changed
    if watch.remotestatus <> debian_bug.status:
        watch.remotestatus = debian_bug.status
        waschanged = True

    # update the watch date details
    watch.lastchecked = UTC_NOW
    if waschanged:
        watch.lastchanged = UTC_NOW
        logger.info('Watch on Malone #%d changed.' % watch.bug.id)
    return waschanged


def main(args):
    parser = OptionParser()
    logger_options(parser, logging.WARNING)
    parser.set_defaults(max=None, debbugs=debbugs_location_default)
    parser.add_option('--max', action='store', type='int', dest='max',
        default=None, help="The maximum number of bugs to synchronise.")
    parser.add_option('--debbugs', action='store', type='string',
        dest='debbugs',
        help="The location of your debbugs database.")
    options, args = parser.parse_args()
    logger = logger_from_options(options)

    # make sure the debbugs location looks sane
    if not os.path.exists(os.path.join(options.debbugs, 'index/index.db')):
        logger.error('%s is not a debbugs db.' % options.debbugs)
        return 1

    lockfile_path = '/var/lock/launchpad-debbugs-sync.lock'
    lockfile = GlobalLock(lockfile_path)
    try:
        lockfile.acquire()
    except LockAlreadyAcquired:
        logger.error('Lockfile %s already exists, exiting.' % lockfile_path)
        return 0

    try:
        logger.info('Setting up utilities...')
        execute_zcml_for_scripts()
        ztm = initZopeless()
        ztm.begin()
        sync(ztm, logger, options.max, options.debbugs)
        ztm.commit()
    except:
        logger.exception('Uncaught exception!')
        lockfile.release()
        return 1

    logger.info('Done!')
    lockfile.release()
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))

