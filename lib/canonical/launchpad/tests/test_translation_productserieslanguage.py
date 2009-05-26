# Copyright 2009 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from datetime import datetime, timedelta
import pytz
import unittest

from zope.component import getAdapter
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces import TranslationValidationStatus
from canonical.launchpad.interfaces.translationcommonformat import (
    ITranslationFileData)
from lp.testing import TestCaseWithFactory
from lp.testing.factory import LaunchpadObjectFactory
from canonical.testing import LaunchpadZopelessLayer


class TestProductSeriesLanguage(TestCaseWithFactory):
    """Test behaviour of ProductSeriesLanguage model class."""

    layer = LaunchpadZopelessLayer

    def createPOTemplateWithPOTMsgSets(self, count_of_potmsgsets):
        potemplate = self.factory.makePOTemplate(
            productseries=self.productseries)
        for sequence in range(count_of_potmsgsets):
            self.factory.makePOTMsgSet(potemplate, sequence=sequence+1)
        return potemplate

    def setUp(self):
        """Set up context to test in."""
        # Create a productseries that uses translations.
        TestCaseWithFactory.setUp(self)
        self.productseries = self.factory.makeProductSeries()
        self.productseries.product.official_rosetta = True

    def test_NoTemplatesNoLanguage(self):
        # There are no templates and no translations.
        # ProductSeriesLanguage for any language will still work,
        # but show a zero everywhere.
        self.assertEquals(self.productseries.productserieslanguages,
                          [])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
