# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""View classes for Git repository listings."""

__metaclass__ = type

__all__ = [
    'PersonTargetGitListingView',
    'TargetGitListingView',
    ]

from zope.component import getUtility
from zope.interface import (
    implementer,
    Interface,
    )

from lp.app.enums import PRIVATE_INFORMATION_TYPES
from lp.code.browser.gitrepository import GitRefBatchNavigator
from lp.code.interfaces.branchcollection import IBranchCollection
from lp.code.interfaces.gitcollection import IGitCollection
from lp.code.interfaces.gitnamespace import (
    get_git_namespace,
    IGitNamespacePolicy,
    )
from lp.code.interfaces.gitrepository import IGitRepositorySet
from lp.registry.interfaces.persondistributionsourcepackage import (
    IPersonDistributionSourcePackage,
    )
from lp.registry.interfaces.personproduct import IPersonProduct
from lp.services.config import config
from lp.services.propertycache import cachedproperty
from lp.services.webapp.authorization import check_permission
from lp.services.webapp.batching import TableBatchNavigator
from lp.services.webapp.publisher import LaunchpadView


class IGitRepositoryBatchNavigator(Interface):
    pass


@implementer(IGitRepositoryBatchNavigator)
class GitRepositoryBatchNavigator(TableBatchNavigator):
    """Batch up Git repository listings."""

    variable_name_prefix = 'repo'

    def __init__(self, view, repo_collection):
        super(GitRepositoryBatchNavigator, self).__init__(
            repo_collection.getRepositories(
                eager_load=True, order_by_date=True),
            view.request, size=config.launchpad.branchlisting_batch_size)
        self.view = view
        self.column_count = 2


class BaseGitListingView(LaunchpadView):

    @property
    def target(self):
        raise NotImplementedError()

    @cachedproperty
    def default_git_repository(self):
        raise NotImplementedError()

    @property
    def repo_collection(self):
        return IGitCollection(self.context).visibleByUser(self.user)

    @property
    def show_bzr_link(self):
        collection = IBranchCollection(self.context)
        return not collection.visibleByUser(self.user).is_empty()

    def default_git_repository_branches(self):
        """All branches in the default Git repository, sorted for display."""
        return GitRefBatchNavigator(self, self.default_git_repository)

    @cachedproperty
    def default_information_type(self):
        """The default information type for new repos."""
        if self.user is None:
            return None
        namespace = get_git_namespace(self.target, self.user)
        policy = IGitNamespacePolicy(namespace)
        return policy.getDefaultInformationType(self.user)

    @property
    def default_information_type_title(self):
        """The title of the default information type for new branches."""
        information_type = self.default_information_type
        if information_type is None:
            return None
        return information_type.title

    @property
    def default_information_type_is_private(self):
        """The title of the default information type for new branches."""
        return self.default_information_type in PRIVATE_INFORMATION_TYPES

    @property
    def repos(self):
        return GitRepositoryBatchNavigator(self, self.repo_collection)

    @property
    def show_junk_directions(self):
        return self.user == self.context


class TargetGitListingView(BaseGitListingView):

    page_title = 'Git'

    @property
    def target(self):
        return self.context

    @cachedproperty
    def default_git_repository(self):
        repo = getUtility(IGitRepositorySet).getDefaultRepository(
            self.context)
        if repo is None:
            return None
        elif check_permission('launchpad.View', repo):
            return repo
        else:
            return None


class PersonTargetGitListingView(BaseGitListingView):

    page_title = 'Git'

    @property
    def label(self):
        return 'Git repositories for %s' % self.target.displayname

    @property
    def target(self):
        if IPersonProduct.providedBy(self.context):
            return self.context.product
        elif IPersonDistributionSourcePackage.providedBy(self.context):
            return self.context.distro_source_package
        else:
            raise Exception("Unknown context: %r" % self.context)

    @cachedproperty
    def default_git_repository(self):
        repo = getUtility(IGitRepositorySet).getDefaultRepositoryForOwner(
            self.context.person, self.target)
        if repo is None:
            return None
        elif check_permission('launchpad.View', repo):
            return repo
        else:
            return None


class PersonDistributionSourcePackageGitListingView(
        PersonTargetGitListingView):

    # PersonDistributionSourcePackage:+branches doesn't exist.
    show_bzr_link = False


class PlainGitListingView(BaseGitListingView):

    page_title = 'Git'
    target = None
    default_git_repository = None
