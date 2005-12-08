# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Support code for cronscripts/supermirror_rewritemap.py."""

__metaclass__ = type

from canonical.launchpad.database import Branch

def main(ztm, outfile):
    ztm.begin()
    branches = Branch.select()
    for branch in branches:
        person_name = branch.owner.name
        product = branch.product
        if product is None:
            product_name = '+junk'
        else:
            product_name = branch.product.name
        branch_name = branch.name

        h = "%08x" % int(branch.id)
        branch_location = '%s/%s/%s/%s' % (h[:2], h[2:4], h[4:6], h[6:])

        outfile.write('~%s/%s/%s\t%s\n' % 
            (person_name, product_name, branch_name, branch_location))
    ztm.abort()

