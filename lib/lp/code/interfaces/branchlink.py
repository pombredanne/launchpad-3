# Copyright 2006 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces for linking Specifications and Branches."""

__metaclass__ = type

__all__ = [
    "ISpecificationBranch",
    "ISpecificationBranchSet",
    ]

from zope.interface import Interface

from lazr.restful.fields import CollectionField, Reference
from lazr.restful.declarations import (call_with, export_as_webservice_entry,
    exported, export_operation_as, export_write_operation,
    operation_parameters, operation_returns_entry, REQUEST_USER)

from canonical.launchpad import _
from lp.code.interfaces.branch import IBranch
from lp.code.interfaces.branchtarget import IHasBranchTarget


class IHasLinkedBranches(Interface):
    """A interface for handling branch linkages."""

    linked_branches = exported(
        CollectionField(
            title=_('MultiJoin of the bugs which are dups of this one'),
            value_type=Reference(schema=IBranch),
            readonly=True))

    @call_with(registrant=REQUEST_USER)
    @operation_parameters(
        branch=Reference(schema=IBranch))
    @export_write_operation()
    def linkBranch(branch, registrant):
        """Associate a branch with this bug.

        :param branch: The branch being linked to.
        :param registrant: The user linking the branch.
        """

    @call_with(unregistrant=REQUEST_USER)
    @operation_parameters(
        branch=Reference(schema=IBranch))
    @export_write_operation()
    def unlinkBranch(branch, unregistrant):
        """Unlink a branch from this bug.

        :param branch: The branch being unlinked from.
        :param unregistrant: The user unlinking the branch.
        """

