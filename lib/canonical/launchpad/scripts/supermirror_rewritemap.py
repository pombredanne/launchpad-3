# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Support code for cronscripts/supermirror_rewritemap.py."""

__metaclass__ = type

from zope.component import getUtility

from canonical.launchpad.interfaces import IBranchSet


def write_map(outfile):
    branches = getUtility(IBranchSet)
    for branch in branches:
        line = generate_mapping_for_branch(branch)
        outfile.write(line)


def generate_mapping_for_branch(branch):
    person_name = branch.owner.name
    product = branch.product
    if product is None:
        product_name = '+junk'
    else:
        product_name = branch.product.name
    branch_name = branch.name
    
    branch_location = split_branch_id(branch.id)
    
    return ('~%s/%s/%s\t%s\n' % 
        (person_name, product_name, branch_name, branch_location))


def split_branch_id(branch_id):
    """Split a branch ID over multiple directories.

    e.g.:
    
        >>> split_branch_id(0xabcdef12)
        'ab/cd/ef/12'
    """
    h = "%08x" % int(branch_id)
    branch_location = '%s/%s/%s/%s' % (h[:2], h[2:4], h[4:6], h[6:])
    return branch_location

