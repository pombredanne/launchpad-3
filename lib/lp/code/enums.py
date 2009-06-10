# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Enumerations used in the lp/code modules."""

__metaclass__ = type
__all__ = [
    'BranchLifecycleStatus',
    'BranchLifecycleStatusFilter',
    'BranchMergeControlStatus',
    'BranchMergeProposalStatus',
    'BranchSubscriptionDiffSize',
    'BranchSubscriptionNotificationLevel',
    'BranchType',
    'BranchVisibilityRule',
    'CodeImportReviewStatus',
    'CodeReviewNotificationLevel',
    'RevisionControlSystems',
    'TeamBranchVisibilityRule',
    'UICreatableBranchType',
    ]

from lazr.enum import (
    DBEnumeratedType, DBItem, EnumeratedType, Item, use_template)


class BranchLifecycleStatus(DBEnumeratedType):
    """Branch Lifecycle Status

    This indicates the status of the branch, as part of an overall
    "lifecycle". The idea is to indicate to other people how mature this
    branch is, or whether or not the code in the branch has been deprecated.
    Essentially, this tells us what the author of the branch thinks of the
    code in the branch.
    """

    EXPERIMENTAL = DBItem(10, """
        Experimental

        Still under active development, and not suitable for merging into
        release branches.
        """)

    DEVELOPMENT = DBItem(30, """
        Development

        Shaping up nicely, but incomplete or untested, and not yet ready for
        merging or production use.
        """)

    MATURE = DBItem(50, """
        Mature

        Completely addresses the issues it is supposed to, tested, and stable
        enough for merging into other branches.
        """)

    MERGED = DBItem(70, """
        Merged

        Successfully merged into its target branch(es). No further development
        is anticipated.
        """)

    ABANDONED = DBItem(80, "Abandoned")


class BranchMergeControlStatus(DBEnumeratedType):
    """Branch Merge Control Status

    Does the branch want Launchpad to manage a merge queue, and if it does,
    how does the branch owner handle removing items from the queue.
    """

    NO_QUEUE = DBItem(1, """
        Does not use a merge queue

        The branch does not use the merge queue managed by Launchpad.  Merges
        are tracked and managed elsewhere.  Users will not be able to queue up
        approved branch merge proposals.
        """)

    MANUAL = DBItem(2, """
        Manual processing of the merge queue

        One or more people are responsible for manually processing the queued
        branch merge proposals.
        """)

    ROBOT = DBItem(3, """
        A branch merge robot is used to process the merge queue

        An external application, like PQM, is used to merge in the queued
        approved proposed merges.
        """)

    ROBOT_RESTRICTED = DBItem(4, """
        The branch merge robot used to process the queue is in restricted mode

        When the robot is in restricted mode, normal queued branches are not
        returned for merging, only those with "Queued for Restricted
        merging" will be.
        """)


class BranchType(DBEnumeratedType):
    """Branch Type

    The type of a branch determins the branch interaction with a number
    of other subsystems.
    """

    HOSTED = DBItem(1, """
        Hosted

        Launchpad is the primary location of this branch.
        """)

    MIRRORED = DBItem(2, """
        Mirrored

        Primarily hosted elsewhere and is periodically mirrored
        from the external location into Launchpad.
        """)

    IMPORTED = DBItem(3, """
        Imported

        Branches that have been converted from some other revision
        control system into bzr and are made available through Launchpad.
        """)

    REMOTE = DBItem(4, """
        Remote

        Registered in Launchpad with an external location,
        but is not to be mirrored, nor available through Launchpad.
        """)


class UICreatableBranchType(EnumeratedType):
    """The types of branches that can be created through the web UI."""
    use_template(BranchType, exclude='IMPORTED')


class BranchLifecycleStatusFilter(EnumeratedType):
    """Branch Lifecycle Status Filter

    Used to populate the branch lifecycle status filter widget.
    UI only.
    """
    use_template(BranchLifecycleStatus)

    sort_order = (
        'CURRENT', 'ALL', 'EXPERIMENTAL', 'DEVELOPMENT', 'MATURE',
        'MERGED', 'ABANDONED')

    CURRENT = Item("""
        Any active status

        Show the currently active branches.
        """)

    ALL = Item("""
        Any status

        Show all the branches.
        """)


class BranchMergeProposalStatus(DBEnumeratedType):
    """Branch Merge Proposal Status

    The current state of a proposal to merge.
    """

    WORK_IN_PROGRESS = DBItem(1, """
        Work in progress

        The source branch is actively being worked on.
        """)

    NEEDS_REVIEW = DBItem(2, """
        Needs review

        A review of the changes has been requested.
        """)

    CODE_APPROVED = DBItem(3, """
        Approved

        The changes have been approved for merging.
        """)

    REJECTED = DBItem(4, """
        Rejected

        The changes have been rejected and will not be merged in their
        current state.
        """)

    MERGED = DBItem(5, """
        Merged

        The changes from the source branch were merged into the target
        branch.
        """)

    MERGE_FAILED = DBItem(6, """
        Code failed to merge

        The changes from the source branch failed to merge into the
        target branch for some reason.
        """)

    QUEUED = DBItem(7, """
        Queued

        The changes from the source branch are queued to be merged into the
        target branch.
        """)

    SUPERSEDED = DBItem(10, """
        Superseded

        This proposal has been superseded by anther proposal to merge.
        """)


class BranchSubscriptionDiffSize(DBEnumeratedType):
    """Branch Subscription Diff Size

    When getting branch revision notifications, the person can set a size
    limit of the diff to send out. If the generated diff is greater than
    the specified number of lines, then it is omitted from the email.
    This enumerated type defines the number of lines as a choice
    so we can sensibly limit the user to a number of size choices.
    """

    NODIFF = DBItem(0, """
        Don't send diffs

        Don't send generated diffs with the revision notifications.
        """)

    HALFKLINES = DBItem(500, """
        500 lines

        Limit the generated diff to 500 lines.
        """)

    ONEKLINES  = DBItem(1000, """
        1000 lines

        Limit the generated diff to 1000 lines.
        """)

    FIVEKLINES = DBItem(5000, """
        5000 lines

        Limit the generated diff to 5000 lines.
        """)

    WHOLEDIFF  = DBItem(-1, """
        Send entire diff

        Don't limit the size of the diff.
        """)


class BranchSubscriptionNotificationLevel(DBEnumeratedType):
    """Branch Subscription Notification Level

    The notification level is used to control the amount and content
    of the email notifications send with respect to modifications
    to branches whether it be to branch attributes in the UI, or
    to the contents of the branch found by the branch scanner.
    """

    NOEMAIL = DBItem(0, """
        No email

        Do not send any email about changes to this branch.
        """)

    ATTRIBUTEONLY = DBItem(1, """
        Branch attribute notifications only

        Only send notifications for branch attribute changes such
        as name, description and whiteboard.
        """)

    DIFFSONLY = DBItem(2, """
        Branch revision notifications only

        Only send notifications about new revisions added to this
        branch.
        """)

    FULL = DBItem(3, """
        Branch attribute and revision notifications

        Send notifications for both branch attribute updates
        and new revisions added to the branch.
        """)


class CodeReviewNotificationLevel(DBEnumeratedType):
    """Code Review Notification Level

    The notification level is used to control the amount and content
    of the email notifications send with respect to code reviews related
    to this branch.
    """

    NOEMAIL = DBItem(0, """
        No email

        Do not send any email about code review for this branch.
        """)

    STATUS = DBItem(1, """
        Status changes only

        Send email when votes are cast or status is changed.
        """)

    FULL = DBItem(2, """
        Email about all changes

        Send email about any code review activity for this branch.
        """)


class BranchVisibilityRule(DBEnumeratedType):
    """Branch Visibility Rules for defining branch visibility policy."""

    PUBLIC = DBItem(1, """
        Public

        Branches are public by default.
        """)

    PRIVATE = DBItem(2, """
        Private

        Branches are private by default.
        """)

    PRIVATE_ONLY = DBItem(3, """
        Private only

        Branches are private by default. Branch owners are not able
        to change the visibility of the branches to public.
        """)

    FORBIDDEN = DBItem(4, """
        Forbidden

        Users are not able to create branches in the context.
        """)


class TeamBranchVisibilityRule(EnumeratedType):
    """The valid policy rules for teams."""
    use_template(BranchVisibilityRule, exclude='FORBIDDEN')


class RevisionControlSystems(DBEnumeratedType):
    """Revision Control Systems

    Bazaar brings code from a variety of upstream revision control
    systems into bzr. This schema documents the known and supported
    revision control systems.
    """

    CVS = DBItem(1, """
        Concurrent Versions System

        Imports from CVS via CSCVS.
        """)

    SVN = DBItem(2, """
        Subversion

        Imports from SVN using CSCVS.
        """)

    BZR_SVN = DBItem(3, """
        Subversion via bzr-svn

        Imports from SVN using bzr-svn.
        """)

    GIT = DBItem(4, """
        Git

        Imports from Git using bzr-git.
        """)


class CodeImportReviewStatus(DBEnumeratedType):
    """CodeImport review status.

    Before a code import is performed, it is reviewed. Only reviewed imports
    are processed.
    """

    NEW = DBItem(1, """Pending Review

        This code import request has recently been filed and has not
        been reviewed yet.
        """)

    INVALID = DBItem(10, """Invalid

        This code import will not be processed.
        """)

    REVIEWED = DBItem(20, """Reviewed

        This code import has been approved and will be processed.
        """)

    SUSPENDED = DBItem(30, """Suspended

        This code import has been approved, but it has been suspended
        and is not processed.""")

    FAILING = DBItem(40, """Failing

        The code import is failing for some reason and is no longer being
        attempted.""")
