# Copyright 2004 Canonical Ltd.  All rights reserved.
# arch-tag: 752bd71e-584e-416e-abff-a4eb6c82399c

from optparse import OptionParser

from zope.component.tests.placelesssetup import PlacelessSetup

from sqlobject.dbconnection import Transaction

import canonical.lp
from canonical.launchpad.database import Person, POTemplate, Product
from canonical.launchpad.database import ProjectSet
from canonical.database.sqlbase import SQLBase
from canonical.rosetta.pofile_adapters import TemplateImporter, POFileImporter

stats_message = """
Msgsets matched to the potemplate that have a non-fuzzy translation in
the PO file when we last parsed it: %d

Msgsets where we have a newer translation in rosetta than the one in
the PO file when we last parsed it: %d

Msgsets where we have a translation in rosetta but there was no
translation in the PO file when we last parsed it: %d
"""


class PODBBridge(PlacelessSetup):

    def __init__(self):
        canonical.lp.initZopeless()
        self._transaction = Transaction(SQLBase._connection)
        SQLBase._connection = self._transaction

    def commit(self):
        self._transaction.commit()

    def rollback(self):
        self._transaction.rollback()

    def imports(self, person, fileHandle, projectName, productName, poTemplateName,
        languageCode=None):
        try:
            project = ProjectSet()[projectName]
            product = Product.selectBy(projectID = project.id,
                                              name=productName)[0]
        except (IndexError, KeyError):
            import sys
            t, e, tb = sys.exc_info()
            raise t, "Couldn't find record in database", tb
        try:
            poTemplate = POTemplate.selectBy(productID = product.id,
                                                    name=poTemplateName)[0]
        except IndexError:
            # XXX: should use Product.newPOTemplate when it works
            if languageCode is not None:
                import sys
                t, e, tb = sys.exc_info()
                raise t, "Couldn't find record in database", tb
            poTemplate = POTemplate(product=product,
                                           name=poTemplateName,
                                           title=poTemplateName, # will have to be edited
                                           description=poTemplateName, # will have to be edited
                                           path=fileHandle.name,
                                           iscurrent=True,
                                           datecreated='NOW',
                                           copyright='XXX: FIXME',
                                           priority=2, # XXX: FIXME
                                           branchID=1, # XXX: FIXME
                                           licenseID=1, # XXX: FIXME
                                           messagecount=0,
                                           ownerID=person.id)
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
        importer.doImport(fileHandle)

    def update_stats(self, projectName, productName, poTemplateName, languageCode):
        try:
            project = DBProjects()[projectName]
            product = Product.selectBy(projectID = project.id,
                                              name=productName)[0]
            poTemplate = POTemplate.selectBy(productID = product.id,
                                                    name=poTemplateName)[0]
            poFile = poTemplate.poFile(languageCode)
        except (IndexError, KeyError):
            import sys
            t, e, tb = sys.exc_info()
            raise t, "Couldn't find record in database", tb
        current, updates, rosetta = poFile.updateStatistics()
        print stats_message % (current, updates, rosetta)

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
    parser.add_option("-U", "--update-stats", dest="update_stats",
        default=False, action="store_true",
        help="Update the statistics fields, don't import anything")
    parser.add_option("-n", "--no-op", dest="noop",
        default=False, action="store_true",
        help="Don't actually write anything to the database, just "
                      "see what would happen")

    (options, args) = parser.parse_args()

    for name in ('owner', 'project', 'product', 'potemplate'):
        if getattr(options, name) is None:
            raise RuntimeError("No %s specified." % name)

    if getattr(options, 'update_stats'):
        print "Connecting to database..."
        bridge = PODBBridge()
        try:
            print "Updating %s pofile for '%s'..." % (
                options.potemplate, options.language)
            bridge.update_stats(options.project, options.product,
                                options.potemplate, options.language)
        except:
            print "aborting database transaction"
            bridge.rollback()
            raise
        else:
            if options.noop:
                bridge.rollback()
            else:
                bridge.commit()
    else:
        if not getattr(options, 'file'):
            raise RuntimeError("No filename specified.")

        print "Connecting to database..."
        bridge = PODBBridge()
        in_f = file(options.file, 'rU')
        person = Person.get(int(options.owner))
        try:
            print "Importing %s ..." % options.file
            bridge.imports(person, in_f, options.project, options.product,
                           options.potemplate, options.language)
        except:
            print "aborting database transaction"
            bridge.rollback()
            raise
        else:
            if options.noop:
                bridge.rollback()
            else:
                bridge.commit()
