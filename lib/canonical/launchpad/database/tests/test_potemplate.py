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
        expected = "testdir/testdomain-eo.po"
        result = self.potemplate._composePOFilePath('eo')
        self.failUnlessEqual(expected, result,
            "_composePOFilePath does not create a correct file name with "
            "directory and language code. "#
            "(Expected: '%s' Got: '%s')" % (expected, result)
            )

        self.potemplate.path = "testdir/messages.pot"
        expected = "testdir/testdomain-eo@VARIANT.po"
        result = self.potemplate._composePOFilePath('eo', 'VARIANT')
        self.failUnlessEqual(expected, result,
            "_composePOFilePath does not create a correct file name with "
            "directory, language code and variant. "
            "(Expected: '%s' Got: '%s')" % (expected, result)
            )

        self.potemplate.path = "/messages.pot"
        expected = "/testdomain-eo.po"
        result = self.potemplate._composePOFilePath('eo')
        self.failUnlessEqual(expected, result,
            "_composePOFilePath does not create a correct file name with "
            "leading slash and language code. "
            "(Expected: '%s' Got: '%s')" % (expected, result)
            )

        self.potemplate.path = "messages.pot"
        expected = "testdomain-eo.po"
        result = self.potemplate._composePOFilePath('eo')
        self.failUnlessEqual(expected, result,
            "_composePOFilePath does not create a correct file name with "
            "missing directory and language code. "
            "(Expected: '%s' Got: '%s')" % (expected, result)
            )


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestPOTemplate))
    return suite
