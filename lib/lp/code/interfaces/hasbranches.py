# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interface definitions for IHas<code related bits>."""

__metaclass__ = type
__all__ = [
    'IHasBranches',
    'IHasMergeProposals',
    'IHasRequestedReviews',
    ]


from zope.interface import Interface
from zope.schema import Choice, Datetime, List

from canonical.launchpad import _
from lp.code.enums import BranchLifecycleStatus, BranchMergeProposalStatus

from lazr.restful.declarations import (
    REQUEST_USER, call_with, export_read_operation, operation_parameters,
    operation_returns_collection_of)


class IHasBranches(Interface):
    """Some things have related branches.

    This interface defines the common methods for getting branches for
    the objects that implement this interface.
    """

    # In order to minimise dependancies the returns_collection is defined as
    # Interface here and defined fully in the circular imports file.

    @operation_parameters(
        status=List(
            title=_("A list of branch lifecycle statuses to filter by."),
            value_type=Choice(vocabulary=BranchLifecycleStatus)),
        modified_since=Datetime(
            title=_('Limit the branches to those modified since this date.'),
            required=False))
    @call_with(visible_by_user=REQUEST_USER)
    @operation_returns_collection_of(Interface) # Really IBranch.
    @export_read_operation()
    def getBranches(status=None, visible_by_user=None,
                    modified_since=None):
        """Returns all branches with the given lifecycle status.

        :param status: A list of statuses to filter with.
        :param visible_by_user: Normally the user who is asking.
        :param modified_since: If set, filters the branches being returned
            to those that have been modified since the specified date/time.
        :returns: A list of `IBranch`.
        """


class IHasMergeProposals(Interface):
    """Some things have related merge proposals.

    This interface defines the common methods for getting merge proposals for
    the objects that implement this interface.
    """

    # In order to minimise dependancies the returns_collection is defined as
    # Interface here and defined fully in the circular imports file.

    @operation_parameters(
        status=List(
            title=_("A list of merge proposal statuses to filter by."),
            value_type=Choice(vocabulary=BranchMergeProposalStatus)))
    @call_with(visible_by_user=REQUEST_USER)
    @operation_returns_collection_of(Interface) # Really IBranchMergeProposal.
    @export_read_operation()
    def getMergeProposals(status=None, visible_by_user=None):
        """Returns all merge proposals of a given status.

        :param status: A list of statuses to filter with.
        :param visible_by_user: Normally the user who is asking.
        :returns: A list of `IBranchMergeProposal`.
        """


class IHasRequestedReviews(Interface):
    """IPersons can have reviews requested of them in merge proposals.

    This interface defines the common methods for getting these merge proposals
    for a particular person.
    """

    # In order to minimise dependancies the returns_collection is defined as
    # Interface here and defined fully in the circular imports file.

    @operation_parameters(
        status=List(
            title=_("A list of merge proposal statuses to filter by."),
            value_type=Choice(vocabulary=BranchMergeProposalStatus)))
    @call_with(visible_by_user=REQUEST_USER)
    @operation_returns_collection_of(Interface) # Really IBranchMergeProposal.
    @export_read_operation()
    def getRequestedReviews(status=None, visible_by_user=None):
        """Returns merge proposals that a review was requested from the person.

        This does not include merge proposals that were requested from
        teams that the person is part of. If status is not passed then
        it will return proposals that are in the "Needs Review" state.

        :param status: A list of statuses to filter with.
        :param visible_by_user: Normally the user who is asking.
        :returns: A list of `IBranchMergeProposal`.
        """
