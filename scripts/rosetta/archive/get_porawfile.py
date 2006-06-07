#!/usr/bin/python
#
# Copyright 2004 Canonical Ltd.  All rights reserved.

import sys, base64

import canonical.lp
from canonical.launchpad.database import Product

def getRawFile(productname, templatename, lang_code):
    products = list(Product.selectBy(name = productname))

    if len(products) != 1:
        raise KeyError, productname

    product = products[0]

    template = product.poTemplate(templatename)

    if lang_code is None:
        file = template.rawfile
    else:
        pofile = template.getPOFileByLang(lang_code)
        file = pofile.rawfile

    if file is not None:
        print base64.decodestring(file)
    else:
        print '''We don't have a rawfile.'''


if __name__ == '__main__':
    if len(sys.argv) < 3:
        raise RuntimeError("usage: %s product template [language_code]" % sys.argv[0])

    product = sys.argv[1]
    template = sys.argv[2]

    if len(sys.argv) == 4:
        lang_code = sys.argv[3]
    else:
        lang_code = None

    ztm = canonical.lp.initZopeless()

    getRawFile(product, template, lang_code)

