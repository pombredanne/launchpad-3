# Copyright 2004 Canonical Ltd.  All rights reserved.
#
# arch-tag: 6f729cad-ca7b-4d66-8008-617457ac9ca1

__metaclass__ = type

import unittest

from zope.component import getService, servicenames
from zope.component.tests.placelesssetup import PlacelessSetup
from canonical.database.sqlbase import SQLBase
from canonical.rosetta.interfaces import ILanguages
from canonical.rosetta.sql import RosettaPerson, RosettaPOTemplate, \
    RosettaProject, RosettaProduct, RosettaLanguages
from canonical.rosetta.poexport import POExport
from sqlobject import connectionForURI


expected = '''# traducci\xc3\xb3n de es.po al Spanish
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
"POT-Creation-Date: 2004-08-17 11:10+0200\\n"
"PO-Revision-Date: 2004-08-15 19:32+0200\\n"
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
msgid "evolution addressbook"
msgstr "libreta de direcciones de Evolution"

#: a11y/addressbook/ea-minicard-view.c:101
msgid "current addressbook folder"
msgstr "carpeta de libretas de direcciones actual"

#: a11y/addressbook/ea-minicard-view.c:102
#, fuzzy
msgid "have "
msgstr "tiene"

#: a11y/addressbook/ea-minicard-view.c:102
msgid "has "
msgstr ""

#: a11y/addressbook/ea-minicard-view.c:104
msgid " cards"
msgstr ""

#: a11y/addressbook/ea-minicard-view.c:104
msgid " card"
msgstr ""

#: a11y/addressbook/ea-minicard-view.c:105
msgid "contact's header: "
msgstr ""

#: a11y/addressbook/ea-minicard.c:166
msgid "evolution minicard"
msgstr ""

#. addressbook:ldap-init primary
#: addressbook/addressbook-errors.xml.h:2
msgid "This addressbook could not be opened."
msgstr ""

#. addressbook:ldap-init secondary
#: addressbook/addressbook-errors.xml.h:4
msgid ""
"This addressbook server might unreachable or the server name may be misspelled "
"or your network connection could be down."
msgstr ""

#. addressbook:ldap-auth primary
#: addressbook/addressbook-errors.xml.h:6
msgid "Failed to authenticate with LDAP server."
msgstr ""

#. addressbook:ldap-auth secondary
#: addressbook/addressbook-errors.xml.h:8
msgid ""
"Check to make sure your password is spelled correctly and that you are using a "
"supported login method. Remember that many passwords are case sensitive; your "
"caps lock might be on."
msgstr ""

#: addressbook/gui/component/addressbook-migrate.c:124
#: calendar/gui/migration.c:188 mail/em-migrate.c:1201
#, c-format
msgid "Migrating `%s':"
msgstr ""

#: addressbook/gui/component/addressbook-migrate.c:1123
msgid ""
"The location and hierarchy of the Evolution contact folders has changed since "
"Evolution 1.x.\\n"
"\\n"
"Please be patient while Evolution migrates your folders..."
msgstr ""

#: addressbook/gui/widgets/e-addressbook-model.c:151
#, c-format
msgid "%d contact"
msgid_plural "%d contacts"
msgstr[0] "%d contacto"
msgstr[1] "%d contactos"

#~ msgid "_Add Group"
#~ msgstr "_A\xc3\xb1adir grupo"
'''

class POExportTestCase(PlacelessSetup, unittest.TestCase):

    def setUp(self):
        super(POExportTestCase, self).setUp()
        utilityService = getService(servicenames.Utilities)
        utilityService.provideUtility(ILanguages, RosettaLanguages(), '')
        SQLBase.initZopeless(connectionForURI('postgres:///launchpad_test'))

    def testPoExportAdapter(self):
        try:
            project = RosettaProject.selectBy(name = 'gnome')[0]
            product = RosettaProduct.selectBy(projectID = project.id, name = 'evolution')[0]
            poTemplate = RosettaPOTemplate.selectBy(productID = product.id, name='evolution-2.0')[0]
        except IndexError, e:
            raise IndexError, "Couldn't find record in database, please import sampledata.sql to do the tests."
        export = POExport(poTemplate)
        dump = export.export('es')
        #print dump
        import difflib, sys
        if dump != expected:
            for l in difflib.unified_diff(
                expected.split('\n'), dump.split('\n'),
                'expected output', 'generated output'):
                print l
            raise AssertionError, 'output was different from the expected'

def test_suite():
    loader = unittest.TestLoader()
    return loader.loadTestsFromTestCase(POExportTestCase)

if __name__ == '__main__':
    unittest.main()
