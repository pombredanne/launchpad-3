# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Git reference views."""

__metaclass__ = type

__all__ = [
    'GitRefNavigation',
    'GitRefView',
    ]

from lp.code.browser.branchmergeproposal import (
    latest_proposals_for_each_branch,
    )
from lp.code.interfaces.gitref import IGitRef
from lp.code.model.gitrepository import GitRepository
from lp.services.database.bulk import load_related
from lp.services.propertycache import cachedproperty
from lp.services.webapp import (
    LaunchpadView,
    Navigation,
    stepthrough,
    )
from lp.services.webapp.authorization import check_permission


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

    @property
    def show_merge_links(self):
        """Return whether or not merge proposal links should be shown.

        Merge proposal links should not be shown if there is only one
        reference in the entire target.
        """
        if not self.context.namespace.supports_merge_proposals:
            return False
        repositories = self.context.namespace.collection.getRepositories()
        if repositories.count() > 1:
            return True
        repository = repositories.one()
        if repository is None:
            return False
        return repository.refs.count() > 1

    @cachedproperty
    def landing_targets(self):
        """Return a filtered list of landing targets."""
        return latest_proposals_for_each_branch(self.context.landing_targets)

    @cachedproperty
    def landing_candidates(self):
        """Return a decorated list of landing candidates."""
        candidates = list(self.context.landing_candidates)
        load_related(
            GitRepository, candidates,
            ["source_git_repositoryID", "prerequisite_git_repositoryID"])
        return [proposal for proposal in candidates
                if check_permission("launchpad.View", proposal)]

    def _getBranchCountText(self, count):
        """Help to show user friendly text."""
        if count == 0:
            return 'No branches'
        elif count == 1:
            return '1 branch'
        else:
            return '%s branches' % count

    @cachedproperty
    def landing_candidate_count_text(self):
        return self._getBranchCountText(len(self.landing_candidates))

    @cachedproperty
    def dependent_landings(self):
        return [proposal for proposal in self.context.dependent_landings
                if check_permission("launchpad.View", proposal)]

    @cachedproperty
    def dependent_landing_count_text(self):
        return self._getBranchCountText(len(self.dependent_landings))
