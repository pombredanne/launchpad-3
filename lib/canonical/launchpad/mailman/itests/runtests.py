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
import traceback
import itest_helper

from operator import itemgetter

sys.path.insert(0, itest_helper.TOP)
sys.path.insert(1, os.path.join(itest_helper.TOP, 'mailman'))

from canonical.launchpad.scripts import execute_zcml_for_scripts
execute_zcml_for_scripts()
itest_helper.create_transaction_manager()


def find_tests():
    """Search for all tests.

    This is a generator, returning 2-tuples of the tests to run, in order.
    The tuple contains the test's full path and the file's short name for
    display during the test run.
    """
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
        yield path, filename


def real_main():
    """Search for all sub-tests and run them in order.

    Returns an exit code, which is passed to sys.exit().
    """

    for path, filename in find_tests():
        print 'WORKING:', filename,
        sys.stdout.flush()
        namespace = {}
        execfile(path, namespace)
        main = namespace['main']
        try:
            main()
        except itest_helper.IntegrationTestFailure, error:
            print 'FAILED:', error
            return 1
        except itest_helper.IntegrationTestTimeout:
            print 'TIMEOUT!'
            traceback.print_exc()
            return 1
        except Exception:
            print
            traceback.print_exc()
            return 1
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
