# Copyright 2008-2009 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces.language import ILanguageSet
from canonical.testing import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory


class TestPOTemplate(TestCaseWithFactory):
    """Test POTemplate functions not covered by doctests."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.potemplate = removeSecurityProxy(self.factory.makePOTemplate(
            translation_domain = "testdomain"))

    def test_composePOFilePath(self):
        esperanto = getUtility(ILanguageSet).getLanguageByCode('eo')
        self.potemplate.path = "testdir/messages.pot"
        expected = "testdir/testdomain-eo.po"
        result = self.potemplate._composePOFilePath(esperanto)
        self.failUnlessEqual(expected, result,
            "_composePOFilePath does not create a correct file name with "
            "directory and language code. "
            "(Expected: '%s' Got: '%s')" % (expected, result)
            )

        self.potemplate.path = "testdir/messages.pot"
        expected = "testdir/testdomain-eo@VARIANT.po"
        result = self.potemplate._composePOFilePath(esperanto, 'VARIANT')
        self.failUnlessEqual(expected, result,
            "_composePOFilePath does not create a correct file name with "
            "directory, language code and variant. "
            "(Expected: '%s' Got: '%s')" % (expected, result)
            )

        self.potemplate.path = "/messages.pot"
        expected = "/testdomain-eo.po"
        result = self.potemplate._composePOFilePath(esperanto)
        self.failUnlessEqual(expected, result,
            "_composePOFilePath does not create a correct file name with "
            "leading slash and language code. "
            "(Expected: '%s' Got: '%s')" % (expected, result)
            )

        self.potemplate.path = "messages.pot"
        expected = "testdomain-eo.po"
        result = self.potemplate._composePOFilePath(esperanto)
        self.failUnlessEqual(expected, result,
            "_composePOFilePath does not create a correct file name with "
            "missing directory and language code. "
            "(Expected: '%s' Got: '%s')" % (expected, result)
            )


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestPOTemplate))
    return suite
