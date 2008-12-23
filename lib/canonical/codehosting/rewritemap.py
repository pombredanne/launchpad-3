# Copyright 2004-2008 Canonical Ltd.  All rights reserved.

"""Support code for cronscripts/supermirror_rewritemap.py."""

__metaclass__ = type

from zope.component import getAdapter, getUtility

from canonical.codehosting import branch_id_to_path
from canonical.launchpad.interfaces import IBranchSet
from canonical.launchpad.webapp.interfaces import IAuthorization


def write_map(outfile):
    """Write a file mapping each branch user/product/name to branch id.

    The file will be written in a format suitable for use with Apache's
    RewriteMap directive.  Only publicly visible branchs have rewrite
    entries.  Remote branches are not mirrored, so are not stored in
    the codehosting facility, so not available through http.
    """
    branches = getUtility(IBranchSet).getRewriteMap()
    for branch in branches:
        access = getAdapter(branch, IAuthorization, name='launchpad.View')
        if not access.checkUnauthenticated():
            continue
        line = generate_mapping_for_branch(branch)
        outfile.write(line)


def generate_mapping_for_branch(branch):
    """Generate a single line of the branch mapping file."""
    branch_location = branch_id_to_path(branch.id)
    return '%s\t%s\n' % (branch.unique_name, branch_location)
