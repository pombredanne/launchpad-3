#! /usr/bin/env python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Run all the Launchpad-Mailman integration tests, in order."""

import os
import sys
import shutil
import traceback
import itest_helper

from operator import itemgetter

sys.path.insert(0, itest_helper.TOP)
sys.path.insert(1, os.path.join(itest_helper.TOP, 'mailman'))

from canonical.launchpad.scripts import execute_zcml_for_scripts
execute_zcml_for_scripts()
itest_helper.create_transaction_manager()


def real_main():
    """Search for all sub-tests and run them in order."""
    tests = []
    for filename in os.listdir(itest_helper.HERE):
        if os.path.splitext(filename)[1] <> '.py':
            continue
        try:
            index = int(filename[:2])
        except (ValueError, IndexError):
            continue
        path = os.path.join(itest_helper.HERE, filename)
        tests.append((index, path, filename))

    for index, path, filename in sorted(tests, key=itemgetter(0)):
        print 'WORKING:', filename,
        sys.stdout.flush()
        namespace = {}
        execfile(path, namespace)
        main = namespace['main']
        try:
            main()
        except itest_helper.IntegrationTestFailure, error:
            print 'FAILED:', error
            return -1
        except itest_helper.IntegrationTestTimeout:
            print 'TIMEOUT!'
            traceback.print_exc()
            -1
        except Exception:
            print
            traceback.print_exc()
            return -1
        else:
            print 'PASSED'

    return 0


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
        return real_main()
    finally:
        os.remove(dst_path)


if __name__ == '__main__':
    sys.exit(main())
