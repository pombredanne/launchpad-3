#! /usr/bin/env python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Run all the Launchpad-Mailman integration tests, in order."""


import os
import sys
from operator import itemgetter

here = os.path.abspath(os.path.dirname(sys.argv[0]))
top = os.path.normpath(os.path.join(here, '../../../..'))
sys.path.insert(0, top)

MAILMAN_BIN = os.path.normpath(os.path.join(
    os.path.dirname(sys.argv[0]), '../../../../', 'mailman', 'bin'))

from canonical.launchpad.scripts import execute_zcml_for_scripts
execute_zcml_for_scripts()

# Set up the  connection to the database.  We use the 'testadmin' uses because
# it has rights to do nasty things like delete Person entries.
from canonical.lp import initZopeless
transactionmgr = initZopeless(dbuser='testadmin')

class IntegrationTestFailure(Exception):
    """An integration test failed."""


def main():
    # Global namespace for all integration test scripts.
    namespace = {
        'transactionmgr': transactionmgr,
        'IntegrationTestFailure': IntegrationTestFailure,
        'MAILMAN_BIN': MAILMAN_BIN,
        }

    # Search for all sub-tests and run them in order.
    tests = []
    for filename in os.listdir(here):
        try:
            index = int(filename[:2])
        except (ValueError, IndexError):
            continue
        path = os.path.join(here, filename)
        tests.append((index, path, filename))

    for index, path, filename in sorted(tests, key=itemgetter(0)):
        print 'WORKING:', filename,
        sys.stdout.flush()
        execfile(path, namespace)
        main = namespace['main']
        try:
            main()
        except IntegrationTestFailure, error:
            print 'FAILED:', error
            return -1
        else:
            print 'PASSED'

    return 0


if __name__ == '__main__':
    sys.exit(main())
