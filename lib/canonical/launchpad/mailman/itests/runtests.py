#! /usr/bin/env python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Run all the Launchpad-Mailman integration tests, in order.

The tests are located by getting a list of all Python files in this directory,
and looking for those that start with a two digit number.  The tests are
numerically ordered by that two digit number.

The file is then execfile()'d and a main() function is pulled from the
namespace.  That main() function is then run with no arguments, and it should
perform all the tests for that step.
"""

import os
import sys
import shutil
import doctest
import unittest
import traceback
import itest_helper

from operator import itemgetter

sys.path.insert(0, itest_helper.TOP)
sys.path.insert(1, os.path.join(itest_helper.TOP, 'mailman'))

from canonical.database.sqlbase import cursor
from canonical.launchpad.scripts import execute_zcml_for_scripts
from Mailman.mm_cfg import QUEUE_DIR

execute_zcml_for_scripts()
itest_helper.create_transaction_manager()

DOCTEST_FLAGS = (doctest.ELLIPSIS |
                 doctest.NORMALIZE_WHITESPACE |
                 doctest.REPORT_NDIFF)


def integrationTestSetUp(test):
    """Common set up for the integration tests."""
    cursor().execute("""
    CREATE TEMP VIEW DeathRow AS SELECT id FROM Person WHERE name IN (
    'team-one', 'team-two', 'team-three',
    'anne', 'bart', 'cris', 'dirk'
    );

    DELETE FROM MailingListSubscription
    WHERE person in (SELECT id FROM DeathRow);

    DELETE FROM EmailAddress
    WHERE person in (SELECT id FROM DeathRow);

    DELETE FROM TeamMembership
    WHERE team IN (SELECT id FROM DeathRow);

    DELETE FROM TeamParticipation
    WHERE team IN (SELECT id FROM DeathRow);

    DELETE FROM MailingList
    WHERE team IN (SELECT id FROM DeathRow);

    DELETE FROM WikiName
    WHERE person IN (SELECT id FROM DeathRow);

    DELETE FROM Person
    WHERE id IN (SELECT id FROM DeathRow);
    """)
    itest_helper.transactionmgr.commit()
    # Now delete any mailing lists still hanging around.  We don't care if
    # this fails because it means the list doesn't exist.
    for team_name in ('team-one', 'team-two', 'team-three'):
        try:
            itest_helper.run_mailman('./rmlist', '-a', team_name)
        except itest_helper.IntegrationTestFailure:
            pass
    # Clear out any qfiles hanging around from a previous run.
    for dirpath, dirnames, filenames in os.walk(QUEUE_DIR):
        for filename in filenames:
            if os.path.splitext(filename)[1] == '.pck':
                os.remove(os.path.join(dirpath, filename))


def find_tests():
    """Search for doctests.

    Return a unittest.TestSuite object.
    """
    suite = unittest.TestSuite()
    for filename in os.listdir(itest_helper.HERE):
        if os.path.splitext(filename)[1] != '.txt':
            continue
        test = doctest.DocFileSuite(
            filename,
            setUp=integrationTestSetUp,
            optionflags=DOCTEST_FLAGS)
        suite.addTest(test)
    return suite


def run_tests():
    """Run all the integration doctests.

    Return True if there were failures or errors, otherwise False.
    """
    suite = find_tests()
    runner = unittest.TextTestRunner()
    results = runner.run(suite)
    return bool(results.failures or results.errors)


def main():
    """A main function with cleanup protection."""
    # Several of the tests require a bin/withlist helper to print useful
    # information about mailing lists.  Mailman requires the withlist script
    # to be in its bin directory or on sys.path.  Hacking the latter in the
    # subprocess is tricky, so it's easier to just copy the file in place.
    src_path = os.path.join(itest_helper.HERE, 'mmhelper.py')
    dst_path = os.path.join(itest_helper.MAILMAN_BIN, 'mmhelper.py')
    shutil.copyfile(src_path, dst_path)
    try:
        return run_tests()
    finally:
        os.remove(dst_path)


if __name__ == '__main__':
    sys.exit(main())
