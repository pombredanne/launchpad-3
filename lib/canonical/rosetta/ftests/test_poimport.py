# Copyright 2004 Canonical Ltd.  All rights reserved.

import unittest
import os
from cStringIO import StringIO

from zope.component import getService, servicenames
from zope.component.tests.placelesssetup import PlacelessSetup

from canonical.launchpad.interfaces import ILanguageSet
from canonical.launchpad.database import Person, POTemplate, \
     Product, LanguageSet, POMsgSet, POTMsgSet, POMsgIDSighting
from canonical.rosetta.pofile_adapters import MessageProxy, \
     TemplateImporter, POFileImporter
from canonical.launchpad.database import Project
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
        utilityService.provideUtility(ILanguageSet, LanguageSet(), '')
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
            product = Product.selectBy(projectID = project.id, name = 'gnome-terminal')[0]
        except IndexError:
            product = Product(project=project,
                              name='gnome-terminal',
                              displayname='Gnome Terminal',
                              title='GNOME Terminal',
                              shortDesc='The GNOME terminal emulator',
                              description='The GNOME terminal emulator',
                              owner=XXXperson)
        try:
            poTemplate = POTemplate.selectBy(productID = product.id,
                                                    name='gnome-terminal')[0]
        except IndexError:
            # XXX: should use Product.newPOTemplate when it works
            poTemplate = POTemplate(product=product,
                                    name='gnome-terminal',
                                    title='GNOME Terminal main template',
                                    description='GNOME Terminal main template',
                                    path=self.pot.name,
                                    iscurrent=True,
                                    datecreated='NOW',
                                    copyright='yes',
                                    priority=1,
                                    branchID=1,
                                    license=1,
                                    messagecount=0,
                                    ownerID=XXXperson.id)
        importer = TemplateImporter(poTemplate, XXXperson)
        importer.doImport(self.pot)
        get_transaction().commit()
        # try a second time to see if it breaks
        self.pot.seek(0)
        importer.doImport(self.pot)
        get_transaction().commit()
        POTMsgSet._connection.cache.clear()
        sets = POTMsgSet.select('potemplate=%d and sequence > 0' % poTemplate.id)
        assert sets.count() == 513, '%d message sets instead of 513' % sets.count()
        for msgset in list(sets):
            # All messages should have the sequence > 0
            # XXX: We are assuming you are cleaning up the DB between tests.
            assert msgset.sequence > 0
            sighting = POMsgIDSighting.selectBy(
                        potmsgsetID=msgset.id,
                        pomsgid_ID=msgset.primemsgid_.id)[0]
            assert sighting.inlastrevision
        return
        # TODO: add some code that actually tests the database
        # here is an attempt
        # but the transaction has to be committed (subtransaction?)
        # so that the test is relevant
        # XXX: Carlos Perello Marin 19/10/04: Review after the database
        # changes.
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
            product = Product.selectBy(projectID = project.id, name = 'gnome-terminal')[0]
        except IndexError:
            product = Product(project=project,
                              name='gnome-terminal',
                              displayname='Gnome Terminal',
                              title='GNOME Terminal',
                              shortDesc='The GNOME terminal emulator',
                              description='The GNOME terminal emulator',
                              ownerID=XXXperson.id)
        try:
            poTemplate = POTemplate.selectBy(productID = product.id,
                                                    name='gnome-terminal')[0]
        except IndexError:
            # XXX: should use the TemplateImporter so that we have message sets
            poTemplate = POTemplate(product=product,
                                    name='gnome-terminal',
                                    title='GNOME Terminal main template',
                                    description='GNOME Terminal main template',
                                    path=self.pot.name,
                                    iscurrent=True,
                                    datecreated='NOW',
                                    copyright='yes',
                                    priority=1,
                                    branchID=1,
                                    license=1,
                                    messagecount=0,
                                    ownerID=XXXperson.id)
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
        POMsgSet._connection.cache.clear()
        for message in importer.parser.messages:
            msgid = message._potmsgset.primemsgid_
            results = POMsgSet.select('''
                POMsgSet.poFile = %d AND
                POMsgSet.potmsgset = POTMsgSet.id AND
                POTMsgSet.primemsgid = %d
                ''' % (poFile.id, msgid.id),
                clauseTables=('POTMsgSet', 'POMsgSet'))
            assert results.count() == 1, '%d message sets' % results.count()
            assert results[0].sequence > 0


def test_suite():
    loader = unittest.TestLoader()
    return loader.loadTestsFromTestCase(POImportTestCase)

if __name__ == '__main__':
    unittest.main()
