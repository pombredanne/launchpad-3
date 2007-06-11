# Copyright 2007 Canonical Ltd.  All rights reserved.
"""Gettext PO importer tests."""

__metaclass__ = type

import unittest
import transaction
from zope.component import getUtility

from canonical.launchpad.components.translationformats.gettext_po_importer import (
    GettextPoImporter
    )
from canonical.launchpad.interfaces import (
    ITranslationImportQueue, IPersonSet, IProductSet
    )
from canonical.launchpad.ftests import login
from canonical.lp.dbschema import TranslationFileFormat
from canonical.testing import LaunchpadFunctionalLayer, LaunchpadZopelessLayer

test_template = r'''
msgid ""
msgstr ""
"PO-Revision-Date: 2005-05-03 20:41+0100\n"
"Content-Type: text/plain; charset=UTF-8\n"

msgid "foo"
msgstr "blah"
'''


class GettextPoImporterTestCase(unittest.TestCase):
    """Class test for gettext's .po file imports"""
    layer = LaunchpadZopelessLayer

    def setUp(self):
        # Add a new entry for testing purposes.
        translation_import_queue = getUtility(ITranslationImportQueue)
        path = 'po/testing.pot'
        is_published = True
        personset = getUtility(IPersonSet)
        importer = personset.getByName('carlos')
        productset = getUtility(IProductSet)
        firefox = productset.getByName('firefox')
        productseries = firefox.getSeries('trunk')
        self.entry = translation_import_queue.addOrUpdateEntry(
            path, test_template, is_published, importer,
            productseries=productseries)
        transaction.commit()

    def testFormat(self):
        importer = GettextPoImporter(self.entry)

        self.failUnless(importer.format == TranslationFileFormat.PO,
            'GettextPoImporter format is not PO but %s' % importer.format.name
            )


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(GettextPoImporterTestCase))
    return suite

