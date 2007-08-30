# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Translation Exporter tests."""

__metaclass__ = type

import unittest
from zope.interface.verify import verifyObject

from canonical.launchpad.translationformat import (
    TranslationExporter, ExportedTranslationFile)
from canonical.launchpad.interfaces import (
    IExportedTranslationFile, ITranslationExporter)
from canonical.lp.dbschema import TranslationFileFormat
from canonical.testing import LaunchpadZopelessLayer


class TranslationExporterTestCase(unittest.TestCase):
    """Class test for translation importer component"""
    layer = LaunchpadZopelessLayer

    def setUp(self):
        self.translation_exporter = TranslationExporter()

    def testInterface(self):
        """Check whether the object follows the interface."""
        self.failUnless(
            verifyObject(ITranslationExporter, self.translation_exporter),
            "TranslationExporter doesn't follow the interface")
        self.failUnless(
            verifyObject(IExportedTranslationFile, ExportedTranslationFile()),
            "ExportedTranslationFile doesn't follow the interface")

    def testGetTranslationFormatExporterByFileFormat(self):
        """Check whether we get the right exporter from the file format."""
        translation_exporter = self.translation_exporter
        po_format_exporter = (
            translation_exporter.getTranslationFormatExporterByFileFormat(
                TranslationFileFormat.PO))

        self.failUnless(po_format_exporter is not None, (
            'There is no exporter for PO file format'))

        mo_format_exporter = (
            translation_exporter.getTranslationFormatExporterByFileFormat(
                TranslationFileFormat.MO))

        self.failUnless(mo_format_exporter is not None, (
            'There is no importer for MO file format'))

    def testgetTranslationFormatExportersForFileFormat(self):
        """We get the right list of exporters to handle the file format."""
        translation_exporter = self.translation_exporter
        exporter_formats = []
        exporters_available = (
            translation_exporter.getTranslationFormatExportersForFileFormat(
                TranslationFileFormat.PO))
        for exporter in exporters_available:
            exporter_formats.append(exporter.format)

        self.failUnless(exporter_formats == [
            TranslationFileFormat.PO, TranslationFileFormat.MO], (
            'PO source file should be exported as PO and MO formats'))

        exporter_formats = []
        exporters_available = (
            translation_exporter.getTranslationFormatExportersForFileFormat(
                TranslationFileFormat.XPI))
        for exporter in exporters_available:
            exporter_formats.append(exporter.format)

        self.failUnless(exporter_formats == [TranslationFileFormat.PO], (
            'XPI source file should be exported as PO format'))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TranslationExporterTestCase))
    return suite

