# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Git reference views."""

__metaclass__ = type

__all__ = [
    'GitRefNavigation',
    'GitRefView',
    ]

from lp.code.interfaces.gitref import IGitRef
from lp.services.webapp import (
    LaunchpadView,
    Navigation,
    stepthrough,
    )


class GitRefNavigation(Navigation):

    usedfor = IGitRef

    @stepthrough("+merge")
    def traverse_merge_proposal(self, id):
        """Traverse to an `IBranchMergeProposal`."""
        try:
            id = int(id)
        except ValueError:
            # Not a number.
            return None
        for proposal in self.context.landing_targets:
            if proposal.id == id:
                return proposal


class GitRefView(LaunchpadView):

    @property
    def label(self):
        return self.context.display_name

    @property
    def tip_commit_info(self):
        return {
            "sha1": self.context.commit_sha1,
            "author": self.context.author,
            "author_date": self.context.author_date,
            "commit_message": self.context.commit_message,
            }
