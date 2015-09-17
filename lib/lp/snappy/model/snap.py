# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'Snap',
    ]

import pytz
from storm.exceptions import IntegrityError
from storm.locals import (
    Bool,
    DateTime,
    Desc,
    Int,
    Not,
    Reference,
    Store,
    Storm,
    Unicode,
    )
from zope.component import getUtility
from zope.interface import implementer
from zope.security.proxy import removeSecurityProxy

from lp.buildmaster.enums import BuildStatus
from lp.buildmaster.interfaces.processor import IProcessorSet
from lp.buildmaster.model.processor import Processor
from lp.code.interfaces.branch import IBranch
from lp.code.interfaces.branchcollection import (
    IAllBranches,
    IBranchCollection,
    )
from lp.code.interfaces.gitcollection import (
    IAllGitRepositories,
    IGitCollection,
    )
from lp.code.interfaces.gitref import IGitRef
from lp.code.interfaces.gitrepository import IGitRepository
from lp.code.model.branch import Branch
from lp.code.model.branchcollection import GenericBranchCollection
from lp.code.model.gitcollection import GenericGitCollection
from lp.code.model.gitref import GitRef
from lp.code.model.gitrepository import GitRepository
from lp.registry.interfaces.person import (
    IPerson,
    IPersonSet,
    )
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.role import IHasOwner
from lp.services.database.bulk import (
    load,
    load_related,
    )
from lp.services.database.constants import (
    DEFAULT,
    UTC_NOW,
    )
from lp.services.database.interfaces import (
    IMasterStore,
    IStore,
    )
from lp.services.database.stormexpr import (
    Greatest,
    NullsLast,
    )
from lp.services.features import getFeatureFlag
from lp.services.webapp.interfaces import ILaunchBag
from lp.snappy.interfaces.snap import (
    BadSnapSearchContext,
    CannotDeleteSnap,
    DuplicateSnapName,
    ISnap,
    ISnapSet,
    SNAP_FEATURE_FLAG,
    SnapBuildAlreadyPending,
    SnapBuildArchiveOwnerMismatch,
    SnapBuildDisallowedArchitecture,
    SnapFeatureDisabled,
    SnapNotOwner,
    NoSourceForSnap,
    NoSuchSnap,
    )
from lp.snappy.interfaces.snapbuild import ISnapBuildSet
from lp.snappy.model.snapbuild import SnapBuild
from lp.soyuz.interfaces.archive import ArchiveDisabled
from lp.soyuz.model.archive import (
    Archive,
    get_enabled_archive_filter,
    )


def snap_modified(snap, event):
    """Update the date_last_modified property when a Snap is modified.

    This method is registered as a subscriber to `IObjectModifiedEvent`
    events on snap packages.
    """
    removeSecurityProxy(snap).date_last_modified = UTC_NOW


@implementer(ISnap, IHasOwner)
class Snap(Storm):
    """See `ISnap`."""

    __storm_table__ = 'Snap'

    id = Int(primary=True)

    date_created = DateTime(
        name='date_created', tzinfo=pytz.UTC, allow_none=False)
    date_last_modified = DateTime(
        name='date_last_modified', tzinfo=pytz.UTC, allow_none=False)

    registrant_id = Int(name='registrant', allow_none=False)
    registrant = Reference(registrant_id, 'Person.id')

    owner_id = Int(name='owner', allow_none=False)
    owner = Reference(owner_id, 'Person.id')

    distro_series_id = Int(name='distro_series', allow_none=False)
    distro_series = Reference(distro_series_id, 'DistroSeries.id')

    name = Unicode(name='name', allow_none=False)

    description = Unicode(name='description', allow_none=True)

    branch_id = Int(name='branch', allow_none=True)
    branch = Reference(branch_id, 'Branch.id')

    git_repository_id = Int(name='git_repository', allow_none=True)
    git_repository = Reference(git_repository_id, 'GitRepository.id')

    git_path = Unicode(name='git_path', allow_none=True)

    require_virtualized = Bool(name='require_virtualized')

    def __init__(self, registrant, owner, distro_series, name,
                 description=None, branch=None, git_ref=None,
                 require_virtualized=True, date_created=DEFAULT):
        """Construct a `Snap`."""
        if not getFeatureFlag(SNAP_FEATURE_FLAG):
            raise SnapFeatureDisabled

        super(Snap, self).__init__()
        self.registrant = registrant
        self.owner = owner
        self.distro_series = distro_series
        self.name = name
        self.description = description
        self.branch = branch
        self.git_ref = git_ref
        self.require_virtualized = require_virtualized
        self.date_created = date_created
        self.date_last_modified = date_created

    @property
    def git_ref(self):
        """See `ISnap`."""
        if self.git_repository is not None:
            return self.git_repository.getRefByPath(self.git_path)
        else:
            return None

    @git_ref.setter
    def git_ref(self, value):
        """See `ISnap`."""
        if value is not None:
            self.git_repository = value.repository
            self.git_path = value.path
        else:
            self.git_repository = None
            self.git_path = None

    @property
    def source(self):
        if self.branch is not None:
            return self.branch
        elif self.git_ref is not None:
            return self.git_ref
        else:
            return None

    def _getProcessors(self):
        return list(Store.of(self).find(
            Processor,
            Processor.id == SnapArch.processor_id,
            SnapArch.snap == self))

    def setProcessors(self, processors):
        """See `ISnap`."""
        enablements = dict(Store.of(self).find(
            (Processor, SnapArch),
            Processor.id == SnapArch.processor_id,
            SnapArch.snap == self))
        for proc in enablements:
            if proc not in processors:
                Store.of(self).remove(enablements[proc])
        for proc in processors:
            if proc not in self.processors:
                snaparch = SnapArch()
                snaparch.snap = self
                snaparch.processor = proc
                Store.of(self).add(snaparch)

    processors = property(_getProcessors, setProcessors)

    def _getAllowedArchitectures(self):
        """Return all distroarchseries that this package can build for.

        :return: Sequence of `IDistroArchSeries` instances.
        """
        return [
            das for das in self.distro_series.buildable_architectures
            if (
                das.enabled
                and das.processor in self.processors
                and (
                    das.processor.supports_virtualized
                    or not self.require_virtualized))]

    def requestBuild(self, requester, archive, distro_arch_series, pocket):
        """See `ISnap`."""
        if not requester.inTeam(self.owner):
            raise SnapNotOwner(
                "%s cannot create snap package builds owned by %s." %
                (requester.displayname, self.owner.displayname))
        if not archive.enabled:
            raise ArchiveDisabled(archive.displayname)
        if distro_arch_series not in self._getAllowedArchitectures():
            raise SnapBuildDisallowedArchitecture(distro_arch_series)
        if archive.private and self.owner != archive.owner:
            # See rationale in `SnapBuildArchiveOwnerMismatch` docstring.
            raise SnapBuildArchiveOwnerMismatch()

        pending = IStore(self).find(
            SnapBuild,
            SnapBuild.snap_id == self.id,
            SnapBuild.archive_id == archive.id,
            SnapBuild.distro_arch_series_id == distro_arch_series.id,
            SnapBuild.pocket == pocket,
            SnapBuild.status == BuildStatus.NEEDSBUILD)
        if pending.any() is not None:
            raise SnapBuildAlreadyPending

        build = getUtility(ISnapBuildSet).new(
            requester, self, archive, distro_arch_series, pocket)
        build.queueBuild()
        return build

    def _getBuilds(self, filter_term, order_by):
        """The actual query to get the builds."""
        query_args = [
            SnapBuild.snap == self,
            SnapBuild.archive_id == Archive.id,
            Archive._enabled == True,
            get_enabled_archive_filter(
                getUtility(ILaunchBag).user, include_public=True,
                include_subscribed=True)
            ]
        if filter_term is not None:
            query_args.append(filter_term)
        result = Store.of(self).find(SnapBuild, *query_args)
        result.order_by(order_by)
        return result

    @property
    def builds(self):
        """See `ISnap`."""
        order_by = (
            NullsLast(Desc(Greatest(
                SnapBuild.date_started,
                SnapBuild.date_finished))),
            Desc(SnapBuild.date_created),
            Desc(SnapBuild.id))
        return self._getBuilds(None, order_by)

    @property
    def _pending_states(self):
        """All the build states we consider pending (non-final)."""
        return [
            BuildStatus.NEEDSBUILD,
            BuildStatus.BUILDING,
            BuildStatus.UPLOADING,
            BuildStatus.CANCELLING,
            ]

    @property
    def completed_builds(self):
        """See `ISnap`."""
        filter_term = (Not(SnapBuild.status.is_in(self._pending_states)))
        order_by = (
            NullsLast(Desc(Greatest(
                SnapBuild.date_started,
                SnapBuild.date_finished))),
            Desc(SnapBuild.id))
        return self._getBuilds(filter_term, order_by)

    @property
    def pending_builds(self):
        """See `ISnap`."""
        filter_term = (SnapBuild.status.is_in(self._pending_states))
        # We want to order by date_created but this is the same as ordering
        # by id (since id increases monotonically) and is less expensive.
        order_by = Desc(SnapBuild.id)
        return self._getBuilds(filter_term, order_by)

    def destroySelf(self):
        """See `ISnap`."""
        if not self.builds.is_empty():
            raise CannotDeleteSnap("Cannot delete a snap package with builds.")
        store = IStore(Snap)
        store.find(SnapArch, SnapArch.snap == self).remove()
        store.remove(self)


class SnapArch(Storm):
    """Link table to back `Snap.processors`."""

    __storm_table__ = 'SnapArch'
    __storm_primary__ = ('snap_id', 'processor_id')

    snap_id = Int(name='snap', allow_none=False)
    snap = Reference(snap_id, 'Snap.id')

    processor_id = Int(name='processor', allow_none=False)
    processor = Reference(processor_id, 'Processor.id')


@implementer(ISnapSet)
class SnapSet:
    """See `ISnapSet`."""

    def new(self, registrant, owner, distro_series, name, description=None,
            branch=None, git_ref=None, require_virtualized=True,
            processors=None, date_created=DEFAULT):
        """See `ISnapSet`."""
        if not registrant.inTeam(owner):
            if owner.is_team:
                raise SnapNotOwner(
                    "%s is not a member of %s." %
                    (registrant.displayname, owner.displayname))
            else:
                raise SnapNotOwner(
                    "%s cannot create snap packages owned by %s." %
                    (registrant.displayname, owner.displayname))

        if branch is None and git_ref is None:
            raise NoSourceForSnap

        store = IMasterStore(Snap)
        snap = Snap(
            registrant, owner, distro_series, name, description=description,
            branch=branch, git_ref=git_ref,
            require_virtualized=require_virtualized, date_created=date_created)
        store.add(snap)

        try:
            store.flush()
        except IntegrityError:
            raise DuplicateSnapName

        if processors is None:
            processors = [
                p for p in getUtility(IProcessorSet).getAll()
                if p.build_by_default]
        snap.setProcessors(processors)

        return snap

    def _getByName(self, owner, name):
        return IStore(Snap).find(
            Snap, Snap.owner == owner, Snap.name == name).one()

    def exists(self, owner, name):
        """See `ISnapSet`."""
        return self._getByName(owner, name) is not None

    def getByName(self, owner, name):
        """See `ISnapSet`."""
        snap = self._getByName(owner, name)
        if snap is None:
            raise NoSuchSnap(name)
        return snap

    def _getSnapsFromCollection(self, collection, owner=None):
        if IBranchCollection.providedBy(collection):
            id_column = Snap.branch_id
            ids = collection.getBranchIds()
        else:
            id_column = Snap.git_repository_id
            ids = collection.getRepositoryIds()
        expressions = [id_column.is_in(ids._get_select())]
        if owner is not None:
            expressions.append(Snap.owner == owner)
        return IStore(Snap).find(Snap, *expressions)

    def findByOwner(self, owner):
        """See `ISnapSet`."""
        return IStore(Snap).find(Snap, Snap.owner == owner)

    def findByPerson(self, person, visible_by_user=None):
        """See `ISnapSet`."""
        def _getSnaps(collection):
            collection = collection.visibleByUser(visible_by_user)
            owned = self._getSnapsFromCollection(collection.ownedBy(person))
            packaged = self._getSnapsFromCollection(collection, owner=person)
            return owned.union(packaged)

        bzr_collection = removeSecurityProxy(getUtility(IAllBranches))
        git_collection = removeSecurityProxy(getUtility(IAllGitRepositories))
        return _getSnaps(bzr_collection).union(_getSnaps(git_collection))

    def findByProject(self, project, visible_by_user=None):
        """See `ISnapSet`."""
        def _getSnaps(collection):
            return self._getSnapsFromCollection(
                collection.visibleByUser(visible_by_user))

        bzr_collection = removeSecurityProxy(IBranchCollection(project))
        git_collection = removeSecurityProxy(IGitCollection(project))
        return _getSnaps(bzr_collection).union(_getSnaps(git_collection))

    def findByBranch(self, branch):
        """See `ISnapSet`."""
        return IStore(Snap).find(Snap, Snap.branch == branch)

    def findByGitRepository(self, repository):
        """See `ISnapSet`."""
        return IStore(Snap).find(Snap, Snap.git_repository == repository)

    def findByGitRef(self, ref):
        """See `ISnapSet`."""
        return IStore(Snap).find(
            Snap,
            Snap.git_repository == ref.repository, Snap.git_path == ref.path)

    def findByContext(self, context, visible_by_user=None, order_by_date=True):
        if IPerson.providedBy(context):
            snaps = self.findByPerson(context, visible_by_user=visible_by_user)
        elif IProduct.providedBy(context):
            snaps = self.findByProject(
                context, visible_by_user=visible_by_user)
        # XXX cjwatson 2015-09-15: At the moment we can assume that if you
        # can see the source context then you can see the snap packages
        # based on it.  This will cease to be true if snap packages gain
        # privacy of their own.
        elif IBranch.providedBy(context):
            snaps = self.findByBranch(context)
        elif IGitRepository.providedBy(context):
            snaps = self.findByGitRepository(context)
        elif IGitRef.providedBy(context):
            snaps = self.findByGitRef(context)
        else:
            raise BadSnapSearchContext(context)
        if order_by_date:
            snaps.order_by(Desc(Snap.date_last_modified))
        return snaps

    def preloadDataForSnaps(self, snaps, user=None):
        """See `ISnapSet`."""
        snaps = [removeSecurityProxy(snap) for snap in snaps]

        branch_ids = set()
        git_ref_keys = set()
        person_ids = set()
        for snap in snaps:
            if snap.branch_id is not None:
                branch_ids.add(snap.branch_id)
            if snap.git_repository_id is not None:
                git_ref_keys.add((snap.git_repository_id, snap.git_path))
            person_ids.add(snap.registrant_id)
            person_ids.add(snap.owner_id)
        git_repository_ids = set(
            repository_id for repository_id, _ in git_ref_keys)

        branches = load_related(Branch, snaps, ["branch_id"])
        repositories = load_related(
            GitRepository, snaps, ["git_repository_id"])
        load(GitRef, git_ref_keys)
        # The stacked-on branches are used to check branch visibility.
        GenericBranchCollection.preloadVisibleStackedOnBranches(branches, user)
        GenericGitCollection.preloadVisibleRepositories(repositories, user)

        # Add branch/repository owners to the list of pre-loaded persons.
        # We need the target repository owner as well; unlike branches,
        # repository unique names aren't trigger-maintained.
        person_ids.update(
            branch.ownerID for branch in branches if branch.id in branch_ids)
        person_ids.update(
            repository.owner_id for repository in repositories
            if repository.id in git_repository_ids)

        list(getUtility(IPersonSet).getPrecachedPersonsFromIDs(
            person_ids, need_validity=True))

        if branches:
            GenericBranchCollection.preloadDataForBranches(branches)
        if repositories:
            GenericGitCollection.preloadDataForRepositories(repositories)

    def detachFromBranch(self, branch):
        """See `ISnapSet`."""
        self.findByBranch(branch).set(
            branch_id=None, date_last_modified=UTC_NOW)

    def detachFromGitRepository(self, repository):
        """See `ISnapSet`."""
        self.findByGitRepository(repository).set(
            git_repository_id=None, git_path=None, date_last_modified=UTC_NOW)

    def empty_list(self):
        """See `ISnapSet`."""
        return []
