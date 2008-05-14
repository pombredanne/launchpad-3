# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Run the standalone launchpadlib tests.

XXX BarryWarsaw 14-May-2008: This shim is here that the tests within the
launchpadlib package will run as part of Launchpad's standard test suite.
Those tests cannot yet be run on their own, since they require a running
Launchpad appserver (but not the real Launchpad!).  Eventually, there will be
mock objects in the package's test suite so that it can be run on its own
outside the Launchpad development environment.
"""

__metaclass__ = type
__all__ = []


import os
import unittest
import launchpadlib

from canonical.launchpad.testing.systemdocs import LayeredDocFileSuite

topdir = os.path.dirname(launchpadlib.__file__)


def test_suite():
    suite = unittest.TestSuite()

    # Find all the doctests in launchpadlib.
    packages = []
    for dirpath, dirnames, filenames in os.walk(topdir):
        if 'docs' in dirnames:
            docsdir = os.path.join(dirpath, 'docs')[len(topdir)+1:]
            packages.append(docsdir)
    doctest_files = {}
    for docsdir in packages:
        for filename in os.listdir(os.path.join(topdir, docsdir)):
            if os.path.splitext(filename)[1] == '.txt':
                doctest_files[filename] = os.path.join(docsdir, filename)
    # Sort the tests.
    for filename in sorted(doctest_files):
        path = doctest_files[filename]
        # XXX BarryWarsaw 14-May-2008: Full implementation of these tests will
        # require the AppServerLayer branch, which is currently in separate
        # review.  For now, until that branch lands, these tests are extremely
        # simple.
        doctest = LayeredDocFileSuite(path, package=launchpadlib)
        suite.addTest(doctest)

    return suite
