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


# XXX: Add 'branches' or __iter__ feature
# XXX: filter by "visible to user"
# XXX: Add 'revisions' property or 'getRecentRevisions' method
# XXX: Add branch count
# XXX: Add recent revision count
# XXX: Add recent committer count
# XXX: Add team_owner_count
# XXX: Add person_owner_count
# XXX: Possibly add a group-by-namespaces feature
# XXX: filter by lifecyle
# XXX: make sure we can get canonical_url of container
# XXX: make adapters for IProduct, IPerson, ISourcePackage
# XXX: somehow deal with sort
# XXX: registered by person
# XXX: owned by person
# XXX: subscribed by person
