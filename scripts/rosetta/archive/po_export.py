#!/usr/bin/python2.4

"""Export a single PO file from the database."""

import sys

from canonical.lp import initZopeless
from canonical.launchpad.database import ProductSet
from canonical.rosetta.poexport import POExport

def po_export(product_name, template_name, language_code):
    products = ProductSet()

    product = products[product_name]

    template = product.poTemplate(template_name)

    exporter = POExport(template)

    return exporter.export(language_code)

def main(argv):
    if len(argv) != 4:
        print "Usage: %s product template language" % argv[0]
        return 1

    print po_export(argv[1], argv[2], argv[3])
    return 0

if __name__ == '__main__':
    ztm = initZopeless()

    status = main(sys.argv)

    ztm.abort()

    sys.exit(status)

