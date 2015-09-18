# Copyright 2014-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'LiveFS',
    ]

import pytz
from storm.exceptions import IntegrityError
from storm.locals import (
    Bool,
    DateTime,
    Desc,
    Int,
    JSON,
    Not,
    Reference,
    Store,
    Storm,
    Unicode,
    )
from zope.component import getUtility
from zope.interface import implementer

from lp.buildmaster.enums import BuildStatus
from lp.registry.errors import NoSuchDistroSeries
from lp.registry.interfaces.distribution import (
    IDistributionSet,
    NoSuchDistribution,
    )
from lp.registry.interfaces.distroseries import IDistroSeriesSet
from lp.registry.interfaces.person import (
    IPersonSet,
    NoSuchPerson,
    )
from lp.registry.interfaces.role import IHasOwner
from lp.registry.model.person import (
    get_person_visibility_terms,
    Person,
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
from lp.soyuz.interfaces.archive import ArchiveDisabled
from lp.soyuz.interfaces.livefs import (
    CannotDeleteLiveFS,
    DuplicateLiveFSName,
    ILiveFS,
    ILiveFSSet,
    LIVEFS_FEATURE_FLAG,
    LiveFSBuildAlreadyPending,
    LiveFSBuildArchiveOwnerMismatch,
    LiveFSFeatureDisabled,
    LiveFSNotOwner,
    NoSuchLiveFS,
    )
from lp.soyuz.interfaces.livefsbuild import ILiveFSBuildSet
from lp.soyuz.model.archive import (
    Archive,
    get_enabled_archive_filter,
    )
from lp.soyuz.model.livefsbuild import LiveFSBuild


def livefs_modified(livefs, event):
    """Update the date_last_modified property when a LiveFS is modified.

    This method is registered as a subscriber to `IObjectModifiedEvent`
    events on live filesystems.
    """
    livefs.date_last_modified = UTC_NOW


@implementer(ILiveFS, IHasOwner)
class LiveFS(Storm):
    """See `ILiveFS`."""

    __storm_table__ = 'LiveFS'

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

    metadata = JSON('json_data')

    require_virtualized = Bool(name='require_virtualized')

    def __init__(self, registrant, owner, distro_series, name,
                 metadata, require_virtualized, date_created):
        """Construct a `LiveFS`."""
        if not getFeatureFlag(LIVEFS_FEATURE_FLAG):
            raise LiveFSFeatureDisabled
        super(LiveFS, self).__init__()
        self.registrant = registrant
        self.owner = owner
        self.distro_series = distro_series
        self.name = name
        self.metadata = metadata
        self.require_virtualized = require_virtualized
        self.date_created = date_created
        self.date_last_modified = date_created

    def requestBuild(self, requester, archive, distro_arch_series, pocket,
                     unique_key=None, metadata_override=None, version=None):
        """See `ILiveFS`."""
        if not requester.inTeam(self.owner):
            raise LiveFSNotOwner(
                "%s cannot create live filesystem builds owned by %s." %
                (requester.displayname, self.owner.displayname))
        if not archive.enabled:
            raise ArchiveDisabled(archive.displayname)
        if archive.private and self.owner != archive.owner:
            # See rationale in `LiveFSBuildArchiveOwnerMismatch` docstring.
            raise LiveFSBuildArchiveOwnerMismatch()

        pending = IStore(self).find(
            LiveFSBuild,
            LiveFSBuild.livefs_id == self.id,
            LiveFSBuild.archive_id == archive.id,
            LiveFSBuild.distro_arch_series_id == distro_arch_series.id,
            LiveFSBuild.pocket == pocket,
            LiveFSBuild.unique_key == unique_key,
            LiveFSBuild.status == BuildStatus.NEEDSBUILD)
        if pending.any() is not None:
            raise LiveFSBuildAlreadyPending

        build = getUtility(ILiveFSBuildSet).new(
            requester, self, archive, distro_arch_series, pocket,
            unique_key=unique_key, metadata_override=metadata_override,
            version=version)
        build.queueBuild()
        return build

    def _getBuilds(self, filter_term, order_by):
        """The actual query to get the builds."""
        query_args = [
            LiveFSBuild.livefs == self,
            LiveFSBuild.archive_id == Archive.id,
            Archive._enabled == True,
            get_enabled_archive_filter(
                getUtility(ILaunchBag).user, include_public=True,
                include_subscribed=True)
            ]
        if filter_term is not None:
            query_args.append(filter_term)
        result = Store.of(self).find(LiveFSBuild, *query_args)
        result.order_by(order_by)
        return result

    @property
    def builds(self):
        """See `ILiveFS`."""
        order_by = (
            NullsLast(Desc(Greatest(
                LiveFSBuild.date_started,
                LiveFSBuild.date_finished))),
            Desc(LiveFSBuild.date_created),
            Desc(LiveFSBuild.id))
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
        """See `ILiveFS`."""
        filter_term = (Not(LiveFSBuild.status.is_in(self._pending_states)))
        order_by = (
            NullsLast(Desc(Greatest(
                LiveFSBuild.date_started,
                LiveFSBuild.date_finished))),
            Desc(LiveFSBuild.id))
        return self._getBuilds(filter_term, order_by)

    @property
    def pending_builds(self):
        """See `ILiveFS`."""
        filter_term = (LiveFSBuild.status.is_in(self._pending_states))
        # We want to order by date_created but this is the same as ordering
        # by id (since id increases monotonically) and is less expensive.
        order_by = Desc(LiveFSBuild.id)
        return self._getBuilds(filter_term, order_by)

    def destroySelf(self):
        """See `ILiveFS`."""
        if not self.builds.is_empty():
            raise CannotDeleteLiveFS(
                "Cannot delete a live filesystem with builds.")
        IStore(LiveFS).remove(self)


@implementer(ILiveFSSet)
class LiveFSSet:
    """See `ILiveFSSet`."""

    def new(self, registrant, owner, distro_series, name, metadata,
            require_virtualized=True, date_created=DEFAULT):
        """See `ILiveFSSet`."""
        if not registrant.inTeam(owner):
            if owner.is_team:
                raise LiveFSNotOwner(
                    "%s is not a member of %s." %
                    (registrant.displayname, owner.displayname))
            else:
                raise LiveFSNotOwner(
                    "%s cannot create live filesystems owned by %s." %
                    (registrant.displayname, owner.displayname))

        store = IMasterStore(LiveFS)
        livefs = LiveFS(
            registrant, owner, distro_series, name, metadata,
            require_virtualized, date_created)
        store.add(livefs)

        try:
            store.flush()
        except IntegrityError:
            raise DuplicateLiveFSName

        return livefs

    def _getByName(self, owner, distro_series, name):
        return IStore(LiveFS).find(
            LiveFS,
            LiveFS.owner == owner,
            LiveFS.distro_series == distro_series,
            LiveFS.name == name).one()

    def exists(self, owner, distro_series, name):
        """See `ILiveFSSet`."""
        return self._getByName(owner, distro_series, name) is not None

    def getByName(self, owner, distro_series, name):
        """See `ILiveFSSet`."""
        livefs = self._getByName(owner, distro_series, name)
        if livefs is None:
            raise NoSuchLiveFS(name)
        return livefs

    def _findOrRaise(self, error, name, finder, *args):
        if name is None:
            return None
        args = list(args)
        args.append(name)
        result = finder(*args)
        if result is None:
            raise error(name)
        return result

    def interpret(self, owner_name, distribution_name, distro_series_name,
                  name):
        """See `ILiveFSSet`."""
        owner = self._findOrRaise(
            NoSuchPerson, owner_name, getUtility(IPersonSet).getByName)
        distribution = self._findOrRaise(
            NoSuchDistribution, distribution_name,
            getUtility(IDistributionSet).getByName)
        distro_series = self._findOrRaise(
            NoSuchDistroSeries, distro_series_name,
            getUtility(IDistroSeriesSet).queryByName, distribution)
        return self.getByName(owner, distro_series, name)

    def getByPerson(self, owner):
        """See `ILiveFSSet`."""
        return IStore(LiveFS).find(LiveFS, LiveFS.owner == owner)

    def getAll(self):
        """See `ILiveFSSet`."""
        user = getUtility(ILaunchBag).user
        return IStore(LiveFS).find(
            LiveFS,
            LiveFS.owner == Person.id,
            get_person_visibility_terms(user)).order_by("name")
