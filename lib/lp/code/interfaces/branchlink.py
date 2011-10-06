# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interfaces for linking Specifications and Branches."""

__metaclass__ = type

__all__ = [
    "IHasLinkedBranches",
    "ISpecificationBranch",
    "ISpecificationBranchSet",
    ]

from lazr.restful.declarations import (
    call_with,
    export_as_webservice_entry,
    export_operation_as,
    export_write_operation,
    exported,
    operation_for_version,
    operation_parameters,
    operation_returns_entry,
    REQUEST_USER,
    )
from lazr.restful.fields import (
    CollectionField,
    Reference,
    )
from zope.interface import Interface

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
    @operation_for_version('beta')
    def linkBranch(branch, registrant):
        """Associate a branch with this bug.

        :param branch: The branch being linked to.
        :param registrant: The user linking the branch.
        """

    @call_with(user=REQUEST_USER)
    @operation_parameters(
        branch=Reference(schema=IBranch))
    @export_write_operation()
    @operation_for_version('beta')
    def unlinkBranch(branch, user):
        """Unlink a branch from this bug.

        :param branch: The branch being unlinked from.
        :param user: The user unlinking the branch.
        """

