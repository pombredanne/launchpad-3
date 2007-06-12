# Copyright 2007 Canonical Ltd.  All rights reserved.
"""Gettext PO importer tests."""

__metaclass__ = type

import unittest
from zope.component import getUtility
from zope.interface.verify import verifyObject

from canonical.launchpad.components.translationformats import (
    TranslationImporter
    )
from canonical.launchpad.components.translationformats.gettext_po_importer import (
    GettextPoImporter
    )
from canonical.launchpad.interfaces import (
    IPersonSet, IProductSet, IPOTemplateSet, ITranslationImporter
    )
from canonical.lp.dbschema import TranslationFileFormat
from canonical.testing import LaunchpadZopelessLayer


class GettextPoImporterTestCase(unittest.TestCase):
    """Class test for gettext's .po file imports"""
    layer = LaunchpadZopelessLayer

    def setUp(self):
        # Add a new entry for testing purposes. It's a template one.
        productset = getUtility(IProductSet)
        evolution = productset.getByName('evolution')
        productseries = evolution.getSeries('trunk')
        potemplateset = getUtility(IPOTemplateSet)
        potemplate_subset = potemplateset.getSubset(
            productseries=productseries)
        evolution_template = potemplate_subset.getPOTemplateByName(
            'evolution-2.2')
        spanish_translation = evolution_template.getPOFileByLang('es')

        self.translation_importer = TranslationImporter()
        self.translation_importer.pofile = spanish_translation
        self.translation_importer.potemplate = evolution_template

    def testInterface(self):
        """Check whether the object follows the interface."""
        self.failUnless(
            verifyObject(ITranslationImporter, self.translation_importer),
            "TranslationImporter doesn't follow the interface")

    def testGetPersonByEmail(self):
        """When importing a POFile, it may be necessary to create new Person
        entries, to represent the last translators of that POFile. This is
        done by the getPersonByEmail() function.
        """
        personset = getUtility(IPersonSet)

        # The account we are going to use is not yet in Launchpad.
        self.failUnless(
            personset.getByEmail('danilo@canonical.com') is None,
            'There is already an account for danilo@canonical.com')

        person = self.translation_importer.getPersonByEmail(
            'danilo@canonical.com')
        self.failUnless(
            person.creation_rationale.name == 'POFILEIMPORT',
            'danilo@canonical.com was not created due to a POFile import')
        self.failUnless(
            person.creation_comment == (
                'when importing the %s translation of %s' % (
                    self.translation_importer.pofile.language.displayname,
                    self.translation_importer.potemplate.displayname)),
            "Creation comment is not matching POFile that is being imported." )

    def testGetImporterByFileFormat(self):
        """PO file format is handled by GettextPoImporter."""
        format_importer = self.translation_importer.getImporterByFileFormat(
            TranslationFileFormat.PO)

        self.failUnless(isinstance(GettextPoImporter, format_importer))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(GettextPoImporterTestCase))
    return suite

