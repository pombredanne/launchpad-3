# Copyright 2004 Canonical Ltd.  All rights reserved.
# arch-tag: 752bd71e-584e-416e-abff-a4eb6c82399c

import sys

from cStringIO import StringIO
from zope.component import getService, servicenames
from zope.component.tests.placelesssetup import PlacelessSetup
from canonical.arch.sqlbase import SQLBase
from canonical.rosetta.interfaces import ILanguages
from canonical.rosetta.sql import RosettaPerson, RosettaPOTemplate, \
    RosettaProject, RosettaProduct, RosettaLanguages, RosettaLanguage, \
    RosettaPOFile
from sqlobject import connectionForURI
from canonical.rosetta.pofile_adapters import MessageProxy, \
    TemplateImporter, POFileImporter

class PODBBridge(PlacelessSetup):

    def __init__(self):
        SQLBase.initZopeless(connectionForURI('postgres:///launchpad_test'))

    def imports(self, file, projectName, productName, poTemplateName,
        languageCode=None):
        try:
            project = RosettaProject.selectBy(name = projectName)[0]
            product = RosettaProduct.selectBy(projectID = project.id,
                                              name=productName)[0]
            poTemplate = RosettaPOTemplate.selectBy(productID = product.id,
                                                    name=poTemplateName)[0]
        except (IndexError, KeyError):
            import sys
            t, e, tb = sys.exc_info()
            raise t, "Couldn't find record in database", tb
        if languageCode==None:
            # We are importing a POTemplate
            importer = TemplateImporter(poTemplate, None)
        else:
            # We are importing a POFile
            language = RosettaLanguage.selectBy(code = languageCode)[0]
            poFile = RosettaPOFile.selectBy(poTemplateID = poTemplate.id,
            languageID = language.id)[0]
            importer = POFileImporter(poFile, None)
        importer.doImport(file)

if __name__ == '__main__':
    if len(sys.argv) < 5:
        print "Usage: "
        print "\t" + sys.argv[0] + " pot_file project_name product_name pot_name"
        print "\t" + sys.argv[0] + " po_file project_name product_name pot_name language_name"
    else:
        bridge = PODBBridge()
        in_f = file(sys.argv[1], 'rU')
        if len(sys.argv) == 6:
            print "Importing .po file..."
            bridge.imports(in_f, sys.argv[2], sys.argv[3], sys.argv[4],
            sys.argv[5])
        else:
            print "Importing .pot file..."
            bridge.imports(in_f, sys.argv[2], sys.argv[3], sys.argv[4])

