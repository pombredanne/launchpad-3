# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Test harnest for Launchpad/Mailman doctests."""

import os
import doctest
import unittest
import subprocess


def call(command_template, *args):
    from canonical.config import config
    command = command_template % args
    mailman_bin = os.path.join(config.mailman.build.prefix, 'bin')
    return subprocess.call(command.split(), cwd=mailman_bin)


def setup(testobj):
    from canonical.config import config
    testobj.globs['config'] = config
    testobj.globs['call'] = call


def teardown(testobj):
    pass


def test_suite():
    suite = unittest.TestSuite()

    # If Mailman isn't even configured to be built, then there's really
    # nothing we can do.  This isn't completely correct because it doesn't
    # catch the case where Mailman was built, but then the 'build' key was set
    # back to false.  This is really better than testing to see if the Mailman
    # package is importable because, that we really want to do in the doctest!
    from canonical.config import config
    if config.mailman.build.build:
        test = doctest.DocFileSuite(
            'test-libmailman.txt',
            optionflags = (doctest.ELLIPSIS     |
                           doctest.REPORT_NDIFF |
                           doctest.NORMALIZE_WHITESPACE),
            setUp=setup, tearDown=teardown)
        suite.addTest(test)
    return suite
