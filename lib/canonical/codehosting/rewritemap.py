# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Support code for cronscripts/supermirror_rewritemap.py."""

__metaclass__ = type

from zope.component import getUtility

from canonical.codehosting import branch_id_to_path
from canonical.launchpad.interfaces import BranchType, IBranchSet


def write_map(outfile):
    """Write a file mapping each branch user/product/name to branch id.

    The file will be written in a format suitable for use with Apache's
    RewriteMap directive.  Only publicly visible branchs have rewrite
    entries.  Remote branches are not mirrored, so are not stored in
    the codehosting facility, so not available through http.
    """
    branches = getUtility(IBranchSet)
    for branch in branches:
        if not branch.private and branch.branch_type != BranchType.REMOTE:
            line = generate_mapping_for_branch(branch)
            outfile.write(line)


def generate_mapping_for_branch(branch):
    """Generate a single line of the branch mapping file."""
    person_name = branch.owner.name
    product = branch.product
    if product is None:
        product_name = '+junk'
    else:
        product_name = branch.product_name
    branch_name = branch.name

    branch_location = branch_id_to_path(branch.id)

    return ('~%s/%s/%s\t%s\n' %
        (person_name, product_name, branch_name, branch_location))
