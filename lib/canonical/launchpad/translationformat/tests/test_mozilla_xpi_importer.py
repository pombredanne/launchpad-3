# Copyright 2007 Canonical Ltd.  All rights reserved.
"""Mozilla XPI importer tests."""

__metaclass__ = type

import unittest
from zope.interface.verify import verifyObject

from canonical.launchpad.translationformat.mozilla_xpi_importer import (
    MozillaXpiImporter)
from canonical.launchpad.interfaces import ITranslationFormatImporter
from canonical.lp.dbschema import TranslationFileFormat
from canonical.testing import LaunchpadZopelessLayer


class MozillaXpiImporterTestCase(unittest.TestCase):
    """Class test for mozilla's .xpi file imports"""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        self.importer = MozillaXpiImporter()

    def testInterface(self):
        """Check whether the object follows the interface."""
        self.failUnless(
            verifyObject(ITranslationFormatImporter, self.importer))

    def testFormat(self):
        """Check that MozillaXpiImporter handles the XPI file format."""
        self.failUnless(
            self.importer.format == TranslationFileFormat.XPI,
            'MozillaXpiImporter format expected XPI but got %s' % (
                self.importer.format.name))

    def testHasAlternativeMsgID(self):
        """Check that MozillaXpiImporter has an alternative msgid."""
        self.failUnless(
            self.importer.has_alternative_msgid,
            "MozillaXpiImporter format says it's not using alternative msgid"
            " when it really does!")


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)
