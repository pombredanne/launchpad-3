# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""The interface for branch merge proposals."""

__metaclass__ = type
__all__ = [
    'InvalidBranchMergeProposal',
    'IBranchMergeProposal',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Choice, Datetime, Int

from canonical.launchpad import _

from canonical.launchpad.fields import Whiteboard


class InvalidBranchMergeProposal(Exception):
    """Raised during the creation of a new branch merge proposal.

    The text of the exception is the rule violation.
    """


class IBranchMergeProposal(Interface):
    """Branch merge proposals show intent of landing one branch on another."""

    id = Int(
        title=_('DB ID'), required=True, readonly=True,
        description=_("The tracking number for this question."))

    registrant = Choice(
        title=_('Person'), required=True,
        vocabulary='ValidPersonOrTeam', readonly=True,
        description=_('The person who registered the landing target.'))

    source_branch = Choice(
        title=_('Source Branch'),
        vocabulary='BranchRestrictedOnProduct', required=True, readonly=True,
        description=_("The branch that has code to land."))

    target_branch = Choice(
        title=_('Target Branch'),
        vocabulary='BranchRestrictedOnProduct', required=True, readonly=True,
        description=_("The branch that the source branch will be merged "
                      "into."))

    dependent_branch = Choice(
        title=_('Dependent Branch'),
        vocabulary='BranchRestrictedOnProduct', required=False, readonly=True,
        description=_("The branch that the source branch branched from. "
                      "If this is the same as the target branch, then leave "
                      "this field blank."))

    whiteboard = Whiteboard(
        title=_('Whiteboard'), required=False,
        description=_('Notes about the merge.'))

    merged_revno = Int(
        title=_("Merged Revision Number"), required=False,
        description=_("The revision number on the target branch which "
                      "contains the merge from the source branch."))

    date_merged = Datetime(
        title=_('Date Merged'), required=False,
        description=_("The date that the source branch was merged into the "
                      "target branch"))

    merge_reporter = Attribute(
        "The user that marked the branch as merged.")

    date_created = Datetime(
        title=_('Date Created'), required=True, readonly=True)

    def markAsMerged(merged_revno=None, date_merged=None, merge_reporter=None):
        """Mark the branch merge proposal as merged.

        If the `merged_revno` is supplied, then the `BranchRevision` is checked
        to see that revision is available in the target branch.  If it is
        then the date from that revision is used as the `date_merged`.  If it
        is not available, then the `date_merged` is set as if the merged_revno
        was not supplied.

        If no `merged_revno` is supplied, the `date_merged` is set to the value
        of date_merged, or if the parameter date_merged is None, then UTC_NOW
        is used.

        :param merged_revno: The revision number in the target branch that
                             contains the merge of the source branch.
        :type merged_revno: ``int``

        :param date_merged: The date/time that the merge took place.
        :type merged_revno: ``datetime`` or a stringified date time value.

        :param merge_reporter: The user that is marking the branch as merged.
        :type merge_reporter: ``Person``
        """
