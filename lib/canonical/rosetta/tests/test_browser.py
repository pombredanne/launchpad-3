# Copyright 2004 Canonical Ltd.  All rights reserved.
#
# arch-tag: 05d714d2-c14d-4f72-bfc3-f210d0ee052d

__metaclass__ = type

import unittest
from cStringIO import StringIO

from zope.testing.doctestunit import DocTestSuite
from zope.interface import implements
from zope.publisher.interfaces.browser import IBrowserRequest

from canonical.launchpad.interfaces import ILanguageSet, \
    IPerson, IDistributionSet, ILaunchBag
from canonical.launchpad.browser.tests.test_pofile import DummyProduct, \
    DummyRequest


class DummyProject:
    def products(self):
        return [DummyProduct(), DummyProduct()]

def test_RosettaProjectView():
    """
    >>> from canonical.launchpad.browser import ProjectView
    >>> view = ProjectView(DummyProject(), DummyRequest())
    >>> view.hasProducts()
    True
    """

def test_suite():
    return DocTestSuite()

if __name__ == '__main__':
    unittest.TextTestRunner().run(test_suite())

