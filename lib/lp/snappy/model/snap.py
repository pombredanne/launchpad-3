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
from lp.registry.interfaces.role import IHasOwner
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
        if git_ref is not None:
            self.git_repository = git_ref.repository
            self.git_path = git_ref.path
        else:
            self.git_repository = None
            self.git_path = None
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
        self.git_repository = value.repository
        self.git_path = value.path

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

    def findByPerson(self, owner):
        """See `ISnapSet`."""
        return IStore(Snap).find(Snap, Snap.owner == owner)

    def findByBranch(self, branch):
        """See `ISnapSet`."""
        return IStore(Snap).find(Snap, Snap.branch == branch)

    def findByGitRepository(self, repository):
        """See `ISnapSet`."""
        return IStore(Snap).find(Snap, Snap.git_repository == repository)

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
