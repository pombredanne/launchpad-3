# Copyright 2004 Canonical Ltd.  All rights reserved.

import unittest

from cStringIO import StringIO
from zope.component import getService, servicenames
from zope.component.tests.placelesssetup import PlacelessSetup
from canonical.arch.sqlbase import SQLBase
from canonical.rosetta.interfaces import ILanguages
from canonical.rosetta.sql import RosettaPerson, RosettaPOTemplate, \
    RosettaProject, RosettaProduct, RosettaLanguages
from sqlobject import connectionForURI
from canonical.rosetta.pofile_adapters import MessageProxy, TemplateImporter

sample_data = '''# SOME DESCRIPTIVE TITLE.
# Copyright (C) YEAR THE PACKAGE'S COPYRIGHT HOLDER
# This file is distributed under the same license as the PACKAGE package.
msgid ""
msgstr ""
"Project-Id-Version: PACKAGE VERSION\\n"
"Report-Msgid-Bugs-To: \\n"
"POT-Creation-Date: 2004-07-18 23:00+0200\\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\\n"
"Language-Team: LANGUAGE <LL@li.org>\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"

#: some/file.c:498
#, fuzzy, c-string
msgid "I am the text of POTSighting 1"
msgid_plural "And I'm a plural form 1"
msgstr[0] "I am a translation text in Welsh"
msgstr[1] "I am a translation text for a plural form in Welsh"

#: some/file.c:498
#, fuzzy, c-string
msgid "I am the text of POTSighting 2"
msgid_plural "And I'm a plural form 2"
msgstr[0] "I am a translation text in Welsh"
msgstr[1] "I am a translation text for a plural form in Welsh"

#: some/file.c:498
#, fuzzy, c-string
msgid "I am the text of POTSighting 3"
msgid_plural "And I'm a plural form 3"
msgstr[0] "I am a translation text in Welsh"
msgstr[1] "I am a translation text for a plural form in Welsh"

#: some/file.c:498
#, fuzzy, c-string
msgid "I am the text of POTSighting 4"
msgid_plural "And I'm a plural form 4"
msgstr[0] "I am a translation text in Welsh"
msgstr[1] "I am a translation text for a plural form in Welsh"

#: some/file.c:498
#, fuzzy, c-string
msgid "I am the text of POTSighting 5"
msgid_plural "And I'm a plural form 5"
msgstr[0] "I am a translation text in Welsh"
msgstr[1] "I am a translation text for a plural form in Welsh"
''' #'

po = StringIO(sample_data)

sample_data = '''# traducci\xc3\xb3n de es.po al Spanish
# translation of es.po to Spanish
# translation of evolution.HEAD to Spanish
# Copyright \xc2\xa9 2000-2002 Free Software Foundation, Inc.
# This file is distributed under the same license as the evolution package.
# Carlos Perell\xc3\xb3 Mar\xc3\xadn <carlos@gnome-db.org>, 2000-2001.
# H\xc3\xa9ctor Garc\xc3\xada \xc3\x81lvarez <hector@scouts-es.org>, 2000-2002.
# Ismael Olea <Ismael@olea.org>, 2001, (revisiones) 2003.
# Eneko Lacunza <enlar@iname.com>, 2001-2002.
# H\xc3\xa9ctor Garc\xc3\xada \xc3\x81lvarez <hector@scouts-es.org>, 2002.
# Pablo Gonzalo del Campo <pablodc@bigfoot.com>,2003 (revisi\xc3\xb3n).
# Francisco Javier F. Serrador <serrador@cvs.gnome.org>, 2003, 2004.
#
#
msgid ""
msgstr ""
"Project-Id-Version: es\\n"
"POT-Creation-Date: 2004-07-02 14:48-0400\\n"
"PO-Revision-Date: 2004-07-07 20:52+0200\\n"
"Last-Translator: Francisco Javier F. Serrador <serrador@cvs.gnome.org>\\n"
"Language-Team: Spanish <traductores@es.gnome.org>\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"
"Report-Msgid-Bugs-To: serrador@hispalinux.es\\n"
"X-Generator: KBabel 1.3.1\\n"
"Plural-Forms: nplurals=2; plural=(n != 1);\\n"

#: a11y/addressbook/ea-addressbook-view.c:94
#: a11y/addressbook/ea-addressbook-view.c:103
#: a11y/addressbook/ea-minicard-view.c:119
#, c-source
msgid "evolution addressbook %s"
msgstr ""

#: a11y/addressbook/ea-addressbook-view.c:94
#: a11y/addressbook/ea-addressbook-view.c:103
#: a11y/addressbook/ea-minicard-view.c:119
#, c-source
msgid "evolution addressbook entry %s"
msgstr ""

#: a11y/addressbook/ea-addressbook-view.c:94
#: a11y/addressbook/ea-addressbook-view.c:103
#: a11y/addressbook/ea-minicard-view.c:119
#, c-source
msgid "evolution addressbook number %s"
msgstr ""
'''

pot = StringIO(sample_data)

del sample_data

class POImportTestCase(PlacelessSetup, unittest.TestCase):

    def setUp(self):
        super(POImportTestCase, self).setUp()
        pot.seek(0)
        utilityService = getService(servicenames.Utilities)
        utilityService.provideUtility(ILanguages, RosettaLanguages(), '')
        SQLBase.initZopeless(connectionForURI('postgres:///launchpad_test'))

    def testTemplateImporter(self):
        try:
            project = RosettaProject.selectBy(name = 'gnome')[0]
            product = RosettaProduct.selectBy(projectID = project.id, name = 'evolution')[0]
            poTemplate = RosettaPOTemplate.selectBy(productID = product.id,
                                                    name='evolution-1.5.90')[0]
        except (IndexError, KeyError):
            import sys
            t, e, tb = sys.exc_info()
            raise t, "Couldn't find record in database", tb
        importer = TemplateImporter(poTemplate, None)
        importer.doImport(pot)
        return
        # TODO: add some code that actually tests the database
        # here is an attempt
        # but the transaction has to be committed (subtransaction?)
        # so that the test is relevant
        msg = poTemplate["evolution addressbook %s"]
        old_sighting = msg.getMessageIDSighting(0)
        print old_sighting, repr(old_sighting.poMessageID_.text), old_sighting.lastSeen
        importer.doImport(pot)
        msg = poTemplate["evolution addressbook %s"]
        print MessageProxy(msg).__unicode__(80).encode('utf-8')
        new_sighting = msg.getMessageIDSighting(0)
        print new_sighting, repr(new_sighting.poMessageID_.text), new_sighting.lastSeen


def test_suite():
    loader = unittest.TestLoader()
    return loader.loadTestsFromTestCase(POImportTestCase)

if __name__ == '__main__':
    unittest.main()
