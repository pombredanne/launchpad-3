#!/usr/bin/python
# Copyright 2009 Canonical Ltd.  All rights reserved.
"""
A script for running all of the windmill JavaScript integration test suites
in Launchpad.  Aggregates the result of running each suite into a global
pass or fail value.

The script exit codes are:
    0: suite success
    1: suite error
    2: suite failure

"""


import subprocess
import os
import sys


# Test runner configuration hash
runner_config = {
    'runner':  'bin/lp-windmill',
    'port':    8085,
    'browser': 'firefox',
}

# Test suite configuration
test_root_dir = 'lib/canonical/launchpad/windmill/tests/'

# A hash of test suites to run.  Each key has two parts: the path to the test
# suite root directory (relative to the test root directory) and the domain
# that the test runner must use during suite execution.
test_suites = {
    'registry': {
        'suite_dir': 'test_registry',
        'domain':    'launchpad.dev'
    },
    'bugs': {
        'suite_dir': 'test_bugs',
        'domain':    'bugs.launchpad.dev'
    },
    'soyuz': {
        'suite_dir': 'test_soyuz',
        'domain':    'launchpad.dev'
    },
    'translations': {
        'suite_dir': 'test_translations',
        'domain':    'translations.launchpad.dev'
    },
}


def run_suite(suite_config):
    """Run a JavaScript test suite using the given suite configuration."""
    config = runner_config.copy()
    config['url'] = 'http://%s:%s' % (
        suite_config['domain'],
        runner_config['port'])
    config['suite'] = os.path.join(test_root_dir, suite_config['suite_dir'])

    # Do we have a test runner?
    if not os.path.exists(config['runner']):
        sys.stderr.write(
            "Error: Couldn't find the testrunner executable: %s\n" % (
                config['runner']))
        sys.exit(1)

    # Do we have a test suite?
    if not os.path.exists(config['suite']):
        sys.stderr.write(
            "Error: Couldn't find the test suite: %s\n" % config['suite'])
        sys.exit(1)

    # The final test runner call.
    # Should be something like: windmill -e test=foo/bar firefox http://blah
    # Pass '-e' to the runner so it exits after suite completion.
    test_command = [
        config['runner'],
        "-e",
        "test=%s" % config['suite'],
        config['browser'],
        config['url'],
    ]

    try:
        retcode = subprocess.call(test_command)
    except OSError, e:
        sys.stderr.write(
            "Error: Test command failed to execute: " + test_command + "\n")
        sys.stderr.write("Exiting\n")
        sys.exit(1)


def run_all_windmills():
    """Run all of the available test suites.

    Returns the number of test suites that failed.
    """
    failures = 0

    for suite_name, suite_config in test_suites.items():
        print "Running the %s test suite" % suite_name

        success = run_suite(suite_config)

        if not success:
            print "Failure: Test failures in the %s test suite" % suite_name
            print
            failures += 1

    return failures


if __name__ == '__main__':
    failures = run_all_windmills()
    if failures != 0:
        print "Failed: %d test suites failed" % failures
        sys.exit(2)
    else:
        print "Success: all suites passed"
        sys.exit(0)
