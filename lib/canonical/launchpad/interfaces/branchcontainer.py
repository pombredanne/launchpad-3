# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Interface for branch containers."""

__metaclass__ = type
__all__ = [
    'IBranchContainer',
    ]

from zope.interface import Interface, Attribute


class IBranchContainer(Interface):
    """A container of branches.

    A product contains branches, a source package on a distroseries contains
    branches, and a person contains branches in two different ways ('branches
    owned' and 'junk branches').
    """

    name = Attribute("The name of the container.")

    def getBranches():
        """Return the branches in this container."""

    # TODO: add lifecycle_statuses filter
    # TODO: add visible_by_user filter
    # TODO: add sort_by option
    # TODO: add quantity / limit option
    # TODO: add getTargetBranchesForUsersMergeProposals, whatever that is.
    # TODO: add subscribed-by-user filter
    # TODO: add owned-by-user filter
    # TODO: add registered-by-user filter
