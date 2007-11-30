# Copyright 2005 Canonical Ltd.  All rights reserved.

"""Functions related to the import of Debbugs bugs into Malone."""

__all__ = [
    'bug_filter',
    'do_import',
    'import_bug',
    ]

__metaclass__ = type

import datetime
import sys

from zope.component import getUtility

from canonical.database.sqlbase import flush_database_updates
from canonical.encoding import guess as ensure_unicode
from canonical.launchpad.interfaces import (
    IBugSet, IMessageSet, ILaunchpadCelebrities, UnknownSender, IBugTaskSet,
    IBugWatchSet, ICveSet, InvalidEmailMessage, CreateBugParams)
from canonical.launchpad.scripts import debbugs


def bug_filter(bug, previous_import_set, target_bugs, target_package_set,
    minimum_age):
    """Function to choose which debian bugs will get processed by the sync
    script.
    """
    # don't re-import one that exists already
    if str(bug.id) in previous_import_set:
        return False
    # if we've been given a list, import only those
    if target_bugs:
        if bug.id in target_bugs:
            return True
        return False
    # we only want bugs in Sid
    if not bug.affects_unstable():
        return False
    # and we only want RC bugs
    #if not bug.is_release_critical():
    #    return False
    # and we only want bugs that affect the packages we care about:
    if not bug.affects_package(target_package_set):
        return False
    # we will not import any dup bugs (any reason to?)
    if len(bug.mergedwith) > 0:
        return False
    # and we won't import any bug that is newer than one week, to give
    # debian some time to find dups
    if bug.date > datetime.datetime.now()-datetime.timedelta(minimum_age):
        return False
    return True


def do_import(logger, max_imports, debbugs_location, target_bugs,
    target_package_set, previous_import_set, minimum_age, debbugs_pl):

    # figure out which bugs have been imported previously
    debbugs_tracker = getUtility(ILaunchpadCelebrities).debbugs
    for w in debbugs_tracker.watches:
        previous_import_set.add(w.remotebug)
    logger.info('%d debian bugs previously imported.' %
        len(previous_import_set))

    # find the new bugs to import
    logger.info('Selecting new debian bugs...')
    debbugs_db = debbugs.Database(debbugs_location, debbugs_pl)
    debian_bugs = []
    for debian_bug in debbugs_db:
        if bug_filter(debian_bug, previous_import_set, target_bugs,
            target_package_set, minimum_age):
            debian_bugs.append(debian_bug)
    logger.info('%d debian bugs ready to import.' % len(debian_bugs))

    # put them in ascending order
    logger.info('Sorting bugs...')
    debian_bugs.sort(lambda a, b: cmp(a.id, b.id))

    logger.info('Importing bugs...')
    newbugs = 0
    for debian_bug in debian_bugs:
        newbug = import_bug(debian_bug, logger)
        if newbug is True:
            newbugs += 1
        if max_imports:
            if newbugs >= max_imports:
                logger.info('Imported %d new bugs!' % newbugs)
                break


def import_bug(debian_bug, logger):
    """Consider importing a debian bug, return True if you did."""
    packagelist = debian_bug.packagelist()
    bugset = getUtility(IBugSet)
    debbugs_tracker = getUtility(ILaunchpadCelebrities).debbugs
    malone_bug = bugset.queryByRemoteBug(debbugs_tracker, debian_bug.id)
    if malone_bug is not None:
        logger.error('Debbugs #%d was previously imported.' % debian_bug.id)
        return False
    # get the email which started it all
    try:
        email_txt = debian_bug.comments[0]
    except IndexError:
        logger.error('No initial mail for debian #%d' % debian_bug.id)
        return False
    except debbugs.LogParseFailed, e:
        logger.warning(e)
        return False
    msg = None
    messageset = getUtility(IMessageSet)
    debian = getUtility(ILaunchpadCelebrities).debian
    ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
    try:
        msg = messageset.fromEmail(email_txt, distribution=debian,
            create_missing_persons=True)
    except UnknownSender:
        logger.error('Cannot create person for %s' % sys.exc_value)
    except InvalidEmailMessage:
        logger.error('Invalid email: %s' % sys.exc_value)
    if msg is None:
        logger.error('Failed to import debian #%d' % debian_bug.id)
        return False

    # get the bug details
    title = debian_bug.subject
    if not title:
        title = 'Debbugs #%d with no title' % debian_bug.id
    title = ensure_unicode(title)
    # debian_bug.package may have ,-separated package names, but
    # debian_bug.packagelist[0] is going to be a single package name for
    # sure. we work through the package list, try to find one we can
    # work with, otherwise give up
    srcpkg = binpkg = pkgname = None
    for pkgname in debian_bug.packagelist():
        try:
            srcpkg, binpkg = ubuntu.guessPackageNames(pkgname)
        except ValueError:
            logger.error(sys.exc_value)
    if srcpkg is None:
        # none of the package names gave us a source package we can use
        # XXX sabdfl 2005-09-16: Maybe this should just be connected to the
        # distro, and allowed to wait for re-assignment to a specific package?
        logger.error('Unable to find package details for %s' % (
            debian_bug.package))
        return False
    # sometimes debbugs has initial emails that contain the package name, we
    # can remove that
    if title.startswith(pkgname+':'):
        title = title[len(pkgname)+2:].strip()
    params = CreateBugParams(
        title=title, msg=msg, owner=msg.owner,
        datecreated=msg.datecreated)
    params.setBugTarget(distribution=debian, sourcepackagename=srcpkg)
    malone_bug = bugset.createBug(params)
    # create a debwatch for this bug
    thewatch = malone_bug.addWatch(debbugs_tracker, str(debian_bug.id),
        malone_bug.owner)
    thewatch.remotestatus = debian_bug.status

    # link the relevant task to this watch
    assert len(malone_bug.bugtasks) == 1, 'New bug should have only one task'
    task = malone_bug.bugtasks[0]
    task.bugwatch = thewatch
    task.setStatusFromDebbugs(debian_bug.status)
    task.setSeverityFromDebbugs(debian_bug.severity)

    # Let the world know about it!
    logger.info('%d/%s: %s: %s' % (
        debian_bug.id, malone_bug.id, debian_bug.package, title))

    # now we need to analyse the message for bugwatch clues
    bugwatchset = getUtility(IBugWatchSet)
    watches = bugwatchset.fromMessage(msg, malone_bug)
    for watch in watches:
        logger.info('New watch for %s on %s' % (watch.bug.id, watch.url))

    # and also for CVE ref clues
    cveset = getUtility(ICveSet)
    cves = cveset.inMessage(msg)
    prior_cves = malone_bug.cves
    for cve in cves:
        if cve not in prior_cves:
            malone_bug.linkCVE(cve)
            logger.info('CVE-%s (%s) found for Malone #%s' % (
                cve.sequence, cve.status.name, malone_bug.id))

    flush_database_updates()
    return True


