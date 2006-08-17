# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Test harness for Ticket Tracker related unit tests.

"""

__metaclass__ = type

__all__ = []

import unittest

from zope.testing.doctest import DocFileSuite

from canonical.launchpad.ftests.test_system_documentation import (
    default_optionflags)

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(DocFileSuite('ticketcontextmenu.txt',
                  optionflags=default_optionflags))
    return suite

if __name__ == '__main__':
    unittest.main()

