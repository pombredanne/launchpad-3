# Copyright 2015-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'Snap',
    ]

from datetime import (
    datetime,
    timedelta,
    )

import pytz
from storm.expr import (
    And,
    Desc,
    LeftJoin,
    Not,
    )
from storm.locals import (
    Bool,
    DateTime,
    Int,
    JSON,
    Reference,
    Store,
    Storm,
    Unicode,
    )
from zope.component import (
    getAdapter,
    getUtility,
    )
from zope.interface import implementer
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy

from lp.app.browser.tales import DateTimeFormatterAPI
from lp.app.enums import PRIVATE_INFORMATION_TYPES
from lp.app.interfaces.security import IAuthorization
from lp.buildmaster.enums import BuildStatus
from lp.buildmaster.interfaces.buildqueue import IBuildQueueSet
from lp.buildmaster.interfaces.processor import IProcessorSet
from lp.buildmaster.model.buildfarmjob import BuildFarmJob
from lp.buildmaster.model.buildqueue import BuildQueue
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
from lp.code.model.gitrepository import GitRepository
from lp.registry.enums import PersonVisibility
from lp.registry.interfaces.person import (
    IPerson,
    IPersonSet,
    )
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.role import (
    IHasOwner,
    IPersonRoles,
    )
from lp.services.config import config
from lp.services.database.bulk import load_related
from lp.services.database.constants import (
    DEFAULT,
    UTC_NOW,
    )
from lp.services.database.enumcol import DBEnum
from lp.services.database.interfaces import (
    IMasterStore,
    IStore,
    )
from lp.services.database.stormexpr import (
    Greatest,
    NullsLast,
    )
from lp.services.features import getFeatureFlag
from lp.services.librarian.model import (
    LibraryFileAlias,
    LibraryFileContent,
    )
from lp.services.webapp.interfaces import ILaunchBag
from lp.services.webhooks.interfaces import IWebhookSet
from lp.services.webhooks.model import WebhookTargetMixin
from lp.snappy.interfaces.snap import (
    BadSnapSearchContext,
    CannotModifySnapProcessor,
    CannotRequestAutoBuilds,
    DuplicateSnapName,
    ISnap,
    ISnapSet,
    NoSourceForSnap,
    NoSuchSnap,
    SNAP_PRIVATE_FEATURE_FLAG,
    SnapBuildAlreadyPending,
    SnapBuildArchiveOwnerMismatch,
    SnapBuildDisallowedArchitecture,
    SnapNotOwner,
    SnapPrivacyMismatch,
    SnapPrivateFeatureDisabled,
    )
from lp.snappy.interfaces.snapbuild import ISnapBuildSet
from lp.snappy.interfaces.snappyseries import ISnappyDistroSeriesSet
from lp.snappy.model.snapbuild import SnapBuild
from lp.soyuz.interfaces.archive import ArchiveDisabled
from lp.soyuz.model.archive import (
    Archive,
    get_enabled_archive_filter,
    )
from lp.soyuz.model.distroarchseries import DistroArchSeries


def snap_modified(snap, event):
    """Update the date_last_modified property when a Snap is modified.

    This method is registered as a subscriber to `IObjectModifiedEvent`
    events on snap packages.
    """
    removeSecurityProxy(snap).date_last_modified = UTC_NOW


@implementer(ISnap, IHasOwner)
class Snap(Storm, WebhookTargetMixin):
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

    auto_build = Bool(name='auto_build', allow_none=False)

    auto_build_archive_id = Int(name='auto_build_archive', allow_none=True)
    auto_build_archive = Reference(auto_build_archive_id, 'Archive.id')

    auto_build_pocket = DBEnum(enum=PackagePublishingPocket, allow_none=True)

    is_stale = Bool(name='is_stale', allow_none=False)

    require_virtualized = Bool(name='require_virtualized')

    private = Bool(name='private')

    store_upload = Bool(name='store_upload', allow_none=False)

    store_series_id = Int(name='store_series', allow_none=True)
    store_series = Reference(store_series_id, 'SnappySeries.id')

    store_name = Unicode(name='store_name', allow_none=True)

    store_secrets = JSON('store_secrets', allow_none=True)

    store_channels = JSON('store_channels', allow_none=True)

    def __init__(self, registrant, owner, distro_series, name,
                 description=None, branch=None, git_ref=None, auto_build=False,
                 auto_build_archive=None, auto_build_pocket=None,
                 require_virtualized=True, date_created=DEFAULT,
                 private=False, store_upload=False, store_series=None,
                 store_name=None, store_secrets=None, store_channels=None):
        """Construct a `Snap`."""
        super(Snap, self).__init__()
        self.registrant = registrant
        self.owner = owner
        self.distro_series = distro_series
        self.name = name
        self.description = description
        self.branch = branch
        self.git_ref = git_ref
        self.auto_build = auto_build
        self.auto_build_archive = auto_build_archive
        self.auto_build_pocket = auto_build_pocket
        self.require_virtualized = require_virtualized
        self.date_created = date_created
        self.date_last_modified = date_created
        self.private = private
        self.store_upload = store_upload
        self.store_series = store_series
        self.store_name = store_name
        self.store_secrets = store_secrets
        self.store_channels = store_channels

    @property
    def valid_webhook_event_types(self):
        return ["snap:build:0.1"]

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

    @property
    def available_processors(self):
        """See `ISnap`."""
        processors = Store.of(self).find(
            Processor,
            Processor.id == DistroArchSeries.processor_id,
            DistroArchSeries.id.is_in(
                self.distro_series.enabled_architectures.get_select_expr(
                    DistroArchSeries.id)))
        return processors.config(distinct=True)

    def _getProcessors(self):
        return list(Store.of(self).find(
            Processor,
            Processor.id == SnapArch.processor_id,
            SnapArch.snap == self))

    def setProcessors(self, processors, check_permissions=False, user=None):
        """See `ISnap`."""
        if check_permissions:
            can_modify = None
            if user is not None:
                roles = IPersonRoles(user)
                authz = lambda perm: getAdapter(self, IAuthorization, perm)
                if authz('launchpad.Admin').checkAuthenticated(roles):
                    can_modify = lambda proc: True
                elif authz('launchpad.Edit').checkAuthenticated(roles):
                    can_modify = lambda proc: not proc.restricted
            if can_modify is None:
                raise Unauthorized(
                    'Permission launchpad.Admin or launchpad.Edit required '
                    'on %s.' % self)
        else:
            can_modify = lambda proc: True

        enablements = dict(Store.of(self).find(
            (Processor, SnapArch),
            Processor.id == SnapArch.processor_id,
            SnapArch.snap == self))
        for proc in enablements:
            if proc not in processors:
                if not can_modify(proc):
                    raise CannotModifySnapProcessor(proc)
                Store.of(self).remove(enablements[proc])
        for proc in processors:
            if proc not in self.processors:
                if not can_modify(proc):
                    raise CannotModifySnapProcessor(proc)
                snaparch = SnapArch()
                snaparch.snap = self
                snaparch.processor = proc
                Store.of(self).add(snaparch)

    processors = property(_getProcessors, setProcessors)

    def getAllowedArchitectures(self):
        """See `ISnap`."""
        return [
            das for das in self.distro_series.buildable_architectures
            if (
                das.enabled
                and das.processor in self.processors
                and (
                    das.processor.supports_virtualized
                    or not self.require_virtualized))]

    @property
    def store_distro_series(self):
        if self.store_series is None:
            return None
        return getUtility(ISnappyDistroSeriesSet).getByBothSeries(
            self.store_series, self.distro_series)

    @store_distro_series.setter
    def store_distro_series(self, value):
        self.distro_series = value.distro_series
        self.store_series = value.snappy_series

    @property
    def can_upload_to_store(self):
        return (
            config.snappy.store_upload_url is not None and
            config.snappy.store_url is not None and
            self.store_upload and
            self.store_series is not None and
            self.store_name is not None and
            self.store_secrets is not None and
            "discharge" in self.store_secrets)

    def requestBuild(self, requester, archive, distro_arch_series, pocket):
        """See `ISnap`."""
        if not requester.inTeam(self.owner):
            raise SnapNotOwner(
                "%s cannot create snap package builds owned by %s." %
                (requester.displayname, self.owner.displayname))
        if not archive.enabled:
            raise ArchiveDisabled(archive.displayname)
        if distro_arch_series not in self.getAllowedArchitectures():
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

    def requestAutoBuilds(self, allow_failures=False, logger=None):
        """See `ISnapSet`."""
        builds = []
        if self.auto_build_archive is None:
            raise CannotRequestAutoBuilds("auto_build_archive")
        if self.auto_build_pocket is None:
            raise CannotRequestAutoBuilds("auto_build_pocket")
        self.is_stale = False
        if logger is not None:
            logger.debug(
                "Scheduling builds of snap package %s/%s",
                self.owner.name, self.name)
        for arch in self.getAllowedArchitectures():
            try:
                build = self.requestBuild(
                    self.owner, self.auto_build_archive, arch,
                    self.auto_build_pocket)
                if logger is not None:
                    logger.debug(
                        " - %s/%s/%s: Build requested.",
                        self.owner.name, self.name, arch.architecturetag)
                builds.append(build)
            except SnapBuildAlreadyPending as e:
                if logger is not None:
                    logger.warning(
                        " - %s/%s/%s: %s",
                        self.owner.name, self.name, arch.architecturetag, e)
            except Exception as e:
                if not allow_failures:
                    raise
                elif logger is not None:
                    logger.exception(
                        " - %s/%s/%s: %s",
                        self.owner.name, self.name, arch.architecturetag, e)
        return builds

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

    def getBuildSummariesForSnapBuildIds(self, snap_build_ids):
        """See `ISnap`."""
        result = {}
        if snap_build_ids is None:
            return result
        filter_term = SnapBuild.id.is_in(snap_build_ids)
        order_by = Desc(SnapBuild.id)
        builds = self._getBuilds(filter_term, order_by)

        # Prefetch data to keep DB query count constant
        getUtility(IBuildQueueSet).preloadForBuildFarmJobs(builds)
        lfas = load_related(LibraryFileAlias, builds, ["log_id"])
        load_related(LibraryFileContent, lfas, ["contentID"])

        for build in builds:
            if build.date is not None:
                when_complete = DateTimeFormatterAPI(build.date).displaydate()
            else:
                when_complete = None

            if build.log:
                build_log_size = build.log.content.filesize
            else:
                build_log_size = None

            result[build.id] = {
                "status": build.status.name,
                "buildstate": build.status,
                "when_complete": when_complete,
                "when_complete_estimate": build.estimate,
                "build_log_url": build.log_url,
                "build_log_size": build_log_size,
                }
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
        store = IStore(Snap)
        store.find(SnapArch, SnapArch.snap == self).remove()
        # Remove build jobs.  There won't be many queued builds, so we can
        # afford to do this the safe but slow way via BuildQueue.destroySelf
        # rather than in bulk.
        buildqueue_records = store.find(
            BuildQueue,
            BuildQueue._build_farm_job_id == SnapBuild.build_farm_job_id,
            SnapBuild.snap == self)
        for buildqueue_record in buildqueue_records:
            buildqueue_record.destroySelf()
        build_farm_job_ids = list(store.find(
            SnapBuild.build_farm_job_id, SnapBuild.snap == self))
        # XXX cjwatson 2016-02-27 bug=322972: Requires manual SQL due to
        # lack of support for DELETE FROM ... USING ... in Storm.
        store.execute("""
            DELETE FROM SnapFile
            USING SnapBuild
            WHERE
                SnapFile.snapbuild = SnapBuild.id AND
                SnapBuild.snap = ?
            """, (self.id,))
        store.find(SnapBuild, SnapBuild.snap == self).remove()
        getUtility(IWebhookSet).delete(self.webhooks)
        store.remove(self)
        store.find(
            BuildFarmJob, BuildFarmJob.id.is_in(build_farm_job_ids)).remove()


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
            branch=None, git_ref=None, auto_build=False,
            auto_build_archive=None, auto_build_pocket=None,
            require_virtualized=True, processors=None, date_created=DEFAULT,
            private=False, store_upload=False, store_series=None,
            store_name=None, store_secrets=None, store_channels=None):
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
        if self.exists(owner, name):
            raise DuplicateSnapName

        if not self.isValidPrivacy(private, owner, branch, git_ref):
            raise SnapPrivacyMismatch

        store = IMasterStore(Snap)
        snap = Snap(
            registrant, owner, distro_series, name, description=description,
            branch=branch, git_ref=git_ref, auto_build=auto_build,
            auto_build_archive=auto_build_archive,
            auto_build_pocket=auto_build_pocket,
            require_virtualized=require_virtualized, date_created=date_created,
            private=private, store_upload=store_upload,
            store_series=store_series, store_name=store_name,
            store_secrets=store_secrets, store_channels=store_channels)
        store.add(snap)

        if processors is None:
            processors = [
                p for p in getUtility(IProcessorSet).getAll()
                if p.build_by_default]
        snap.setProcessors(processors)

        return snap

    def isValidPrivacy(self, private, owner, branch=None, git_ref=None):
        """See `ISnapSet`."""
        # Private snaps may contain anything ...
        if private:
            # If appropriately enabled via feature flag.
            if not getFeatureFlag(SNAP_PRIVATE_FEATURE_FLAG):
                raise SnapPrivateFeatureDisabled
            return True

        # Public snaps with private sources are not allowed.
        source_ref = branch or git_ref
        if source_ref.information_type in PRIVATE_INFORMATION_TYPES:
            return False

        # Public snaps owned by private teams are not allowed.
        if owner.is_team and owner.visibility == PersonVisibility.PRIVATE:
            return False

        return True

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

    def findByGitRepository(self, repository, paths=None):
        """See `ISnapSet`."""
        clauses = [Snap.git_repository == repository]
        if paths is not None:
            clauses.append(Snap.git_path.is_in(paths))
        return IStore(Snap).find(Snap, *clauses)

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

        person_ids = set()
        for snap in snaps:
            person_ids.add(snap.registrant_id)
            person_ids.add(snap.owner_id)

        branches = load_related(Branch, snaps, ["branch_id"])
        repositories = load_related(
            GitRepository, snaps, ["git_repository_id"])
        if branches:
            GenericBranchCollection.preloadDataForBranches(branches)
        if repositories:
            GenericGitCollection.preloadDataForRepositories(repositories)
        # The stacked-on branches are used to check branch visibility.
        GenericBranchCollection.preloadVisibleStackedOnBranches(branches, user)
        GenericGitCollection.preloadVisibleRepositories(repositories, user)

        # Add branch/repository owners to the list of pre-loaded persons.
        # We need the target repository owner as well; unlike branches,
        # repository unique names aren't trigger-maintained.
        person_ids.update(branch.ownerID for branch in branches)
        person_ids.update(repository.owner_id for repository in repositories)

        list(getUtility(IPersonSet).getPrecachedPersonsFromIDs(
            person_ids, need_validity=True))

    @staticmethod
    def _findStaleSnaps():
        """See `ISnapSet`."""
        threshold_date = (
            datetime.now(pytz.UTC) -
            timedelta(minutes=config.snappy.auto_build_frequency))
        origin = [
            Snap,
            LeftJoin(
                SnapBuild,
                And(
                    SnapBuild.snap_id == Snap.id,
                    SnapBuild.archive_id == Snap.auto_build_archive_id,
                    SnapBuild.pocket == Snap.auto_build_pocket,
                    # We only want Snaps that haven't had an automatic
                    # SnapBuild dispatched for them recently.
                    SnapBuild.date_created >= threshold_date)),
            ]
        return IStore(Snap).using(*origin).find(
            Snap,
            Snap.is_stale == True,
            Snap.auto_build == True,
            SnapBuild.date_created == None).config(distinct=True)

    @classmethod
    def makeAutoBuilds(cls, logger=None):
        """See `ISnapSet`."""
        snaps = cls._findStaleSnaps()
        builds = []
        for snap in snaps:
            builds.extend(snap.requestAutoBuilds(
                allow_failures=True, logger=logger))
        return builds

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
