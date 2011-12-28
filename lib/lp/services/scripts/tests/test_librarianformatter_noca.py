# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Python harness for librarianformatter_noca.txt."""

__metaclass__ = type

from lp.testing import reset_logging
from lp.testing.systemdocs import LayeredDocFileSuite


def setUp(test):
    # Suck this modules environment into the test environment
    reset_logging()

def tearDown(test):
    reset_logging()

def test_suite():
    return LayeredDocFileSuite(
        'librarianformatter_noca.txt',
        setUp=setUp, tearDown=tearDown, stdout_logging=False)
