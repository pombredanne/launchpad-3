# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Interface definitions for IHas<code related bits>."""

__metaclass__ = type
__all__ = [
    'IHasMergeProposals',
    ]


from zope.interface import Interface
from zope.schema import Choice, List

from canonical.launchpad import _
from lp.code.enums import BranchMergeProposalStatus

from lazr.restful.declarations import (
    REQUEST_USER, call_with, export_read_operation, operation_parameters,
    operation_returns_collection_of)


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
    @operation_returns_collection_of(Interface) #IBranchMergeProposal
    @export_read_operation()
    def getMergeProposals(status=None, visible_by_user=None):
        """Returns all merge proposals of a given status.

        :param status: A list of statuses to filter with.
        :param visible_by_user: Normally the user who is asking.
        :returns: A list of `IBranchMergeProposal`.
        """
