# Copyright 2004 Canonical Ltd.  All rights reserved.

import unittest

from cStringIO import StringIO
from zope.component import getService, servicenames
from zope.component.tests.placelesssetup import PlacelessSetup
from canonical.database.sqlbase import SQLBase
from canonical.rosetta.interfaces import ILanguages
from canonical.rosetta.sql import RosettaPerson, RosettaPOTemplate, \
     xxxRosettaProject, RosettaProduct, RosettaLanguages, RosettaPOMessageSet
from sqlobject import connectionForURI
from canonical.rosetta.pofile_adapters import MessageProxy, \
     TemplateImporter, POFileImporter
import os

# XXX: not using Person at all, probably should
class FakePerson(object):
    id = 1
XXXperson = FakePerson()

here = os.path.dirname(os.path.abspath(__file__))

class POImportTestCase(PlacelessSetup, unittest.TestCase):

    def setUp(self):
        super(POImportTestCase, self).setUp()
        utilityService = getService(servicenames.Utilities)
        utilityService.provideUtility(ILanguages, RosettaLanguages(), '')
        SQLBase.initZopeless(connectionForURI('postgres:///launchpad_test'))
        self.pot = file(os.path.join(here, 'gnome-terminal.pot'))
        self.po = file(os.path.join(here, 'gnome-terminal-cy.po'))

    def testTemplateImporter(self):
        try:
            project = xxxRosettaProject.selectBy(name = 'gnome')[0]
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
        importer = TemplateImporter(poTemplate, XXXperson)
        importer.doImport(self.pot)
        get_transaction().commit()
        # try a second time to see if it breaks
        importer.doImport(self.pot)
        msgid = poTemplate.messageSet(slice(1))[0].primeMessageID_
        results = RosettaPOMessageSet.selectBy(
            poTemplateID=poTemplate.id,
            poFileID=None,
            primeMessageID_ID=msgid.id)
        assert results.count() == 1, results.count()
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
            project = xxxRosettaProject.selectBy(name = 'gnome')[0]
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
        importer = POFileImporter(poFile, XXXperson)
        importer.doImport(self.po)
        get_transaction().commit()
        # try a second time to see if it breaks
        importer.doImport(self.po)


def test_suite():
    loader = unittest.TestLoader()
    return loader.loadTestsFromTestCase(POImportTestCase)

if __name__ == '__main__':
    unittest.main()
