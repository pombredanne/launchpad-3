#!/usr/bin/python
# Copyright 2004 Canonical Ltd.  All rights reserved.

import sys, base64

from optparse import OptionParser

from canonical.database.constants import UTC_NOW
import canonical.lp
from canonical.launchpad.database import Person, POTemplate
from canonical.launchpad.database import ProductSet
from canonical.interfaces import RosettaImportStatus

from canonical.rosetta.pofile import POParser

stats_message = """
Msgsets matched to the potemplate that have a non-fuzzy translation in
the PO file when we last parsed it: %d

Msgsets where we have a newer translation in rosetta than the one in
the PO file when we last parsed it: %d

Msgsets where we have a translation in rosetta but there was no
translation in the PO file when we last parsed it: %d
"""

def get_product(name):
    # XXX: Dafydd Harries 2004-11-19:
    # We should probably be using a utility for getting the product.
    # -- 
    # XXX: Steve Alexander 2004-11-19
    #      This will be difficult when this is run as a script.
    #      Perhaps initZopeless needs to load adapters and utilities too?
    try:
        product = ProductSet()[name]
    except KeyError:
        print "product '%s' does not exist" % name
        sys.exit(1)

    return product

def get_template(product, name):
    templates = list(POTemplate.selectBy(productID = product.id, name = name))

    if len(templates) == 0:
        print ("template '%s' does not exist for product '%s'"
               % (name, product.name))
        sys.exit(1)

    return templates[0]

class PODBBridge:
    def __init__(self):
        self._tm = canonical.lp.initZopeless()

    def commit(self):
        self._tm.commit()

    def abort(self):
        self._tm.abort()

    def imports(self, person, fileHandle, productName,
            poTemplateName, languageCode = None):
        product = get_product(productName)
        poTemplate = get_template(product, poTemplateName)

        fileData = fileHandle.read()

        parser = POParser()
        parser.write(fileData)
        parser.finish()

        if languageCode is None:
            # We are importing a PO template.
            poTemplate.rawfile = base64.encodestring(fileData)
            poTemplate.daterawimport = UTC_NOW
            poTemplate.rawimporter = person
            poTemplate.rawimportstatus = RosettaImportStatus.PENDING
        else:
            # We are importing a PO file.
            poFile = poTemplate.getOrCreatePOFile(languageCode)
            poFile.rawfile = base64.encodestring(fileData)
            poFile.daterawimport = UTC_NOW
            poFile.rawimporter = person
            poFile.rawimportstatus = RosettaImportStatus.PENDING

    def update_stats(self, productName, poTemplateName,
            languageCode):
        product = get_product(productName)
        poTemplate = get_template(product, poTemplateName)
        # XXX: Dafydd Harries 2004-11-19:
        # Perhaps we should try and catch the case where the PO file does
        # not exist.
        poFile = poTemplate.poFile(languageCode)
        current, updates, rosetta = poFile.updateStatistics()
        print stats_message % (current, updates, rosetta)

def parse_options():
    parser = OptionParser()
    parser.add_option("-o", "--owner", dest="owner",
        help="The database ID for the owner of the imported file")
    parser.add_option("-f", "--file", dest="filename",
        help="The file to import data from")
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

def main(owner, product, potemplate, language, update_stats_only,
        filename, noop):
    print "Connecting to database..."

    bridge = PODBBridge()

    if update_stats_only:
        try:
            print "Updating %s pofile for '%s'..." % (potemplate, language)
            bridge.update_stats(product, potemplate, language)
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

        in_f = file(filename, 'rU')
        person = Person.get(int(owner))

        try:
            print "Importing %s ..." % filename

            bridge.imports(person, in_f, product, potemplate,
                language)
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

    for name in ('owner', 'product', 'potemplate'):
        if getattr(options, name) is None:
            raise RuntimeError("No %s specified." % name)

    main(
        owner = options.owner,
        product = options.product,
        potemplate = options.potemplate,
        language = options.language,
        update_stats_only = options.update_stats_only,
        filename = options.filename,
        noop = options.noop
        )

