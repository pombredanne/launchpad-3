# Copyright 2004 Canonical Ltd.  All rights reserved.

import unittest

from cStringIO import StringIO
from zope.component import getService, servicenames
from zope.component.tests.placelesssetup import PlacelessSetup
from canonical.rosetta.interfaces import ILanguages
from canonical.rosetta.sql import RosettaPerson, RosettaPOTemplate, \
     RosettaProduct, RosettaLanguages, RosettaPOMessageSet, \
     RosettaPOMessageIDSighting
from canonical.rosetta.pofile_adapters import MessageProxy, \
     TemplateImporter, POFileImporter
from canonical.database.doap import Project
import os
import canonical.lp

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
        canonical.lp.initZopeless()
        self.pot = file(os.path.join(here, 'gnome-terminal.pot'))
        self.po = file(os.path.join(here, 'gnome-terminal-cy.po'))

    def testTemplateImporter(self):
        try:
            project = Project.selectBy(name = 'gnome')[0]
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
        self.pot.seek(0)
        importer.doImport(self.pot)
        get_transaction().commit()
        RosettaPOMessageSet._connection.cache.clear()
        sets = RosettaPOMessageSet.select('potemplate=%d AND pofile IS NULL' % poTemplate.id)
        assert sets.count() == 513, '%d message sets instead of 513' % sets.count()
        for msgset in list(sets):
            # All messages should have the sequence > 0
            # XXX: We are assuming you are cleaning up the DB between tests.
            assert msgset.sequence > 0
            sighting = RosettaPOMessageIDSighting.selectBy(
                        poMessageSetID=msgset.id,
                        poMessageID_ID=msgset.primeMessageID_.id)[0]
            assert sighting.inLastRevision
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
            project = Project.selectBy(name = 'gnome')[0]
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
        self.po.seek(0)
        importer.doImport(self.po)
        # check that there aren't duplicates in the db
        RosettaPOMessageSet._connection.cache.clear()
        for message in importer.parser.messages:
            msgid = message._msgset.primeMessageID_
            results = RosettaPOMessageSet.select('''
                poTemplate = %d AND
                poFile = %d AND
                primeMsgID = %d
                ''' % (poTemplate.id, poFile.id, msgid.id))
            assert results.count() == 1, '%d message sets' % results.count()
            assert results[0].sequence > 0


def test_suite():
    loader = unittest.TestLoader()
    return loader.loadTestsFromTestCase(POImportTestCase)

if __name__ == '__main__':
    unittest.main()
