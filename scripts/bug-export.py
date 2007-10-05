#!/usr/bin/python2.4
# Copyright 2006 Canonical Ltd.  All rights reserved.

import sys
import optparse

import _pythonpath

from zope.component import getUtility
from canonical.lp import initZopeless
from canonical.launchpad.interfaces import IProductSet
from canonical.launchpad.scripts import execute_zcml_for_scripts

from canonical.launchpad.scripts.bugexport import export_bugtasks

def main(argv):
    parser = optparse.OptionParser(
        description="Export bugs for a Launchpad product as XML")
    parser.add_option('-o', '--output', metavar='FILE', action='store',
                      help='Export bugs to this file',
                      type='string', dest='output', default=None)
    parser.add_option('-p', '--product', metavar='PRODUCT', action='store',
                      help='Which product to export',
                      type='string', dest='product', default=None)
    parser.add_option('--include-private', action='store_true',
                      help='Include private bugs in dump',
                      dest='include_private', default=False)

    options, args = parser.parse_args(argv[1:])

    if options.product is None:
        parser.error('No product specified')
    output = sys.stdout
    if options.output is not None:
        output = open(options.output, 'wb')
    
    execute_zcml_for_scripts()
    ztm = initZopeless()

    product = getUtility(IProductSet).getByName(options.product)
    if product is None:
        parser.error('Product %s does not exist' % options.product)

    export_bugtasks(ztm, product, output,
                    include_private=options.include_private)

if __name__ == '__main__':
    sys.exit(main(sys.argv))
