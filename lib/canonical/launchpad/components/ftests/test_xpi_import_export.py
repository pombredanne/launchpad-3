# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Functional tests for XPI file format"""
__metaclass__ = type

import os.path
import tempfile
import transaction
import unittest
import zipfile

from zope.component import getUtility
import canonical.launchpad
from canonical.launchpad.interfaces import (
    IPersonSet, IProductSet, IPOTemplateNameSet, IPOTemplateSet,
    ITranslationImportQueue)
from canonical.launchpad.ftests import login
from canonical.launchpad.ftests.harness import LaunchpadZopelessTestCase
from canonical.lp.dbschema import RosettaImportStatus

def get_en_US_xpi_file_to_import():
    """Return an en-US.xpi file object ready to be imported."""
    # en-US.xpi file is a ZIP file which contains embedded JAR file (which is
    # also a ZIP file) and a couple of other files.  Embedded JAR file is
    # named 'en-US.jar' and contains translatable resources.

    # Get the root path where the data to generate .xpi file is stored.
    test_root = os.path.join(
        os.path.dirname(canonical.launchpad.__file__),
        'components/ftests/firefox-data/')

    # First create a en-US.jar file to be included in XPI file.
    jarfile = tempfile.TemporaryFile()
    jar = zipfile.ZipFile(jarfile, 'w')
    jarlist = ['copyover1.foo', 'test1.dtd', 'test1.properties',
               'subdir/test2.dtd', 'subdir/test2.properties',
               'subdir/copyover2.foo']
    for subfile in jarlist:
        f = open(test_root + 'en-US/en-US-jar/' + subfile, 'r')
        jar.writestr(subfile, f.read())
    jar.close()
    jarfile.seek(0)

    # Add remaining bits and en-US.jar to en-US.xpi.

    xpifile = tempfile.TemporaryFile()
    xpi = zipfile.ZipFile(xpifile, 'w')
    xpilist = [ 'install.rdf', 'copyover3.png' ]
    for subfile in xpilist:
        f = open(test_root + 'en-US/' + subfile, 'r')
        xpi.writestr(subfile, f.read())
    xpi.writestr('chrome/en-US.jar', jarfile.read())
    xpi.close()
    xpifile.seek(0)

    return xpifile

class XpiTestCase(LaunchpadZopelessTestCase):
    """XPI file import/export into Rosetta."""

    def setUp(self):
        LaunchpadZopelessTestCase.setUp(self)

        # Login as a Rosetta expert to be able to do changes to the import
        # queue.
        login('carlos@canonical.com')

        # Get the importer.
        person_set = getUtility(IPersonSet)
        self.importer = person_set.getByName('sabdfl')

        # Get the Firefox template.
        product_set = getUtility(IProductSet)
        firefox_product = product_set.getByName('firefox')
        firefox_productseries = firefox_product.getSeries('trunk')
        firefox_potemplatename = getUtility(IPOTemplateNameSet)['firefox']
        firefox_potemplate_subset = getUtility(IPOTemplateSet).getSubset(
            productseries=firefox_productseries)
        self.firefox_template = firefox_potemplate_subset.new(
            potemplatename=firefox_potemplatename,
            path='en-US.xpi',
            owner=self.importer)
        self.firefox_template = (
            firefox_potemplate_subset.getPOTemplateByName('firefox'))

    def testImport(self):
        """Test XPI file import."""
        # Get the file to import.
        en_US_xpi =  get_en_US_xpi_file_to_import()

        # Attach it to the import queue.
        translation_import_queue = getUtility(ITranslationImportQueue)
        published = True
        entry = translation_import_queue.addOrUpdateEntry(
            self.firefox_template.path, en_US_xpi.read(), published,
            self.importer, productseries=self.firefox_template.productseries,
            potemplate=self.firefox_template)

        # The file data is stored in the Librarian, so we have to commit the
        # transaction to make sure it's stored properly.
        transaction.commit()

        # We must approve the entry to be able to import it.
        entry.status = RosettaImportStatus.APPROVED

        # Now, we tell the PO template to import from the file data it has.
        self.firefox_template.importFromQueue()

        # The status is now IMPORTED:
        self.failUnlessEqual(entry.status, RosettaImportStatus.IMPORTED)

        # Once we've done this, the correct message IDs should show up in the
        # template.
        potmsgsets = list(self.firefox_template.getPOTMsgSets())
        self.failUnlessEqual(
            [potmsgset.singular_text for potmsgset in potmsgsets],
            [u'FooZilla!', u'Do you want to play with fire?',
             u'Play with ice?', u'FooZilla Zilla Thingy', u'FooZillingy',
             u'No Comment', u'\u0414\u0430\u043d=Day', u'MENU',
             u'foozilla.menu.accesskey', u'foozilla.menu.commandkey',
             u'SomeZilla'])

        # File references are also stored
        self.failUnlessEqual(
            potmsgsets[2].filereferences, u'test1.dtd(foozilla.play.ice)')


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(XpiTestCase))
    return suite
