# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Components related to branches."""

__metaclass__ = type

from zope.interface import implements

from canonical.launchpad.components import ObjectDelta
from canonical.launchpad.interfaces import IBranchDelta, IBranchMergeProposal
from canonical.launchpad.webapp import snapshot

# XXX: thumper 2006-12-20: This needs to be extended
# to cover bugs and specs linked and unlinked, as
# well as landing target when it is added to the UI

class BranchDelta:
    """See canonical.launchpad.interfaces.IBranchDelta."""
    implements(IBranchDelta)
    def __init__(self, branch, user,
                 name=None, title=None, summary=None, url=None,
                 whiteboard=None, lifecycle_status=None):
        self.branch = branch
        self.user = user

        self.name = name
        self.title = title
        self.summary = summary
        self.url = url
        self.whiteboard = whiteboard
        self.lifecycle_status = lifecycle_status

    @staticmethod
    def construct(old_branch, new_branch, user):
        """Return a BranchDelta instance that encapsulates the changes.

        This method is primarily used by event subscription code to
        determine what has changed during an SQLObjectModifiedEvent.
        """
        delta = ObjectDelta(old_branch, new_branch)
        delta.recordNewValues(("summary", "whiteboard"))
        delta.recordNewAndOld(("name", "lifecycle_status",
                               "title", "url"))
        # delta.record_list_added_and_removed()
        # XXX thumper 2006-12-21: Add in bugs and specs.
        if delta.changes:
            changes = delta.changes
            changes["branch"] = new_branch
            changes["user"] = user

            return BranchDelta(**changes)
        else:
            return None


class BranchMergeProposalDelta:
    """Represent changes made to a BranchMergeProposal."""

    delta_values = (
        'registrant', 'source_branch', 'target_branch', 'dependent_branch',
        'queue_status', 'queue_position',)
    new_values = ('commit_message', 'whiteboard',)
    interface = IBranchMergeProposal

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    @classmethod
    def construct(klass, old_merge_proposal, new_merge_proposal):
        """Return a new instance representing the differences.

        :param old_merge_proposal: A snapshot representing the merge
            proposal's previous state.
        :param new_merge_proposal: The merge proposal (not a snapshot).
        """
        delta = ObjectDelta(old_merge_proposal, new_merge_proposal)
        delta.recordNewValues(klass.new_values)
        delta.recordNewAndOld(klass.delta_values)
        if not delta.changes:
            return None
        return BranchMergeProposalDelta(**delta.changes)

    @classmethod
    def snapshot(klass, merge_proposal):
        """Return a snapshot suitable for use with construct.

        :param merge_proposal: The merge proposal to take a snapshot of.
        """
        names = klass.new_values + klass.delta_values
        return snapshot.Snapshot(merge_proposal, names=names)
