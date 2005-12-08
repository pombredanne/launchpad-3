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
        outfile.write('~%s/%s/%s\t%d\n' % 
            (person_name, product_name, branch_name, branch.id))
    ztm.abort()

