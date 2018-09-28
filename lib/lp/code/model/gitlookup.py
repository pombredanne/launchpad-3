# Copyright 2015-2018 Canonical Ltd.  This software is licensed under the
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
    adapter,
    getUtility,
    queryMultiAdapter,
    )
from zope.interface import implementer

from lp.app.errors import NameLookupFailed
from lp.app.validators.name import valid_name
from lp.code.errors import (
    InvalidNamespace,
    NoSuchGitRepository,
    )
from lp.code.interfaces.gitlookup import (
    IGitLookup,
    IGitTraversable,
    IGitTraverser,
    )
from lp.code.interfaces.gitnamespace import IGitNamespaceSet
from lp.code.interfaces.gitrepository import IGitRepositorySet
from lp.code.interfaces.hasgitrepositories import IHasGitRepositories
from lp.code.model.gitrepository import GitRepository
from lp.registry.errors import NoSuchSourcePackageName
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage,
    )
from lp.registry.interfaces.person import (
    IPerson,
    IPersonSet,
    NoSuchPerson,
    )
from lp.registry.interfaces.pillar import IPillarNameSet
from lp.registry.interfaces.product import (
    InvalidProductName,
    IProduct,
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


@implementer(IGitTraversable)
class RootGitTraversable:
    """Root traversable for Git repository objects.

    Corresponds to '/' in the path.  From here, you can traverse to a
    project or a distribution, optionally with a person context as well.
    """

    # Marker for references to Git URL layouts: ##GITNAMESPACE##
    def traverse(self, owner, name, segments):
        """See `IGitTraversable`.

        :raises InvalidProductName: If 'name' is not a valid name.
        :raises NoSuchPerson: If 'name' begins with a '~', but the remainder
            doesn't match an existing person.
        :raises NoSuchProduct: If 'name' doesn't match an existing pillar.
        :return: A tuple of (`IPerson`, `IPillar`, None).
        """
        assert owner is None
        if name.startswith("~"):
            owner_name = name[1:]
            owner = getUtility(IPersonSet).getByName(owner_name)
            if owner is None:
                raise NoSuchPerson(owner_name)
            return owner, owner, None
        else:
            if not valid_name(name):
                raise InvalidProductName(name)
            pillar = getUtility(IPillarNameSet).getByName(name)
            if pillar is None:
                # Actually, the pillar is no such *anything*.
                raise NoSuchProduct(name)
            return owner, pillar, None


class _BaseGitTraversable:
    """Base class for traversable implementations."""

    def __init__(self, context):
        self.context = context

    # Marker for references to Git URL layouts: ##GITNAMESPACE##
    def traverse(self, owner, name, segments):
        """See `IGitTraversable`.

        :raises InvalidNamespace: If 'name' is not '+git', or there is no
            owner, or there are no further segments.
        :raises NoSuchGitRepository: If the segment after '+git' doesn't
            match an existing Git repository.
        :return: A tuple of (`IPerson`, `IHasGitRepositories`,
            `IGitRepository`).
        """
        if owner is None or name != "+git":
            raise InvalidNamespace("/".join(segments.traversed))
        try:
            repository_name = next(segments)
        except StopIteration:
            raise InvalidNamespace("/".join(segments.traversed))
        repository = self.getNamespace(owner).getByName(repository_name)
        if repository is None:
            raise NoSuchGitRepository(repository_name)
        return owner, self.context, repository


@adapter(IProduct)
@implementer(IGitTraversable)
class ProjectGitTraversable(_BaseGitTraversable):
    """Git repository traversable for projects.

    From here, you can traverse to a named project repository.
    """

    def getNamespace(self, owner):
        return getUtility(IGitNamespaceSet).get(owner, project=self.context)


@adapter(IDistribution)
@implementer(IGitTraversable)
class DistributionGitTraversable(_BaseGitTraversable):
    """Git repository traversable for distributions.

    From here, you can traverse to a distribution source package.
    """

    # Marker for references to Git URL layouts: ##GITNAMESPACE##
    def traverse(self, owner, name, segments):
        """See `IGitTraversable`.

        :raises InvalidNamespace: If 'name' is not '+source' or there are no
            further segments.
        :raises NoSuchSourcePackageName: If the segment after '+source'
            doesn't match an existing source package name.
        :return: A tuple of (`IPerson`, `IDistributionSourcePackage`, None).
        """
        # Distributions don't support named repositories themselves, so
        # ignore the base traverse method.
        if name != "+source":
            raise InvalidNamespace("/".join(segments.traversed))
        try:
            spn_name = next(segments)
        except StopIteration:
            raise InvalidNamespace("/".join(segments.traversed))
        distro_source_package = self.context.getSourcePackage(spn_name)
        if distro_source_package is None:
            raise NoSuchSourcePackageName(spn_name)
        return owner, distro_source_package, None


@adapter(IDistributionSourcePackage)
@implementer(IGitTraversable)
class DistributionSourcePackageGitTraversable(_BaseGitTraversable):
    """Git repository traversable for distribution source packages.

    From here, you can traverse to a named package repository.
    """

    def getNamespace(self, owner):
        return getUtility(IGitNamespaceSet).get(
            owner, distribution=self.context.distribution,
            sourcepackagename=self.context.sourcepackagename)


@adapter(IPerson)
@implementer(IGitTraversable)
class PersonGitTraversable(_BaseGitTraversable):
    """Git repository traversable for people.

    From here, you can traverse to a named personal repository, or to a
    project or a distribution with a person context.
    """

    def getNamespace(self, owner):
        return getUtility(IGitNamespaceSet).get(owner)

    # Marker for references to Git URL layouts: ##GITNAMESPACE##
    def traverse(self, owner, name, segments):
        """See `IGitTraversable`.

        :raises InvalidNamespace: If 'name' is '+git' and there are no
            further segments.
        :raises InvalidProductName: If 'name' is not '+git' and is not a
            valid name.
        :raises NoSuchGitRepository: If the segment after '+git' doesn't
            match an existing Git repository.
        :raises NoSuchProduct: If 'name' is not '+git' and doesn't match an
            existing pillar.
        :return: A tuple of (`IPerson`, `IHasGitRepositories`,
            `IGitRepository`).
        """
        if name == "+git":
            return super(PersonGitTraversable, self).traverse(
                owner, name, segments)
        else:
            if not valid_name(name):
                raise InvalidProductName(name)
            pillar = getUtility(IPillarNameSet).getByName(name)
            if pillar is None:
                # Actually, the pillar is no such *anything*.
                raise NoSuchProduct(name)
            return owner, pillar, None


class SegmentIterator:
    """An iterator that remembers the elements it has traversed."""

    def __init__(self, iterator):
        self._iterator = iterator
        self.traversed = []

    def next(self):
        segment = next(self._iterator)
        if not isinstance(segment, unicode):
            segment = segment.decode("US-ASCII")
        self.traversed.append(segment)
        return segment


@implementer(IGitTraverser)
class GitTraverser:
    """Utility for traversing to objects that can have Git repositories."""

    def traverse(self, segments, owner=None):
        """See `IGitTraverser`."""
        repository = None
        if owner is None:
            target = None
            traversable = RootGitTraversable()
        else:
            target = owner
            traversable = adapt(owner, IGitTraversable)
        trailing = None
        segments_iter = SegmentIterator(segments)
        while traversable is not None:
            try:
                name = next(segments_iter)
            except StopIteration:
                break
            try:
                owner, target, repository = traversable.traverse(
                    owner, name, segments_iter)
            except InvalidNamespace:
                if target is not None or repository is not None:
                    # We have some information, so the rest may consist of
                    # trailing path information.
                    trailing = name
                    break
            if repository is not None:
                break
            traversable = adapt(target, IGitTraversable)
        if target is None or not IHasGitRepositories.providedBy(target):
            raise InvalidNamespace("/".join(segments_iter.traversed))
        return owner, target, repository, trailing

    def traverse_path(self, path):
        """See `IGitTraverser`."""
        segments = iter(path.split("/"))
        owner, target, repository, trailing = self.traverse(segments)
        if trailing or list(segments):
            raise InvalidNamespace(path)
        return owner, target, repository


@implementer(IGitLookup)
class GitLookup:
    """Utility for looking up Git repositories."""

    def get(self, repository_id, default=None):
        """See `IGitLookup`."""
        repository = IStore(GitRepository).get(GitRepository, repository_id)
        if repository is None:
            return default
        return repository

    def getByHostingPath(self, path):
        """See `IGitLookup`."""
        # This may need to change later to improve support for sharding.
        # See also `IGitRepository.getInternalPath`.
        try:
            repository_id = int(path)
        except ValueError:
            return None
        return self.get(repository_id)

    @staticmethod
    def uriToPath(uri):
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

        path = self.uriToPath(uri)
        if path is None:
            return None
        path, extra_path = self.getByPath(path)
        if extra_path:
            return None
        return path

    def getByUniqueName(self, unique_name):
        """See `IGitLookup`."""
        try:
            if unique_name.startswith("~"):
                traverser = getUtility(IGitTraverser)
                segments = iter(unique_name.split("/"))
                _, _, repository, trailing = traverser.traverse(segments)
                if repository is None or trailing or list(segments):
                    raise InvalidNamespace(unique_name)
                return repository
        except (InvalidNamespace, InvalidProductName, NameLookupFailed):
            pass
        return None

    def getByPath(self, path):
        """See `IGitLookup`."""
        traverser = getUtility(IGitTraverser)
        segments = iter(path.split("/"))
        try:
            owner, target, repository, trailing = traverser.traverse(segments)
        except (InvalidNamespace, InvalidProductName, NameLookupFailed):
            return None, None
        if repository is None:
            if IPerson.providedBy(target):
                return None, None
            repository_set = getUtility(IGitRepositorySet)
            if owner is None:
                repository = repository_set.getDefaultRepository(target)
            else:
                repository = repository_set.getDefaultRepositoryForOwner(
                    owner, target)
        trailing_segments = list(segments)
        if trailing:
            trailing_segments.insert(0, trailing)
        return repository, "/".join(trailing_segments)
