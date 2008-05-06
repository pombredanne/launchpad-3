# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Unit tests for XPI headers (i.e. install.rdf files)."""

__metaclass__ = type

import unittest

from canonical.launchpad.translationformat.xpi_header import XpiHeader


rdf_content = """
    <?xml version="1.0"?>
    <!-- Sample RDF file -->
    <RDF xmlns="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
        xmlns:em="http://www.mozilla.org/2004/em-rdf#">
    <Description about="urn:mozilla:install-manifest"
                 em:id="langpack-ca@firefox.mozilla.org"
                 em:name="Catalan Language Pack"
                 em:version="3.0b3"
                 em:type="8"
                 em:creator="Mozilla.org / Softcatala">
        %(contributors)s

        <em:targetApplication>
        <Description>
            <em:id>{ec8030f7-c20a-464f-9b0e-13a3a9e97384}</em:id>
            <em:minVersion>3.0b3</em:minVersion>
            <em:maxVersion>3.0b3</em:maxVersion>
        </Description>
        </em:targetApplication>
    </Description>
    </RDF>
    """.strip()


class XpiHeaderTestCase(unittest.TestCase):
    """Test `XpiHeader`."""

    def _produceHeader(self, contributors=None):
        """Generate RDF file text and parse it into an `XpiHeader`.

        :param contributors: optional list of "contributor" entries.
        :return: a fresh `XpiHeader`.
        """
        if contributors is None:
            contributors = []
        contributor_xml = [
            "<em:contributor>%s</em:contributor>" % (
                person.replace('<', "&lt;").replace('>', "&gt;"))
            for person in contributors]

        insertions = {'contributors': '\n'.join(contributor_xml)}

        content = (rdf_content % insertions).encode('utf-8')
        return XpiHeader(content)

    def test_ParseRdf(self):
        # Parse basic RDF file, verify its information.
        header = self._produceHeader()
        self.assertEqual(
            header.getRawContent(), rdf_content % {'contributors': ''})
        self.assertEqual(header.getLastTranslator(), (None, None))

    def test_SetLastTranslator(self):
        # Setting the last translator is a no-op on XPI headers.
        header = self._produceHeader()
        self.assertEqual(header.getLastTranslator(), (None, None))
        header.setLastTranslator('translator@example.com', 'Translator')
        self.assertEqual(header.getLastTranslator(), (None, None))

    def test_ParseTranslator(self):
        # The header parser extracts a contributor's name and email address.
        header = self._produceHeader(['Translator <translator@example.com>'])
        self.assertEqual(header.getLastTranslator(),
            ('Translator', 'translator@example.com'))

    def test_ParseTranslators(self):
        # If multiple contributors are listed, the "last translator" is the
        # last one in the list.
        header = self._produceHeader([
            'First Translator <translator1@example.com>',
            'Second Translator <translator2@example.com>'])
        self.assertEqual(header.getLastTranslator(),
            ('Second Translator', 'translator2@example.com'))

    def test_EmptyContributor(self):
        # Empty contributor entries are ignored.
        header = self._produceHeader([''])
        self.assertEqual(header.getLastTranslator(), (None, None))

    def test_WeirdContributor(self):
        # Contributor entries without well-formed email addresses are 
        # also ignored.
        header = self._produceHeader(['Hello Mom!'])
        self.assertEqual(header.getLastTranslator(), (None, None))

    def test_IgnoredContributorInList(self):
        # The last valid contributor is seen as the last translator.
        header = self._produceHeader([
            '',
            'First Translator <translator1@example.com>',
            'Hello Mom!',
            'Second Translator <translator2@example.com>',
            'Nothing Useful in this entry',
            ''])
        self.assertEqual(header.getLastTranslator(),
            ('Second Translator', 'translator2@example.com'))

    def test_NonAsciiContributor(self):
        # Contributor names don't have to be in ASCII.
        header = self._produceHeader([
            u"\u0e40\u0e2d\u0e4b <eai@example.com>"])
        self.assertEqual(header.getLastTranslator(),
            (u"\u0e40\u0e2d\u0e4b", 'eai@example.com'))

def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)

