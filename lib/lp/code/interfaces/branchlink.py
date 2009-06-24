# Copyright 2006 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces for linking Specifications and Branches."""

__metaclass__ = type

__all__ = [
    "ISpecificationBranch",
    "ISpecificationBranchSet",
    ]

from lazr.restful.fields import CollectionField
from lazr.restful.declarations import (export_as_webservice_entry, exported,
    export_operation_as, export_write_operation)

from canonical.launchpad import _
from canonical.launchpad.interfaces.launchpad import IHasDateCreated
from lp.code.interfaces.branch import IBranch


class IHasLinkedBranches(IHasDateCreated):
    """A interface for handling branch linkages."""

    linked_branches = exported(
        CollectionField(
            title=_('MultiJoin of the bugs which are dups of this one'),
            value_type=IBranch,
            readonly=True))

    def linkBranch(branch, registrant):
        """Associate a branch with this bug.

        :param branch: The branch being linked to.
        :param registrant: The user linking the branch.
        """

    def unlinkBranch(branch, unregistrant):
        """Unlink a branch from this bug.

        :param branch: The branch being unlinked from.
        :param unregistrant: The user unlinking the branch.
        """

    def hasBranches():
        """Return whether or not the item has linked_branches."""

