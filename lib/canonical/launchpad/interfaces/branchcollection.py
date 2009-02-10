# Copyright 2009 Canonical Ltd.  All rights reserved.

"""A collection of branches."""

__metaclass__ = type
__all__ = [
    'IBranchCollection',
    ]

from zope.interface import Attribute, Interface


class IBranchCollection(Interface):
    """A collection of branches."""

    # XXX: Write tests to guarantee that adapted objects are being secured via
    # this interface.

    count = Attribute("The number of branches in this collection.")

    def getBranches():
        """Return a result sest of all branches in this collection."""


# XXX: revision support

# XXX: counts
# - Add team_owner_count
# - Add person_owner_count
# - others?

# XXX: find existing tests for all of this crap and migrate / delete it.
# - database.tests.test_branch
#   - TestGetBranchForContextVisibleUser
#   - BranchSorting
# - others?

# XXX: adapters / easy access methods for common views / concepts
# - source package
# - registered by person
# - subscribed by person
# - project
# - global set (i.e. IBranchSet)

# XXX: Possibly add a group-by-namespaces feature
# XXX: make sure we can get canonical_url of container if it exists.
# XXX: somehow deal with sort
