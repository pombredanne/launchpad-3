# Copyright 2004 Canonical Ltd.  All rights reserved.

import unittest

from cStringIO import StringIO
from zope.component import getService, servicenames
from zope.component.tests.placelesssetup import PlacelessSetup
from canonical.arch.sqlbase import SQLBase
from canonical.rosetta.interfaces import ILanguages
from canonical.rosetta.sql import RosettaPerson, RosettaPOTemplate, \
    RosettaProject, RosettaProduct, RosettaLanguages
from sqlobject.dbconnection import TheURIOpener as connectionFactory
from canonical.rosetta.pofile_adapters import MessageProxy, TemplateImporter
import os

# XXX:
from canonical.rosetta.pofile_adapters import XXXperson

here = os.path.dirname(os.path.abspath(__file__))

class POImportTestCase(PlacelessSetup, unittest.TestCase):

    def setUp(self):
        # these tests are going to be slow as hell...
        os.system("make -C %s testdb > /dev/null 2>/dev/null" % os.path.dirname(here))
        super(POImportTestCase, self).setUp()
        utilityService = getService(servicenames.Utilities)
        utilityService.provideUtility(ILanguages, RosettaLanguages(), '')
        self.connection = connectionFactory.connectionForURI('postgres:///launchpad_test')
        SQLBase.initZopeless(self.connection)
        self.pot = file(os.path.join(here, 'gnome-terminal.pot'))
        self.po = file(os.path.join(here, 'gnome-terminal-cy.po'))

    def tearDown(self):
        c = self.connection.getConnection()
        self.connection.releaseConnection(c)
        c.close()
        connectionFactory.cachedURIs.clear()
        super(POImportTestCase, self).tearDown()

    def testTemplateImporter(self):
        try:
            project = RosettaProject.selectBy(name = 'gnome')[0]
        except (IndexError, KeyError):
            import sys
            t, e, tb = sys.exc_info()
            raise t, "Couldn't find record in database", tb
        try:
            product = RosettaProduct.selectBy(projectID = project.id, name = 'gnome-terminal')[0]
        except IndexError:
            product = RosettaProduct(project=project,
                                     name='gnome-terminal',
                                     displayName='Gnome Terminal',
                                     title='GNOME Terminal',
                                     shortDesc='The GNOME terminal emulator',
                                     description='The GNOME terminal emulator',
                                     owner=XXXperson)
        try:
            poTemplate = RosettaPOTemplate.selectBy(productID = product.id,
                                                    name='gnome-terminal')[0]
        except IndexError:
            # XXX: should use Product.newPOTemplate when it works
            poTemplate = RosettaPOTemplate(product=product,
                                           name='gnome-terminal',
                                           title='GNOME Terminal main template',
                                           description='GNOME Terminal main template',
                                           path=self.pot.name,
                                           isCurrent=True,
                                           dateCreated='NOW',
                                           copyright='yes',
                                           priority=1,
                                           branch=1,
                                           license=1,
                                           messageCount=0,
                                           owner=XXXperson)
        importer = TemplateImporter(poTemplate, None)
        importer.doImport(self.pot)
        return
        # TODO: add some code that actually tests the database
        # here is an attempt
        # but the transaction has to be committed (subtransaction?)
        # so that the test is relevant
        msg = poTemplate["evolution addressbook %s"]
        old_sighting = msg.getMessageIDSighting(0)
        print old_sighting, repr(old_sighting.poMessageID_.text), old_sighting.lastSeen
        importer.doImport(self.pot)
        msg = poTemplate["evolution addressbook %s"]
        print MessageProxy(msg).__unicode__(80).encode('utf-8')
        new_sighting = msg.getMessageIDSighting(0)
        print new_sighting, repr(new_sighting.poMessageID_.text), new_sighting.lastSeen

    def testFileImporter(self):
        try:
            project = RosettaProject.selectBy(name = 'gnome')[0]
        except (IndexError, KeyError):
            import sys
            t, e, tb = sys.exc_info()
            raise t, "Couldn't find record in database", tb
        try:
            product = RosettaProduct.selectBy(projectID = project.id, name = 'gnome-terminal')[0]
        except IndexError:
            product = RosettaProduct(project=project,
                                     name='gnome-terminal',
                                     displayName='Gnome Terminal',
                                     title='GNOME Terminal',
                                     shortDesc='The GNOME terminal emulator',
                                     description='The GNOME terminal emulator',
                                     owner=XXXperson)
        try:
            poTemplate = RosettaPOTemplate.selectBy(productID = product.id,
                                                    name='gnome-terminal')[0]
        except IndexError:
            # XXX: should use the TemplateImporter so that we have message sets
            poTemplate = RosettaPOTemplate(product=product,
                                           name='gnome-terminal',
                                           title='GNOME Terminal main template',
                                           description='GNOME Terminal main template',
                                           path=self.pot.name,
                                           isCurrent=True,
                                           dateCreated='NOW',
                                           copyright='yes',
                                           priority=1,
                                           branch=1,
                                           license=1,
                                           messageCount=0,
                                           owner=XXXperson)
        try:
            poFile = poTemplate.poFile('cy')
        except KeyError:
            poFile = poTemplate.newPOFile(XXXperson, 'cy')
        importer = TemplateImporter(poTemplate, None)
        importer.doImport(self.pot)


def test_suite():
    loader = unittest.TestLoader()
    return unittest.makeSuite(POImportTestCase)

if __name__ == '__main__':
    unittest.main()
