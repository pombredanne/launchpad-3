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

    def imports(self, person, file, projectName, productName, poTemplateName,
        languageCode=None):
        try:
            project = RosettaProject.selectBy(name = projectName)[0]
            product = RosettaProduct.selectBy(projectID = project.id,
                                              name=productName)[0]
        except (IndexError, KeyError):
            import sys
            t, e, tb = sys.exc_info()
            raise t, "Couldn't find record in database", tb
        try:
            poTemplate = RosettaPOTemplate.selectBy(productID = product.id,
                                                    name=poTemplateName)[0]
        except IndexError:
            # XXX: should use Product.newPOTemplate when it works
            if languageCode is not None:
                import sys
                t, e, tb = sys.exc_info()
                raise t, "Couldn't find record in database", tb
            poTemplate = RosettaPOTemplate(product=product,
                                           name=poTemplateName,
                                           title=poTemplateName, # will have to be edited
                                           description=poTemplateName, # will have to be edited
                                           path=file.name,
                                           isCurrent=True,
                                           dateCreated='NOW',
                                           copyright='XXX: FIXME',
                                           priority=2, # XXX: FIXME
                                           branch=1, # XXX: FIXME
                                           license=1, # XXX: FIXME
                                           messageCount=0,
                                           owner=person)
        if languageCode is None:
            # We are importing a POTemplate
            importer = TemplateImporter(poTemplate, None)
        else:
            # We are importing a POFile
            try:
                poFile = poTemplate.poFile(languageCode)
            except KeyError:
                poFile = poTemplate.newPOFile(person, languageCode)
            importer = POFileImporter(poFile, None)
        importer.doImport(file)

if __name__ == '__main__':
    if len(sys.argv) < 6:
        print "Usage: "
        print "\t" + sys.argv[0] + " user_id pot_file project_name product_name pot_name"
        print "\t" + sys.argv[0] + " user_id po_file project_name product_name pot_name language_name"
    else:
        bridge = PODBBridge()
        in_f = file(sys.argv[2], 'rU')
        person = RosettaPerson.get(int(sys.argv[1]))
        try:
            if len(sys.argv) == 7:
                print "Importing .po file..."
                bridge.imports(person, in_f, sys.argv[3], sys.argv[4], sys.argv[5],
                sys.argv[6])
            else:
                print "Importing .pot file..."
                bridge.imports(person, in_f, sys.argv[3], sys.argv[4], sys.argv[5])
        except:
            get_transaction().abort()
            raise
