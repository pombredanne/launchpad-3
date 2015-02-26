# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Database implementation of the Git repository lookup utility."""

__metaclass__ = type
# This module doesn't export anything. If you want to look up Git
# repositories by name, then get the IGitLookup utility.
__all__ = []

from lazr.uri import (
    InvalidURIError,
    URI,
    )
from zope.component import (
    adapts,
    getUtility,
    queryMultiAdapter,
    )
from zope.interface import implements

from lp.app.errors import NameLookupFailed
from lp.app.validators.name import valid_name
from lp.code.errors import InvalidNamespace
from lp.code.interfaces.gitlookup import (
    IDefaultGitTraversable,
    IDefaultGitTraverser,
    IGitLookup,
    )
from lp.code.interfaces.gitnamespace import IGitNamespaceSet
from lp.code.interfaces.gitrepository import IGitRepositorySet
from lp.code.interfaces.hasgitrepositories import IHasGitRepositories
from lp.code.model.gitrepository import GitRepository
from lp.registry.errors import NoSuchSourcePackageName
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.person import (
    IPersonSet,
    NoSuchPerson,
    )
from lp.registry.interfaces.pillar import IPillarNameSet
from lp.registry.interfaces.product import (
    InvalidProductName,
    NoSuchProduct,
    )
from lp.services.config import config
from lp.services.database.interfaces import IStore


def adapt(obj, interface):
    """Adapt 'obj' to 'interface', using multi-adapters if necessary."""
    required = interface(obj, None)
    if required is not None:
        return required
    try:
        return queryMultiAdapter(obj, interface)
    except TypeError:
        return None


class RootGitTraversable:
    """Root traversable for default Git repository objects.

    Corresponds to '/' in the path.  From here, you can traverse to a
    distribution or a project, optionally with a person context as well.
    """

    implements(IDefaultGitTraversable)

    # Marker for references to Git URL layouts: ##GITNAMESPACE##
    def traverse(self, owner, name, segments):
        """See `IDefaultGitTraversable`.

        :raise InvalidNamespace: If 'name' begins with a '~', but there are
            no further segments.
        :raise InvalidProductName: If 'name' is not a valid name.
        :raise NoSuchPerson: If 'name' begins with a '~', but the remainder
            doesn't match an existing person.
        :raise NoSuchProduct: If 'name' doesn't match an existing pillar.
        :return: A tuple of (`IPerson`, `IPillar`).
        """
        assert owner is None
        if name.startswith("~"):
            if not segments:
                raise InvalidNamespace(name)
            owner_name = name[1:]
            owner = getUtility(IPersonSet).getByName(owner_name)
            if owner is None:
                raise NoSuchPerson(owner_name)
            name = segments.pop(0)
        if not valid_name(name):
            raise InvalidProductName(name)
        pillar = getUtility(IPillarNameSet).getByName(name)
        if pillar is None:
            # Actually, the pillar is no such *anything*.
            raise NoSuchProduct(name)
        return owner, pillar


class _BaseGitTraversable:
    """Base class for traversable implementations.

    This just defines a very simple constructor.
    """

    def __init__(self, context):
        self.context = context


class DistributionGitTraversable(_BaseGitTraversable):
    """Default Git repository traversable for distributions.

    From here, you can traverse to a distribution source package.
    """

    adapts(IDistribution)
    implements(IDefaultGitTraversable)

    # Marker for references to Git URL layouts: ##GITNAMESPACE##
    def traverse(self, owner, name, segments):
        """See `IDefaultGitTraversable`.

        :raise InvalidNamespace: If 'name' is not '+source' or there are no
            further segments.
        :raise NoSuchSourcePackageName: If the segment after '+source'
            doesn't match an existing source package name.
        :return: `IDistributionSourcePackage`.
        """
        if name != "+source" or not segments:
            raise InvalidNamespace(name)
        spn_name = segments.pop(0)
        distro_source_package = self.context.getSourcePackage(spn_name)
        if distro_source_package is None:
            raise NoSuchSourcePackageName(spn_name)
        return owner, distro_source_package


class DefaultGitTraverser:
    """Utility for traversing to objects that can have default repositories."""

    implements(IDefaultGitTraverser)

    def traverse(self, path):
        """See `IDefaultGitTraverser`."""
        segments = path.split("/")
        owner = None
        target = None
        traversable = RootGitTraversable()
        while segments:
            name = segments.pop(0)
            owner, target = traversable.traverse(owner, name, segments)
            traversable = adapt(target, IDefaultGitTraversable)
            if traversable is None:
                break
        if (segments or target is None or
            not IHasGitRepositories.providedBy(target)):
            raise InvalidNamespace(path)
        return owner, target


class GitLookup:
    """Utility for looking up Git repositories."""

    implements(IGitLookup)

    def get(self, repository_id, default=None):
        """See `IGitLookup`."""
        repository = IStore(GitRepository).get(GitRepository, repository_id)
        if repository is None:
            return default
        return repository

    @staticmethod
    def uriToHostingPath(uri):
        """See `IGitLookup`."""
        schemes = ('git', 'git+ssh', 'https', 'ssh')
        codehosting_host = URI(config.codehosting.git_anon_root).host
        if ((uri.scheme in schemes and uri.host == codehosting_host) or
            (uri.scheme == "lp" and uri.host is None)):
            return uri.path.lstrip("/")
        else:
            return None

    def getByUrl(self, url):
        """See `IGitLookup`."""
        if url is None:
            return None
        url = url.rstrip("/")
        try:
            uri = URI(url)
        except InvalidURIError:
            return None

        path = self.uriToHostingPath(uri)
        if path is None:
            return None
        return self.getByPath(path)

    def getByUniqueName(self, unique_name):
        """See `IGitLookup`."""
        try:
            if unique_name.startswith("~"):
                path = unique_name.lstrip("~")
                namespace_set = getUtility(IGitNamespaceSet)
                segments = iter(path.split("/"))
                repository = namespace_set.traverse(segments)
                if list(segments):
                    raise InvalidNamespace(path)
                return repository
        except (InvalidNamespace, NameLookupFailed):
            pass
        return None

    def getByPath(self, path):
        """See `IGitLookup`."""
        # Try parsing as a unique name.
        repository = self.getByUniqueName(path)
        if repository is not None:
            return repository

        # Try parsing as a shortcut.
        repository_set = getUtility(IGitRepositorySet)
        try:
            owner, target = getUtility(IDefaultGitTraverser).traverse(path)
        except (InvalidNamespace, InvalidProductName, NameLookupFailed):
            return None
        if owner is None:
            return repository_set.getDefaultRepository(target)
        else:
            return repository_set.getDefaultRepositoryForOwner(owner, target)
