#! /usr/bin/env python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Run all the Launchpad-Mailman integration doctests in this directory."""

import os
import re
import sys
import errno
import shutil
import doctest
import optparse
import unittest
# pylint: disable-msg=W0403
import itest_helper

sys.path.insert(0, itest_helper.TOP)
sys.path.insert(1, os.path.join(itest_helper.TOP, 'mailman'))

from canonical.database.sqlbase import cursor
from canonical.launchpad.scripts import execute_zcml_for_scripts
# pylint: disable-msg=F0401
from Mailman.mm_cfg import QUEUE_DIR, VAR_PREFIX

execute_zcml_for_scripts()

# Initialize zopeless mode, which sets up a global transaction manager.
from canonical.lp import initZopeless
initZopeless(dbuser='testadmin')

from canonical.database.sqlbase import commit


DOCTEST_FLAGS = (doctest.ELLIPSIS |
                 doctest.NORMALIZE_WHITESPACE |
                 doctest.REPORT_NDIFF)


def integrationTestSetUp(testobj):
    """Set up for all integration doctests."""
    # We'll always need an smtp server.
    smtpd = itest_helper.SMTPServer()
    smtpd.start()
    if testobj is not None:
        testobj.globs['smtpd'] = smtpd


def integrationTestCleanUp(testobj):
    """Common tear down for the integration tests."""
    # Ensure the smtp server is stopped and cleared.
    if testobj is not None:
        smtpd = testobj.globs['smtpd']
        smtpd.reset()
        smtpd.stop()
    cursor().execute("""
    CREATE TEMP VIEW DeathRow AS SELECT id FROM Person WHERE name IN (
    'itest-one', 'itest-two', 'itest-three',
    'anne', 'bart', 'cris', 'dirk', 'emma'
    );

    DELETE FROM AnswerContact
    WHERE person in (SELECT id FROM DeathRow);

    DELETE FROM PersonLanguage
    WHERE person in (SELECT id FROM DeathRow);

    DELETE FROM SpecificationSubscription
    WHERE person in (SELECT id FROM DeathRow);

    DELETE FROM MailingListSubscription
    WHERE person in (SELECT id FROM DeathRow);

    DELETE FROM EmailAddress
    WHERE person in (SELECT id FROM DeathRow);

    DELETE FROM TeamMembership
    WHERE team IN (SELECT id FROM DeathRow);

    DELETE FROM TeamMembership
    WHERE person IN (SELECT id FROM DeathRow);

    DELETE FROM TeamParticipation
    WHERE team IN (SELECT id FROM DeathRow);

    DELETE FROM TeamParticipation
    WHERE person IN (SELECT id FROM DeathRow);

    DELETE FROM MessageChunk
    WHERE message IN (SELECT id from Message WHERE owner IN
                      (SELECT id FROM DeathRow));

    DELETE FROM Message
    WHERE owner IN (SELECT id FROM DeathRow);

    DELETE FROM MessageApproval
    WHERE mailing_list IN (SELECT id from MailingList WHERE team IN
                           (SELECT id FROM DeathRow));

    DELETE FROM MailingList
    WHERE team IN (SELECT id FROM DeathRow);

    DELETE FROM WikiName
    WHERE person IN (SELECT id FROM DeathRow);

    DELETE FROM BugSubscription
    WHERE person IN (SELECT id FROM DeathRow);

    DELETE FROM Person
    WHERE id IN (SELECT id FROM DeathRow);
    """)
    commit()
    # Clear out any qfiles hanging around from a previous run.  Do this first
    # to prevent stale list references.
    for dirpath, dirnames, filenames in os.walk(QUEUE_DIR):
        for filename in filenames:
            if os.path.splitext(filename)[1] == '.pck':
                os.remove(os.path.join(dirpath, filename))
    # Now delete any mailing lists still hanging around.  We don't care if
    # this fails because it means the list doesn't exist.  While we're at it,
    # remove any related archived backup files.
    for team_name in ('itest-one', 'itest-two', 'itest-three', 'fake-team'):
        try:
            itest_helper.run_mailman('./rmlist', '-a', team_name)
        except itest_helper.IntegrationTestFailure:
            pass
        backup_file = os.path.join(
            VAR_PREFIX, 'backups', '%s.tgz' % team_name)
        try:
            os.remove(backup_file)
        except OSError, error:
            if error.errno != errno.ENOENT:
                raise
        # Delete the MHonArc archives if they exist.
        path = os.path.join(VAR_PREFIX, 'mhonarc')
        try:
            shutil.rmtree(path)
        except OSError, error:
            if error.errno != errno.ENOENT:
                raise
    # Clean up the library data.  Remove only the librarian files, not any
    # intermediate directories.
    from canonical.config import config
    for dirpath, dirnames, filenames in os.walk(config.librarian_server.root):
        for filename in filenames:
            path = os.path.join(dirpath, filename)
            os.remove(path)
    # Remove all the locks except the master lock.
    lock_dir = os.path.join(VAR_PREFIX, 'locks')
    for filename in os.listdir(lock_dir):
        if not filename.startswith('master-qrunner'):
            os.remove(os.path.join(lock_dir, filename))
    # Remove all held messages.
    data_dir = os.path.join(VAR_PREFIX, 'data')
    for filename in os.listdir(data_dir):
        if filename.startswith('heldmsg'):
            os.remove(os.path.join(data_dir, filename))


def find_tests(match_regexps):
    """Search for doctests with filenames that match the given regexps.

    Return a unittest.TestSuite object.
    """
    # Ensure we start with a clean world.
    integrationTestCleanUp(None)
    suite = unittest.TestSuite()
    for filename in os.listdir(itest_helper.HERE):
        if match_regexps:
            for regexp in match_regexps:
                if re.search(regexp, filename, re.IGNORECASE):
                    break
            else:
                continue
        if os.path.splitext(filename)[1] != '.txt':
            continue
        test = doctest.DocFileSuite(
            filename,
            setUp=integrationTestSetUp,
            tearDown=integrationTestCleanUp,
            optionflags=DOCTEST_FLAGS)
        suite.addTest(test)
    return suite


def v_callback(option, opt, value, parser):
    """Process the -v/--verbose and -q/--quiet options."""
    if opt in ('-q', '--quiet'):
        delta = -1
    elif opt in ('-v', '--verbose'):
        delta = 1
    else:
        raise AssertionError('Unexpected option: %s' % opt)
    dest = getattr(parser.values, option.dest)
    setattr(parser.values, option.dest, max(0, dest + delta))


def parseargs():
    parser = optparse.OptionParser(usage="""\
%prog [options]

Run the Launchpad/Mailman integration test suite.""")
    parser.set_defaults(verbosity=2)
    parser.add_option('-v', '--verbose',
                      action='callback', callback=v_callback,
                      dest='verbosity', help="""\
Increase verbosity by 1, which defaults to %default.  Use -q to reduce
verbosity.  -v and -q options accumulate.""")
    parser.add_option('-q', '--quiet',
                      action='callback', callback=v_callback,
                      dest='verbosity', help="""\
Reduce verbosity by 1 (but not below 0).""")
    opts, args = parser.parse_args()
    return parser, opts, args


def main():
    """Run all the integration doctests.

    Return True if there were failures or errors, otherwise False.
    """
    parser, opts, args = parseargs()
    suite = find_tests(args)
    runner = unittest.TextTestRunner(verbosity=opts.verbosity)
    results = runner.run(suite)
    if results.failures or results.errors:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
