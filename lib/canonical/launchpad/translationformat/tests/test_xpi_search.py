# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Functional tests for searching through XPI POTemplates"""
__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.launchpad.interfaces import (
    IPersonSet, IProductSet, IPOTemplateSet, RosettaImportStatus)
from canonical.testing import LaunchpadZopelessLayer
from canonical.launchpad.translationformat.tests.helpers import (
    import_pofile_or_potemplate,
    )
from canonical.launchpad.translationformat.tests.xpi_helpers import (
    get_en_US_xpi_file_to_import,
    )


class XpiSearchTestCase(unittest.TestCase):
    """XPI file import into Launchpad."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        # Get the importer.
        self.importer = getUtility(IPersonSet).getByName('sabdfl')

        # Get the Firefox template.
        firefox_product = getUtility(IProductSet).getByName('firefox')
        firefox_productseries = firefox_product.getSeries('trunk')
        firefox_potemplate_subset = getUtility(IPOTemplateSet).getSubset(
            productseries=firefox_productseries)
        self.firefox_template = firefox_potemplate_subset.new(
            name='firefox',
            translation_domain='firefox',
            path='en-US.xpi',
            owner=self.importer)
        self.spanish_firefox = self.firefox_template.newPOFile('es')
        self.spanish_firefox.path = 'translations/es.xpi'

    def setUpTranslationImportQueueForTemplate(self, subdir):
        """Return an ITranslationImportQueueEntry for testing purposes.

        :param subdir: subdirectory in firefox-data to get XPI data from.
        """
        # Get the file to import.
        en_US_xpi = get_en_US_xpi_file_to_import(subdir)
        return import_pofile_or_potemplate(
            file_contents=en_US_xpi.read(),
            person=self.importer,
            potemplate=self.firefox_template)

    def test_TemplateSearching(self):
        """Test that searching works correctly for template strings."""
        entry = self.setUpTranslationImportQueueForTemplate('en-US')

        # The status is now IMPORTED:
        self.assertEquals(entry.status, RosettaImportStatus.IMPORTED)

        potmsgsets = list(self.spanish_firefox.findPOTMsgSetsContaining(
            text='zilla'))

        message_list = []
        for message in potmsgsets:
            message_list.append(message.singular_text)

        self.assertEquals(len(potmsgsets), 3)

        self.assertEquals([u'SomeZilla', u'FooZilla!',
                           u'FooZilla Zilla Thingy'],
                          message_list)


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)
