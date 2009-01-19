# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Interface for branch containers."""

__metaclass__ = type
__all__ = [
    'IBranchContainer',
    ]

from zope.interface import Interface, Attribute


# XXX: Add display name.
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


class IBranchContainer(Interface):
    """A container of branches.

    A product contains branches, a source package on a distroseries contains
    branches, and a person contains 'junk' branches.
    """

    name = Attribute("The name of the container.")
