#!/usr/bin/python
# Copyright 2004 Canonical Ltd.  All rights reserved.
# arch-tag: 752bd71e-584e-416e-abff-a4eb6c82399c

import sys

from optparse import OptionParser

import canonical.lp
from canonical.launchpad.database import Person, POTemplate, Product
from canonical.launchpad.database import ProjectSet
from canonical.rosetta.pofile_adapters import TemplateImporter, POFileImporter

stats_message = """
Msgsets matched to the potemplate that have a non-fuzzy translation in
the PO file when we last parsed it: %d

Msgsets where we have a newer translation in rosetta than the one in
the PO file when we last parsed it: %d

Msgsets where we have a translation in rosetta but there was no
translation in the PO file when we last parsed it: %d
"""

def get_project(name):
    # XXX: We should probably be using a utility for getting the project.
    # -- Dafydd Harries, Fri, 19 Nov 2004 01:31:23 -0500
    # XXX: This will be difficult when this is run as a script.
    #      Perhaps initZopeless needs to load adapters and utilities too?
    # -- Steve Alexander, Fri Nov 19 15:25:08 UTC 2004

    try:
        project = ProjectSet()[name]
    except KeyError:
        print "project '%s' does not exist"
        sys.exit(1)

    return project

def get_product(project, name):
    products = list(Product.selectBy(projectID = project.id, name = name))

    if len(products) == 0:
        print "product '%s' does not exist for project '%s'" % (
            name, project.name)
        sys.exit(1)

    return products[0]

def get_template(product, name):
    templates = list(POTemplate.selectBy(productID = product.id, name = name))

    if len(templates) == 0:
        print ("template '%s' does not exist for project '%s', product '%s'"
               % (name, product.project.name, product.name))
        sys.exit(1)

    return templates[0]

class PODBBridge:

    def __init__(self):
        self._tm = canonical.lp.initZopeless()

    def commit(self):
        self._tm.commit()

    def abort(self):
        self._tm.abort()

    def imports(self, person, fileHandle, projectName, productName,
            poTemplateName, languageCode = None):
        project = get_project(projectName)
        product = get_product(project, productName)
        poTemplate = get_template(product, poTemplateName)

        if languageCode is None:
            # We are importing a POTemplate.
            importer = TemplateImporter(poTemplate, None)
        else:
            # We are importing a POFile.
            try:
                poFile = poTemplate.poFile(languageCode)
            except KeyError:
                poFile = poTemplate.newPOFile(person, languageCode)

            importer = POFileImporter(poFile, person)

        importer.doImport(fileHandle)

    def update_stats(self, projectName, productName, poTemplateName,
            languageCode, newImport = False):
        project = get_project(projectName)
        product = get_product(project, productName)
        poTemplate = get_template(product, poTemplateName)
        # XXX: Perhaps we should try and catch the case where the PO file does
        # not exist.
        #  -- Dafydd Harries, Fri, 19 Nov 2004 01:29:30 -0500
        poFile = poTemplate.poFile(languageCode)
        current, updates, rosetta = poFile.updateStatistics(newImport)
        print stats_message % (current, updates, rosetta)

def parse_options():
    parser = OptionParser()
    parser.add_option("-o", "--owner", dest="owner",
        help="The database ID for the owner of the imported file")
    parser.add_option("-f", "--file", dest="filename",
        help="The file to import data from")
    parser.add_option("-p", "--project", dest="project",
        help="The project the imported file belongs to")
    parser.add_option("-d", "--product", dest="product",
        help="The product the imported file belongs to")
    parser.add_option("-t", "--potemplate", dest="potemplate",
        help="The template the imported file belongs to")
    parser.add_option("-l", "--language", dest="language",
        help="The language code, for importing PO files")
    parser.add_option("-U", "--update-stats-only", dest="update_stats_only",
        default=False, action="store_true",
        help="Update the statistics fields, don't import anything")
    parser.add_option("-n", "--no-op", dest="noop",
        default=False, action="store_true",
        help="Don't actually write anything to the database,"
             " just see what would happen")

    (options, args) = parser.parse_args()

    return options

def main(owner, project, product, potemplate, language, update_stats_only,
        filename, noop):
    if update_stats_only:
        print "Connecting to database..."
        bridge = PODBBridge()
        try:
            print "Updating %s pofile for '%s'..." % (potemplate, language)
            bridge.update_stats(project, product, potemplate, language)
        except: # Bare except followed by a raise.
            print "aborting database transaction"
            bridge.abort()
            raise
        else:
            if noop:
                bridge.abort()
            else:
                bridge.commit()
    else:
        if filename is None:
            raise RuntimeError("No filename specified.")

        print "Connecting to database..."

        bridge = PODBBridge()
        in_f = file(filename, 'rU')
        person = Person.get(int(owner))

        try:
            print "Importing %s ..." % filename

            bridge.imports(person, in_f, project, product, potemplate,
                language)

            if language is not None:
                print "Updating %s pofile for '%s'..." % (
                    potemplate, language)

                bridge.update_stats(project, product, potemplate, language,
                    True)
        except: # Bare except followed by a raise.
            print "aborting database transaction"
            bridge.abort()
            raise
        else:
            if noop:
                bridge.abort()
            else:
                bridge.commit()

if __name__ == '__main__':
    options = parse_options()

    for name in ('owner', 'project', 'product', 'potemplate'):
        if getattr(options, name) is None:
            raise RuntimeError("No %s specified." % name)

    main(
        owner = options.owner,
        project = options.project,
        product = options.product,
        potemplate = options.potemplate,
        language = options.language,
        update_stats_only = options.update_stats_only,
        filename = options.filename,
        noop = options.noop
        )

