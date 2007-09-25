#!/usr/bin/python2.4

"""Import a single PO template or PO file into the database."""

import base64
import sys

from canonical.lp import initZopeless
from canonical.database.constants import UTC_NOW
from canonical.launchpad.database import ProductSet
from canonical.launchpad.interfaces import RosettaImportStatus
from canonical.rosetta.poexport import POExport

def po_import(product_name, template_name, language_code, contents):
    products = ProductSet()

    product = products[product_name]

    template = product.poTemplate(template_name)

    if language_code is not None:
        potemplate_or_pofile = template.getOrCreatePOFile(language_code)
    else:
        potemplate_or_pofile = template

    potemplate_or_pofile.rawfile = base64.encodestring(contents)
    potemplate_or_pofile.daterawimport = UTC_NOW
    potemplate_or_pofile.rawimporter = None
    potemplate_or_pofile.rawimportstatus = RosettaImportStatus.PENDING
    potemplate_or_pofile.doRawImport()

def main(argv):
    if len(argv) not in (3, 4):
        print "Usage: %s product template [language]" % argv[0]
        return 1

    contents = sys.stdin.read()

    if len(argv) == 3:
        po_import(argv[1], argv[2], None, contents)
    else:
        po_import(argv[1], argv[2], argv[3], contents)

    return 0

if __name__ == '__main__':
    ztm = initZopeless()

    status = main(sys.argv)

    if status == 0:
        ztm.commit()
    else:
        ztm.abort()

    sys.exit(status)

