# Copyright 2004 Canonical Ltd.  All rights reserved.
# arch-tag: 752bd71e-584e-416e-abff-a4eb6c82399c

from zope.component.tests.placelesssetup import PlacelessSetup
import canonical.lp
from canonical.rosetta.sql import RosettaPerson, RosettaPOTemplate, \
    RosettaProduct
from canonical.database.doap import ProjectSet
from canonical.database.sqlbase import SQLBase
from canonical.rosetta.pofile_adapters import TemplateImporter, POFileImporter
from optparse import OptionParser
from sqlobject.dbconnection import Transaction

class PODBBridge(PlacelessSetup):

    def __init__(self):
        canonical.lp.initZopeless()
        self._transaction = Transaction(SQLBase._connection)
        SQLBase._connection = self._transaction

    def commit(self):
        self._transaction.commit()

    def rollback(self):
        self._transaction.rollback()

    def imports(self, person, file, projectName, productName, poTemplateName,
        languageCode=None):
        try:
            project = ProjectSet()[projectName]
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
            importer = POFileImporter(poFile, person)
        importer.doImport(file)

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-o", "--owner", dest="owner",
        help="The database ID for the owner of the imported file")
    parser.add_option("-f", "--file", dest="file",
        help="The file to import data from")
    parser.add_option("-p", "--project", dest="project",
        help="The project the imported file belongs to")
    parser.add_option("-d", "--product", dest="product",
        help="The product the imported file belongs to")
    parser.add_option("-t", "--potemplate", dest="potemplate",
        help="The template the imported file belongs to")
    parser.add_option("-l", "--language", dest="language",
        help="The language code, for importing PO files")

    (options, args) = parser.parse_args()

    for name in ('owner', 'file', 'project', 'product', 'potemplate'):
        if getattr(options, name) is None:
            raise RuntimeError("No %s specified." % name)

    print "Connecting to database..."
    bridge = PODBBridge()
    in_f = file(options.file, 'rU')
    person = RosettaPerson.get(int(options.owner))
    try:
        print "Importing %s ..." % options.file
        bridge.imports(person, in_f, options.project, options.product,
                       options.potemplate, options.language)
    except:
        print "aborting database transaction"
        bridge.rollback()
        raise
    else:
        bridge.commit()
