# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Branch subset."""

__metaclass__ = type
__all__ = [
    'IBranchSubset',
    ]

from zope.interface import Interface


class IBranchSubset(Interface):
    # XXX: Write tests to guarantee that adapted objects are being secured via
    # this interface.
    pass


# XXX: filters for
# - "visible to user"
# - within product
# - owned by person
# - registered by person?
# - subscribed by person?
# - lifecycle_status

# XXX: revision support
# - Add recent revision count
# - Add recent committer count


# XXX: counts
# - Add team_owner_count
# - Add person_owner_count

# XXX: find existing tests for all of this crap and migrate / delete it.
# - database.tests.test_branch
#   - TestGetBranchForContextVisibleUser
#   - BranchSorting

# XXX: types of subsets
# - source package
# - registered by person
# - subscribed by person
# - project
# - global set (i.e. IBranchSet)

# XXX: Possibly add a group-by-namespaces feature
# XXX: make sure we can get canonical_url of container if it exists.
# XXX: somehow deal with sort
