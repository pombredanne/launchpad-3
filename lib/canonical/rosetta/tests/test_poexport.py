# Copyright 2004 Canonical Ltd.  All rights reserved.
#
# arch-tag: 6f729cad-ca7b-4d66-8008-617457ac9ca1

__metaclass__ = type

import unittest

from zope.component import getService, servicenames
from zope.component.tests.placelesssetup import PlacelessSetup
from canonical.arch.sqlbase import SQLBase
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
msgid "evolution addressbook %s"
msgstr ""

#: a11y/addressbook/ea-addressbook-view.c:94
#: a11y/addressbook/ea-addressbook-view.c:103
#: a11y/addressbook/ea-minicard-view.c:119
#, c-source
msgid "evolution addressbook %s"
msgstr ""
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
            poTemplate = RosettaPOTemplate.selectBy(productID = product.id, name='evolution-1.5.90')[0]
        except IndexError, e:
            raise IndexError, "Couldn't find record in database, please import populate.sql to do the tests."
        export = POExport(poTemplate)
        dump = export.export('cy')
        import difflib, sys
        if dump != expected:
            for l in difflib.unified_diff(
                dump.split('\n'), expected.split('\n'),
                'expected output', 'generated output'):
                print l
            raise AssertionError, 'output was different from the expected'

def test_suite():
    loader = unittest.TestLoader()
    return loader.loadTestsFromTestCase(POExportTestCase)

if __name__ == '__main__':
    unittest.main()
