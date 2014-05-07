# Copyright 2014 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'LiveFS',
    ]

import pytz
from storm.exceptions import IntegrityError
from storm.locals import (
    DateTime,
    Desc,
    Int,
    JSON,
    Reference,
    Store,
    Storm,
    Unicode,
    )
from zope.component import getUtility
from zope.interface import implements

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
from lp.services.database.constants import (
    DEFAULT,
    UTC_NOW,
    )
from lp.services.database.interfaces import (
    IMasterStore,
    IStore,
    )
from lp.services.database.stormexpr import Greatest
from lp.services.features import getFeatureFlag
from lp.soyuz.interfaces.livefs import (
    DuplicateLiveFSName,
    ILiveFS,
    ILiveFSSet,
    LIVEFS_FEATURE_FLAG,
    LiveFSBuildAlreadyPending,
    LiveFSFeatureDisabled,
    LiveFSNotOwner,
    )
from lp.soyuz.interfaces.livefsbuild import ILiveFSBuildSet
from lp.soyuz.model.archive import Archive
from lp.soyuz.model.livefsbuild import LiveFSBuild


def livefs_modified(livefs, event):
    """Update the date_last_modified property when a LiveFS is modified.

    This method is registered as a subscriber to `IObjectModifiedEvent`
    events on live filesystems.
    """
    livefs.date_last_modified = UTC_NOW


class LiveFS(Storm):
    """See `ILiveFS`."""

    __storm_table__ = 'LiveFS'

    implements(ILiveFS, IHasOwner)

    id = Int(primary=True)

    date_created = DateTime(
        name='date_created', tzinfo=pytz.UTC, allow_none=False)
    date_last_modified = DateTime(
        name='date_last_modified', tzinfo=pytz.UTC, allow_none=False)

    registrant_id = Int(name='registrant', allow_none=False)
    registrant = Reference(registrant_id, 'Person.id')

    owner_id = Int(name='owner', allow_none=False)
    owner = Reference(owner_id, 'Person.id')

    distroseries_id = Int(name='distroseries', allow_none=False)
    distroseries = Reference(distroseries_id, 'DistroSeries.id')

    name = Unicode(name='name', allow_none=False)

    metadata = JSON('json_data')

    def __init__(self, registrant, owner, distroseries, name, metadata,
                 date_created):
        """Construct a `LiveFS`."""
        if not getFeatureFlag(LIVEFS_FEATURE_FLAG):
            raise LiveFSFeatureDisabled
        super(LiveFS, self).__init__()
        self.registrant = registrant
        self.owner = owner
        self.distroseries = distroseries
        self.name = name
        self.metadata = metadata
        self.date_created = date_created
        self.date_last_modified = date_created

    def requestBuild(self, requester, archive, distroarchseries, pocket,
                     unique_key=None, metadata_override=None):
        """See `ILiveFS`."""
        if not requester.inTeam(self.owner):
            raise LiveFSNotOwner(
                "%s cannot create live filesystem builds owned by %s." %
                (requester.displayname, self.owner.displayname))

        pending = IStore(self).find(
            LiveFSBuild,
            LiveFSBuild.livefs_id == self.id,
            LiveFSBuild.archive_id == archive.id,
            LiveFSBuild.distroarchseries_id == distroarchseries.id,
            LiveFSBuild.pocket == pocket,
            LiveFSBuild.unique_key == unique_key,
            LiveFSBuild.status == BuildStatus.NEEDSBUILD)
        if pending.any() is not None:
            raise LiveFSBuildAlreadyPending

        build = getUtility(ILiveFSBuildSet).new(
            requester, self, archive, distroarchseries, pocket,
            unique_key=unique_key, metadata_override=metadata_override)
        build.queueBuild()
        return build

    def _getBuilds(self, filter_term, order_by):
        """The actual query to get the builds."""
        query_args = [
            LiveFSBuild.livefs == self,
            LiveFSBuild.archive_id == Archive.id,
            Archive._enabled == True,
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
            Desc(Greatest(
                LiveFSBuild.date_started,
                LiveFSBuild.date_finished)),
            Desc(LiveFSBuild.date_created),
            Desc(LiveFSBuild.id))
        return self._getBuilds(None, order_by)

    @property
    def completed_builds(self):
        """See `ILiveFS`."""
        filter_term = (LiveFSBuild.status != BuildStatus.NEEDSBUILD)
        order_by = (
            Desc(Greatest(
                LiveFSBuild.date_started,
                LiveFSBuild.date_finished)),
            Desc(LiveFSBuild.id))
        return self._getBuilds(filter_term, order_by)

    @property
    def pending_builds(self):
        """See `ILiveFS`."""
        filter_term = (LiveFSBuild.status == BuildStatus.NEEDSBUILD)
        # We want to order by date_created but this is the same as ordering
        # by id (since id increases monotonically) and is less expensive.
        order_by = Desc(LiveFSBuild.id)
        return self._getBuilds(filter_term, order_by)


class LiveFSSet:
    """See `ILiveFSSet`."""

    implements(ILiveFSSet)

    def new(self, registrant, owner, distroseries, name, metadata,
            date_created=DEFAULT):
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
            registrant, owner, distroseries, name, metadata, date_created)
        store.add(livefs)

        try:
            store.flush()
        except IntegrityError:
            raise DuplicateLiveFSName

        return livefs

    def exists(self, owner, distroseries, name):
        """See `ILiveFSSet`."""
        return self.get(owner, distroseries, name) is not None

    def get(self, owner, distroseries, name):
        """See `ILiveFSSet`."""
        store = IStore(LiveFS)
        return store.find(
            LiveFS,
            LiveFS.owner == owner,
            LiveFS.distroseries == distroseries,
            LiveFS.name == name).one()

    def _findOrRaise(self, error, name, finder, *args):
        if name is None:
            return None
        args = list(args)
        args.append(name)
        result = finder(*args)
        if result is None:
            raise error(name)
        return result

    def interpret(self, owner_name, distribution_name, distroseries_name,
                  name):
        """See `ILiveFSSet`."""
        owner = self._findOrRaise(
            NoSuchPerson, owner_name, getUtility(IPersonSet).getByName)
        distribution = self._findOrRaise(
            NoSuchDistribution, distribution_name,
            getUtility(IDistributionSet).getByName)
        distroseries = self._findOrRaise(
            NoSuchDistroSeries, distroseries_name,
            getUtility(IDistroSeriesSet).queryByName, distribution)
        return self.get(owner, distroseries, name)

    def getAll(self):
        """See `ILiveFSSet`."""
        store = IStore(LiveFS)
        return store.find(LiveFS).order_by("name")
