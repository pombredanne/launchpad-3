#!/usr/bin/env python
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""
Given an error report, run all of the failed tests again.

For instance, it can be used in the following scenario:
% bin/test -vvm lp.registry | tee test.out
% # Oh nos!  Failures!
% # Fix tests.
% utilities/retest.py test.out
"""

import subprocess
import sys
import re
from pprint import pprint

# Regular expression to match numbered stories.
STORY_RE = re.compile("(.*)/\d{2}-.*")


def getTestName(test):
    """Get the test name of a failed test.

    If the test is part of a numbered story,
    e.g. 'stories/gpg-coc/01-claimgpgp.txt', then return the directory name
    since all of the stories must be run together.
    """
    match = STORY_RE.match(test)
    if match:
        return match.group(1)
    return test


def extractTests(fd):
    """Get the set of tests to be run.

    Given an open file descriptor pointing to a test summary report, find all
    of the tests to be run.
    """
    failed_tests = set()
    reading_tests = False
    line = True
    while (line):
        line = fd.readline()
        if line.startswith('Tests with failures:'):
            reading_tests = True
            continue
        if reading_tests:
            if line.startswith('Total:'):
                break
            test = getTestName(line.strip())
            failed_tests.add(test)
    return failed_tests


def run_tests(tests):
    """Given a set of tests, run them as one group."""
    cmd = ['bin/test', '-vv']
    print "Running tests:"
    pprint(sorted(list(tests)))
    for test in tests:
        cmd.append('-t')
        cmd.append(test)
    p = subprocess.Popen(cmd)
    p.wait()


if __name__ == '__main__':
    try:
        log_file = sys.argv[1]
    except IndexError:
        print "Usage: %s test_output_file" % (sys.argv[0])
        sys.exit(-1)
    fd = open(log_file, 'r')
    failed_tests = extractTests(fd)
    run_tests(failed_tests)
