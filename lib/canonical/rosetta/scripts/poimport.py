# Copyright 2004 Canonical Ltd.  All rights reserved.
# arch-tag: 752bd71e-584e-416e-abff-a4eb6c82399c

from zope.component.tests.placelesssetup import PlacelessSetup
from canonical.database.sqlbase import SQLBase
from canonical.rosetta.sql import RosettaPerson, RosettaPOTemplate, \
    RosettaProject, RosettaProduct 
from sqlobject import connectionForURI
from canonical.rosetta.pofile_adapters import TemplateImporter, POFileImporter
from optparse import OptionParser

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
    parser = OptionParser()
    parser.add_option("-o", "--owner", dest="ownerID",
                      help="DB ID for the Owner")
    parser.add_option("-f", "--file", dest="file",
                      help="FILE to import")
    parser.add_option("-p", "--project", dest="project",
                      help="Project name owner of this file")
    parser.add_option("-d", "--product", dest="product",
                      help="Product name owner of this file")
    parser.add_option("-t", "--potemplate", dest="potemplate",
                      help="POTemplate name owner of this file")
    parser.add_option("-l", "--language", dest="language",
                      help="Language code for this pofile")

    (options, args) = parser.parse_args()
    
    bridge = PODBBridge()
    in_f = file(options.file, 'rU')
    person = RosettaPerson.get(int(options.ownerID))
    try:
        print "Importing %s ..." % options.file
        bridge.imports(person, in_f, options.project, options.product,
                       options.potemplate, options.language)
    except:
        get_transaction().abort()
        raise
