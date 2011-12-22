# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Python harness for librarianformatter_noca.txt."""

__metaclass__ = type

from canonical.launchpad.testing.systemdocs import LayeredDocFileSuite
from canonical.testing import reset_logging


def setUp(test):
    # Suck this modules environment into the test environment
    reset_logging()

def tearDown(test):
    reset_logging()

def test_suite():
    return LayeredDocFileSuite(
        'librarianformatter_noca.txt',
        setUp=setUp, tearDown=tearDown, stdout_logging=False)
