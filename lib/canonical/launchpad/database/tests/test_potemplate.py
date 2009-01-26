# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest

from zope.security.proxy import removeSecurityProxy

from canonical.testing import DatabaseFunctionalLayer
from canonical.launchpad.testing import TestCaseWithFactory


class TestPOTemplate(TestCaseWithFactory):
    """Test POTemplate functions not covered by doctests."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.potemplate = removeSecurityProxy(self.factory.makePOTemplate(
            translation_domain = "testdomain"))

    def test_composePOFilePath(self):
        self.potemplate.path = "testdir/messages.pot"
        self.failUnlessEqual(
            self.potemplate._composePOFilePath('eo'),
            "testdir/testdomain-eo.po",
            "_composePOFilePath does not create a correct file name with "
            "directory and language code."
            )

        self.potemplate.path = "testdir/messages.pot"
        self.failUnlessEqual(
            self.potemplate._composePOFilePath('eo', 'VARIANT'),
            "testdir/testdomain-eo@VARIANT.po",
            "_composePOFilePath does not create a correct file name with "
            "directory, language code and variant."
            )

        self.potemplate.path = "/messages.pot"
        self.failUnlessEqual(
            self.potemplate._composePOFilePath('eo'),
            "testdomain-eo.po",
            "_composePOFilePath does not create a correct file name with "
            "leading slash and language code."
            )

        self.potemplate.path = "messages.pot"
        self.failUnlessEqual(
            self.potemplate._composePOFilePath('eo'),
            "testdomain-eo.po",
            "_composePOFilePath does not create a correct file name with "
            "missing directory and language code."
            )


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestPOTemplate))
    return suite
