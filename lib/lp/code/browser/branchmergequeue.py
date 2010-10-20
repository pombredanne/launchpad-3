# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""SourcePackageRecipe views."""

__metaclass__ = type

__all__ = [
    'BranchMergeQueueContextMenu',
    'BranchMergeQueueView',
    ]

from canonical.launchpad.webapp import ContextMenu, LaunchpadView
from lp.code.interfaces.branchmergequeue import IBranchMergeQueue


class BranchMergeQueueContextMenu(ContextMenu):
    """Context menu for sourcepackage recipes."""

    usedfor = IBranchMergeQueue

    facet = 'branches'

    links = ()


class BranchMergeQueueView(LaunchpadView):
    """Default view of a SourcePackageRecipe."""

    @property
    def page_title(self):
        return "%(queue_name)s queue owned by %(name)s's" % {
            'name': self.context.owner.displayname,
            'queue_name': self.context.name}

    label = page_title
