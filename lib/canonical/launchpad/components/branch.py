# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Components related to branches."""

__metaclass__ = type

from zope.interface import implements

from canonical.config import config
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


def bazaar_identity(branch, associated_series, is_dev_focus):
    """Return the shortest lp: style branch identity."""
    use_series = None
    lp_prefix = config.codehosting.bzr_lp_prefix
    # XXX: TimPenhey 2008-05-06 bug=227602
    # Since at this stage the launchpad name resolution is not
    # authenticated, we can't resolve series branches that end
    # up pointing to private branches, so don't show short names
    # for the branch if it is private.

    # It is possible for +junk branches to be related to a product
    # series.  However we do not show the shorter name for these
    # branches as it would be giving extra authority to them.  When
    # the owner of these branches realises that they want other people
    # to be able to commit to them, the branches will need to have a
    # team owner.  When this happens, they will no longer be able to
    # stay as junk branches, and will need to be associated with a
    # product.  In this way +junk branches associated with product
    # series should be self limiting.  We are not looking to enforce
    # extra strictness in this case, but instead let it manage itself.
    if not branch.private and branch.product is not None:
        if is_dev_focus:
            return lp_prefix + branch.product.name

        for series in associated_series:
            if (use_series is None or
                series.datecreated > use_series.datecreated):
                use_series = series
    # If there is no series, use the prefix with the unique name.
    if use_series is None:
        return lp_prefix + branch.unique_name
    else:
        return "%(prefix)s%(product)s/%(series)s" % {
            'prefix': lp_prefix,
            'product': use_series.product.name,
            'series': use_series.name}
